"""Claves API en memoria cargadas desde BD (prioridad sobre .env)."""

from __future__ import annotations

_gemini_db: str | None = None
_nvidia_db: str | None = None


def set_db_api_keys(*, gemini: str | None, nvidia: str | None) -> None:
    global _gemini_db, _nvidia_db
    _gemini_db = (gemini or "").strip() or None
    _nvidia_db = (nvidia or "").strip() or None


def get_db_gemini_api_key() -> str | None:
    return _gemini_db


def get_db_nvidia_api_key() -> str | None:
    return _nvidia_db
