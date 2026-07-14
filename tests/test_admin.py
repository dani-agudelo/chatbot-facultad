"""Pruebas del panel de administracion (auth, settings, docs, chat)."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import config
from admin.db import Base, get_db
from admin.models import AdminUser, ChatbotAdminSettings
from admin.security import create_access_token, hash_password
from admin.settings import get_admin_settings


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def admin_user(db_session):
    user = AdminUser(
        email="admin@facultad.edu",
        password_hash=hash_password("Password123!"),
        full_name="Admin Test",
        is_active=True,
    )
    db_session.add(user)
    db_session.add(
        ChatbotAdminSettings(
            provider="nvidia",
            llm_model="meta/llama-3.1-8b-instruct",
            embed_model="baai/bge-m3",
            similarity_top_k=5,
            reindex_required=False,
        )
    )
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def inactive_user(db_session):
    user = AdminUser(
        email="inactive@facultad.edu",
        password_hash=hash_password("Password123!"),
        full_name="Inactive",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def client(db_session, admin_user):
    config._CONFIGURED = True
    get_admin_settings.cache_clear()

    def _override_db():
        try:
            yield db_session
        finally:
            pass

    with (
        patch("api.main.configure_settings"),
        patch("api.main.setup_logging"),
        patch("api.main.get_llm_provider") as provider_mock,
        patch("api.main.get_active_llm_model", return_value="meta/llama-3.1-8b-instruct"),
    ):
        provider_mock.return_value.get_provider_name.return_value = "nvidia"
        from api.main import app

        app.dependency_overrides[get_db] = _override_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()


def auth_headers(email: str = "admin@facultad.edu") -> dict[str, str]:
    token = create_access_token(subject=email)
    return {"Authorization": f"Bearer {token}"}


def test_login_success(client):
    response = client.post(
        "/auth/login",
        json={"email": "admin@facultad.edu", "password": "Password123!"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "access_token" in payload
    assert payload["token_type"] == "bearer"


def test_login_failed(client):
    response = client.post(
        "/auth/login",
        json={"email": "admin@facultad.edu", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_inactive(client, inactive_user):
    response = client.post(
        "/auth/login",
        json={"email": "inactive@facultad.edu", "password": "Password123!"},
    )
    assert response.status_code == 401


def test_protected_without_token(client):
    response = client.get("/admin/dashboard")
    assert response.status_code == 401


def test_protected_with_token(client):
    response = client.get("/admin/dashboard", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["provider"] == "nvidia"


def test_create_admin_user(client):
    response = client.post(
        "/admin/users",
        headers=auth_headers(),
        json={
            "email": "nuevo@facultad.edu",
            "password": "Password123!",
            "full_name": "Nuevo Admin",
            "is_active": True,
        },
    )
    assert response.status_code == 201
    assert response.json()["email"] == "nuevo@facultad.edu"


def test_upload_document_authenticated(client, tmp_path):
    with patch("admin.services.DATA_DIR", tmp_path), patch("admin.router.DATA_DIR", tmp_path):
        files = {
            "file": ("norma.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf"),
        }
        response = client.post(
            "/admin/documents/upload",
            headers=auth_headers(),
            files=files,
        )
    assert response.status_code == 201
    assert response.json()["file_name"] == "norma.pdf"


def test_reindex_authenticated(client):
    fake = SimpleNamespace(
        indexed_documents=2,
        indexed_nodes=10,
        total_documents=2,
        collection_name="faculty_docs",
    )
    with (
        patch("admin.router.apply_runtime_settings"),
        patch("admin.router.apply_embed_model"),
        patch("admin.router.IngestService") as ingest_cls,
    ):
        ingest_cls.return_value.run.return_value = fake
        response = client.post("/admin/reindex", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["indexed_documents"] == 2


def test_chat_test_authenticated(client):
    fake_source = MagicMock()
    fake_source.model_dump.return_value = {
        "file_name": "norma.pdf",
        "page_label": "1",
        "score": 0.9,
    }
    fake_response = SimpleNamespace(answer="Respuesta de prueba", sources=[fake_source])
    with patch("admin.router.ChatService") as chat_cls, patch(
        "admin.router.get_active_llm_model", return_value="meta/llama-3.1-8b-instruct"
    ):
        chat_cls.return_value.reply.return_value = fake_response
        response = client.post(
            "/admin/chat/test",
            headers=auth_headers(),
            json={"message": "Hola", "session_id": "admin-test"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Respuesta de prueba"
    assert payload["provider"] == "nvidia"


def test_settings_update_invalid_provider(client):
    response = client.put(
        "/admin/settings",
        headers=auth_headers(),
        json={"provider": "openai"},
    )
    assert response.status_code == 422


def test_settings_get_and_update(client):
    with patch("admin.router.apply_runtime_settings"):
        response = client.put(
            "/admin/settings",
            headers=auth_headers(),
            json={"provider": "gemini", "llm_model": "gemini-2.5-flash", "similarity_top_k": 4},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "gemini"
    assert payload["similarity_top_k"] == 4

    got = client.get("/admin/settings", headers=auth_headers())
    assert got.status_code == 200
    assert got.json()["provider"] == "gemini"


def test_branding_public_and_update(client):
    public = client.get("/admin/branding")
    assert public.status_code == 200
    assert public.json()["primary_color"] == "#00407d"

    with patch("admin.router.apply_runtime_settings"):
        response = client.put(
            "/admin/settings",
            headers=auth_headers(),
            json={
                "logo_url": "https://example.com/logo-facultad.png",
                "primary_color": "#003366",
                "accent_color": "#ff6600",
                "brand_name": "Facultad IA",
                "brand_subtitle": "Panel",
            },
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["logo_url"].endswith("logo-facultad.png")
    assert payload["primary_color"] == "#003366"

    branding = client.get("/admin/branding")
    assert branding.status_code == 200
    assert branding.json()["brand_name"] == "Facultad IA"
    assert branding.json()["accent_color"] == "#ff6600"


def test_api_keys_encrypted_not_returned(client, db_session):
    from admin.models import ChatbotAdminSettings
    from admin.runtime_keys import get_db_nvidia_api_key, set_db_api_keys
    from admin.secrets_crypto import decrypt_secret
    from config import get_nvidia_api_key

    with patch("admin.router.apply_runtime_settings"):
        response = client.put(
            "/admin/settings",
            headers=auth_headers(),
            json={"nvidia_api_key": "nvapi-test-secret-key-123"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["nvidia_api_key_set"] is True
    assert "nvidia_api_key" not in payload
    assert "nvapi-test-secret" not in str(payload)

    row = db_session.query(ChatbotAdminSettings).first()
    assert row is not None
    assert row.nvidia_api_key_enc
    assert "nvapi-test-secret" not in row.nvidia_api_key_enc
    assert decrypt_secret(row.nvidia_api_key_enc) == "nvapi-test-secret-key-123"

    set_db_api_keys(gemini=None, nvidia=decrypt_secret(row.nvidia_api_key_enc))
    assert get_nvidia_api_key() == "nvapi-test-secret-key-123"
    assert get_db_nvidia_api_key() == "nvapi-test-secret-key-123"

    with patch("admin.router.apply_runtime_settings"):
        cleared = client.put(
            "/admin/settings",
            headers=auth_headers(),
            json={"clear_nvidia_api_key": True},
        )
    assert cleared.status_code == 200
    assert cleared.json()["nvidia_api_key_set"] is False
