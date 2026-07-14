"""Routers del panel de administracion."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from admin.db import get_db
from admin.deps import get_current_admin
from admin.models import AdminUser
from admin.schemas import (
    AdminChatRequest,
    AdminChatResponse,
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
    BrandingOut,
    DashboardOut,
    DocumentOut,
    LoginRequest,
    ReindexResponse,
    SettingsOut,
    SettingsUpdate,
    TokenResponse,
)
from admin.security import create_access_token, hash_password
from admin.services import (
    apply_embed_model,
    apply_runtime_settings,
    authenticate_admin,
    branding_to_out,
    create_admin_user,
    delete_document,
    documents_count,
    get_or_create_settings,
    list_documents,
    save_upload,
    settings_to_out,
    write_audit,
)
from admin.secrets_crypto import encrypt_secret
from admin.settings import get_admin_settings
from api.schemas import ChatRequest
from config import DATA_DIR, get_active_llm_model
from services.chat_service import ChatService
from services.ingest_service import IngestService

auth_router = APIRouter(prefix="/auth", tags=["admin-auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@auth_router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_admin(db, body.email, body.password)
    settings = get_admin_settings()
    token = create_access_token(subject=user.email, extra={"uid": user.id})
    write_audit(db, user, "auth.login", f"email={user.email}")
    return TokenResponse(
        access_token=token,
        expires_in_hours=settings.jwt_expire_hours,
    )


@auth_router.get("/me", response_model=AdminUserOut)
def me(current: AdminUser = Depends(get_current_admin)) -> AdminUser:
    return current


@admin_router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> DashboardOut:
    settings = get_or_create_settings(db)
    model_name = settings.llm_model or "unknown"
    try:
        model_name = get_active_llm_model()
    except Exception:
        pass
    return DashboardOut(
        status="ok",
        provider=settings.provider,
        model=model_name,
        documents_count=documents_count(),
        reindex_required=settings.reindex_required,
        last_reindex_at=settings.last_reindex_at,
        last_reindex_result=settings.last_reindex_result,
    )


@admin_router.get("/branding", response_model=BrandingOut)
def get_branding(db: Session = Depends(get_db)) -> BrandingOut:
    return branding_to_out(get_or_create_settings(db))


@admin_router.get("/settings", response_model=SettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> SettingsOut:
    return settings_to_out(get_or_create_settings(db))


@admin_router.put("/settings", response_model=SettingsOut)
def update_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
) -> SettingsOut:
    row = get_or_create_settings(db)
    embed_changed = False

    if body.provider is not None:
        row.provider = body.provider
    if body.llm_model is not None:
        row.llm_model = body.llm_model.strip()
    if body.similarity_top_k is not None:
        row.similarity_top_k = body.similarity_top_k
    if body.embed_model is not None:
        new_embed = body.embed_model.strip()
        if new_embed != row.embed_model:
            row.embed_model = new_embed
            row.reindex_required = True
            embed_changed = True
    if body.logo_url is not None:
        row.logo_url = body.logo_url.strip()
    if body.primary_color is not None:
        row.primary_color = body.primary_color.lower()
    if body.accent_color is not None:
        row.accent_color = body.accent_color.lower()
    if body.brand_name is not None:
        row.brand_name = body.brand_name.strip()
    if body.brand_subtitle is not None:
        row.brand_subtitle = body.brand_subtitle.strip()

    if body.clear_gemini_api_key:
        row.gemini_api_key_enc = ""
    elif body.gemini_api_key is not None:
        row.gemini_api_key_enc = encrypt_secret(body.gemini_api_key)

    if body.clear_nvidia_api_key:
        row.nvidia_api_key_enc = ""
    elif body.nvidia_api_key is not None:
        row.nvidia_api_key_enc = encrypt_secret(body.nvidia_api_key)

    row.updated_by_id = current.id
    db.commit()
    db.refresh(row)

    try:
        apply_runtime_settings(row)
        if embed_changed:
            # Guardamos el nuevo embed en Settings pero el indice queda desactualizado
            # hasta reindex; se avisa con reindex_required.
            apply_embed_model(row)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo aplicar la configuracion: {exc}",
        ) from exc

    keys_note = []
    if body.clear_gemini_api_key or body.gemini_api_key is not None:
        keys_note.append("gemini_key")
    if body.clear_nvidia_api_key or body.nvidia_api_key is not None:
        keys_note.append("nvidia_key")
    write_audit(
        db,
        current,
        "settings.update",
        f"provider={row.provider} model={row.llm_model} embed={row.embed_model}"
        + (f" keys={','.join(keys_note)}" if keys_note else ""),
    )
    return settings_to_out(row)


@admin_router.get("/documents", response_model=list[DocumentOut])
def documents(
    _: AdminUser = Depends(get_current_admin),
) -> list[DocumentOut]:
    return [DocumentOut(**item) for item in list_documents()]


@admin_router.post("/documents/upload", response_model=DocumentOut, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
) -> DocumentOut:
    name = save_upload(file)
    settings = get_or_create_settings(db)
    settings.reindex_required = True
    db.commit()
    write_audit(db, current, "documents.upload", f"file={name}")

    path = DATA_DIR / name
    stat = path.stat()
    return DocumentOut(
        file_name=name,
        size_bytes=stat.st_size,
        updated_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
    )


@admin_router.delete("/documents/{file_name}", status_code=204)
def remove_document(
    file_name: str,
    db: Session = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
) -> None:
    delete_document(file_name)
    settings = get_or_create_settings(db)
    settings.reindex_required = True
    db.commit()
    write_audit(db, current, "documents.delete", f"file={file_name}")


@admin_router.post("/reindex", response_model=ReindexResponse)
def reindex(
    db: Session = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
) -> ReindexResponse:
    settings = get_or_create_settings(db)
    try:
        apply_runtime_settings(settings)
        if settings.reindex_required:
            apply_embed_model(settings)
        result = IngestService().run()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    settings.reindex_required = False
    settings.last_reindex_at = datetime.now(timezone.utc)
    settings.last_reindex_result = (
        f"{result.indexed_documents} docs / {result.indexed_nodes} chunks"
    )
    settings.updated_by_id = current.id
    db.commit()
    write_audit(db, current, "documents.reindex", settings.last_reindex_result)

    return ReindexResponse(
        indexed_documents=result.indexed_documents,
        indexed_nodes=result.indexed_nodes,
        total_documents=result.total_documents,
        collection_name=result.collection_name,
        message="Reindexacion completada.",
    )


@admin_router.post("/chat/test", response_model=AdminChatResponse)
def chat_test(
    body: AdminChatRequest,
    db: Session = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
) -> AdminChatResponse:
    settings = get_or_create_settings(db)
    response = ChatService().reply(
        ChatRequest(session_id=body.session_id, message=body.message)
    )
    note = None
    if settings.reindex_required:
        note = "Advertencia: hay cambios pendientes de reindexar."
    write_audit(db, current, "chat.test", f"session={body.session_id}")
    return AdminChatResponse(
        answer=response.answer,
        provider=settings.provider,
        model=get_active_llm_model(),
        sources=[item.model_dump() for item in response.sources],
        note=note,
    )


@admin_router.get("/users", response_model=list[AdminUserOut])
def list_users(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> list[AdminUser]:
    return db.query(AdminUser).order_by(AdminUser.id.asc()).all()


@admin_router.post("/users", response_model=AdminUserOut, status_code=201)
def create_user(
    body: AdminUserCreate,
    db: Session = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
) -> AdminUser:
    return create_admin_user(
        db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        is_active=body.is_active,
        actor=current,
    )


@admin_router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    body: AdminUserUpdate,
    db: Session = Depends(get_db),
    current: AdminUser = Depends(get_current_admin),
) -> AdminUser:
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.is_active is not None:
        if user.id == current.id and body.is_active is False:
            raise HTTPException(
                status_code=400,
                detail="No puede desactivarse a si mismo.",
            )
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = hash_password(body.password)

    db.commit()
    db.refresh(user)
    write_audit(db, current, "user.update", f"id={user.id}")
    return user
