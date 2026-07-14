"""Dependencias inyectables de FastAPI."""

from __future__ import annotations

from functools import lru_cache

from services.chat_service import ChatService


@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    return ChatService()
