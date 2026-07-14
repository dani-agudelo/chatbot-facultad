"""Schemas Pydantic del panel admin."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_hours: int


class AdminUserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


_HEX = r"^#[0-9A-Fa-f]{6}$"


class BrandingOut(BaseModel):
    logo_url: str = ""
    primary_color: str = "#00407d"
    accent_color: str = "#f27022"
    brand_name: str = "Chatbot Facultad"
    brand_subtitle: str = "Administración"


class SettingsOut(BaseModel):
    provider: Literal["gemini", "nvidia"]
    llm_model: str
    embed_model: str
    similarity_top_k: int
    reindex_required: bool
    last_reindex_at: datetime | None
    last_reindex_result: str | None
    updated_at: datetime | None
    logo_url: str = ""
    primary_color: str = "#00407d"
    accent_color: str = "#f27022"
    brand_name: str = "Chatbot Facultad"
    brand_subtitle: str = "Administración"
    gemini_api_key_set: bool = False
    nvidia_api_key_set: bool = False
    gemini_api_key_env: bool = False
    nvidia_api_key_env: bool = False


class SettingsUpdate(BaseModel):
    provider: Literal["gemini", "nvidia"] | None = None
    llm_model: str | None = Field(default=None, min_length=1, max_length=128)
    embed_model: str | None = Field(default=None, min_length=1, max_length=128)
    similarity_top_k: int | None = Field(default=None, ge=1, le=20)
    logo_url: str | None = Field(default=None, max_length=512)
    primary_color: str | None = Field(default=None, pattern=_HEX)
    accent_color: str | None = Field(default=None, pattern=_HEX)
    brand_name: str | None = Field(default=None, min_length=1, max_length=128)
    brand_subtitle: str | None = Field(default=None, max_length=128)
    # Si se envia texto: cifra y guarda. None = sin cambio.
    gemini_api_key: str | None = Field(default=None, min_length=8, max_length=512)
    nvidia_api_key: str | None = Field(default=None, min_length=8, max_length=512)
    clear_gemini_api_key: bool = False
    clear_nvidia_api_key: bool = False


class DocumentOut(BaseModel):
    file_name: str
    size_bytes: int
    updated_at: datetime


class ReindexResponse(BaseModel):
    indexed_documents: int
    indexed_nodes: int
    total_documents: int
    collection_name: str
    message: str


class AdminChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = Field(default="admin-test", min_length=1)


class AdminChatResponse(BaseModel):
    answer: str
    provider: str
    model: str
    sources: list[dict]
    note: str | None = None


class DashboardOut(BaseModel):
    status: str
    provider: str
    model: str
    documents_count: int
    reindex_required: bool
    last_reindex_at: datetime | None
    last_reindex_result: str | None
