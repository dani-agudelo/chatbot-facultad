"""Configuracion admin: JWT, PostgreSQL y seed."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AdminSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/chatbot_admin"
    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 12
    admin_email: str = "admin@facultad.local"
    admin_password: str = "ChangeMe123!"
    admin_full_name: str = "Administrador Facultad"
    admin_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_mb: int = 25

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.admin_cors_origins.split(",") if item.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_admin_settings() -> AdminSettings:
    return AdminSettings()


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", get_admin_settings().database_url).strip()
