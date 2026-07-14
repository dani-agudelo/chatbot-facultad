"""Servicios de dominio del panel admin."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from admin.models import AdminAuditLog, AdminUser, ChatbotAdminSettings
from admin.runtime_keys import set_db_api_keys
from admin.schemas import BrandingOut, SettingsOut
from admin.secrets_crypto import decrypt_secret, encrypt_secret
from admin.security import hash_password, verify_password
from admin.settings import get_admin_settings
from config import (
    DATA_DIR,
    DEFAULT_EMBED_MODEL,
    DEFAULT_CHAT_SIMILARITY_TOP_K,
    get_active_llm_model,
)
from llm.factory import DEFAULT_GEMINI_MODEL, DEFAULT_NVIDIA_MODEL

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


def write_audit(db: Session, actor: AdminUser | None, action: str, summary: str) -> None:
    db.add(
        AdminAuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            payload_summary=summary[:2000],
        )
    )
    db.commit()


def get_or_create_settings(db: Session) -> ChatbotAdminSettings:
    row = db.query(ChatbotAdminSettings).order_by(ChatbotAdminSettings.id.asc()).first()
    if row is not None:
        return row

    from config import _load_env
    import os

    _load_env()
    provider = os.getenv("LLM_PROVIDER", "nvidia").strip().lower()
    if provider not in {"gemini", "nvidia"}:
        provider = "nvidia"
    default_model = DEFAULT_NVIDIA_MODEL if provider == "nvidia" else DEFAULT_GEMINI_MODEL
    llm_model = os.getenv("LLM_MODEL", default_model).strip() or default_model
    embed_model = os.getenv("EMBED_MODEL", DEFAULT_EMBED_MODEL).strip() or DEFAULT_EMBED_MODEL
    top_k = int(os.getenv("CHAT_SIMILARITY_TOP_K", str(DEFAULT_CHAT_SIMILARITY_TOP_K)))

    row = ChatbotAdminSettings(
        provider=provider,
        llm_model=llm_model,
        embed_model=embed_model,
        similarity_top_k=max(1, min(20, top_k)),
        reindex_required=False,
        logo_url="",
        primary_color="#00407d",
        accent_color="#f27022",
        brand_name="Chatbot Facultad",
        brand_subtitle="Administración",
        gemini_api_key_enc="",
        nvidia_api_key_enc="",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def sync_api_keys_from_row(row: ChatbotAdminSettings) -> None:
    """Carga en memoria las keys cifradas de BD (prioridad sobre .env)."""
    set_db_api_keys(
        gemini=decrypt_secret(row.gemini_api_key_enc),
        nvidia=decrypt_secret(row.nvidia_api_key_enc),
    )


def load_api_keys_from_db() -> None:
    """Best-effort al arranque: si PostgreSQL no esta, se usa .env."""
    try:
        from admin.db import SessionLocal

        db = SessionLocal()
        try:
            sync_api_keys_from_row(get_or_create_settings(db))
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001 — arranque no debe morir por admin DB
        logger.warning("event=api_keys_db_load_skipped reason=%s", exc)


def settings_to_out(row: ChatbotAdminSettings) -> SettingsOut:
    import os

    from config import _load_env

    _load_env()
    return SettingsOut(
        provider=row.provider,  # type: ignore[arg-type]
        llm_model=row.llm_model,
        embed_model=row.embed_model,
        similarity_top_k=row.similarity_top_k,
        reindex_required=row.reindex_required,
        last_reindex_at=row.last_reindex_at,
        last_reindex_result=row.last_reindex_result,
        updated_at=row.updated_at,
        logo_url=row.logo_url or "",
        primary_color=row.primary_color or "#00407d",
        accent_color=row.accent_color or "#f27022",
        brand_name=row.brand_name or "Chatbot Facultad",
        brand_subtitle=row.brand_subtitle or "Administración",
        gemini_api_key_set=bool((row.gemini_api_key_enc or "").strip()),
        nvidia_api_key_set=bool((row.nvidia_api_key_enc or "").strip()),
        gemini_api_key_env=bool(os.getenv("GEMINI_API_KEY", "").strip()),
        nvidia_api_key_env=bool(os.getenv("NVIDIA_API_KEY", "").strip()),
    )


def branding_to_out(row: ChatbotAdminSettings) -> BrandingOut:
    return BrandingOut(
        logo_url=row.logo_url or "",
        primary_color=row.primary_color or "#00407d",
        accent_color=row.accent_color or "#f27022",
        brand_name=row.brand_name or "Chatbot Facultad",
        brand_subtitle=row.brand_subtitle or "Administración",
    )


def apply_runtime_settings(settings: ChatbotAdminSettings) -> None:
    """Aplica provider/modelo/top_k y secrets de BD en caliente."""
    import os

    import config as app_config
    from llama_index.core import Settings
    from llm.gemini_provider import GeminiLLMProvider
    from llm.nvidia_provider import NvidiaLLMProvider

    sync_api_keys_from_row(settings)

    if settings.provider == "gemini":
        GeminiLLMProvider(
            api_key=app_config.get_gemini_api_key(),
            model=settings.llm_model,
        ).configure_llm()
    elif settings.provider == "nvidia":
        NvidiaLLMProvider(
            api_key=app_config.get_nvidia_api_key(),
            model=settings.llm_model,
        ).configure_llm()
    else:
        raise ValueError(f"Proveedor no soportado: {settings.provider}")

    os.environ["CHAT_SIMILARITY_TOP_K"] = str(settings.similarity_top_k)
    os.environ["LLM_PROVIDER"] = settings.provider
    os.environ["LLM_MODEL"] = settings.llm_model
    os.environ["EMBED_MODEL"] = settings.embed_model

    from generation.engine_factory import reset_shared_retriever
    from generation.session_store import clear_all_sessions

    reset_shared_retriever()
    clear_all_sessions()

    _ = Settings.llm
    logger.info(
        "event=admin_settings_applied provider=%s model=%s top_k=%s",
        settings.provider,
        settings.llm_model,
        settings.similarity_top_k,
    )


def apply_embed_model(settings: ChatbotAdminSettings) -> None:
    """Aplica embeddings y exige indice fresco."""
    from llama_index.core import Settings
    from llama_index.embeddings.nvidia import NVIDIAEmbedding

    import config as app_config

    Settings.embed_model = NVIDIAEmbedding(
        model=settings.embed_model,
        api_key=app_config.get_nvidia_api_key(),
        embed_batch_size=app_config.DEFAULT_EMBED_BATCH_SIZE,
        truncate="END",
    )


def authenticate_admin(db: Session, email: str, password: str) -> AdminUser:
    user = db.query(AdminUser).filter(AdminUser.email == email.lower().strip()).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo.",
        )
    return user


def create_admin_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    is_active: bool = True,
    actor: AdminUser | None = None,
) -> AdminUser:
    normalized = email.lower().strip()
    exists = db.query(AdminUser).filter(AdminUser.email == normalized).first()
    if exists is not None:
        raise HTTPException(status_code=400, detail="El correo ya esta registrado.")

    user = AdminUser(
        email=normalized,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit(db, actor, "user.create", f"email={normalized}")
    return user


def list_documents() -> list[dict]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    for path in sorted(DATA_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        stat = path.stat()
        items.append(
            {
                "file_name": path.name,
                "size_bytes": stat.st_size,
                "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            }
        )
    return items


def save_upload(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo requerido.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo no permitido. Use: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    safe_name = Path(file.filename).name
    target = DATA_DIR / safe_name
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    settings = get_admin_settings()
    size = 0
    with target.open("wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.max_upload_bytes:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400,
                    detail=f"Archivo supera el limite de {settings.max_upload_mb} MB.",
                )
            out.write(chunk)
    return safe_name


def delete_document(file_name: str) -> None:
    safe_name = Path(file_name).name
    target = DATA_DIR / safe_name
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    if target.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Tipo de archivo no gestionable.")
    target.unlink()


def documents_count() -> int:
    return len(list_documents())
