"""Modelos PostgreSQL del panel de administracion."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from admin.db import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    audit_logs: Mapped[list[AdminAuditLog]] = relationship(back_populates="actor")


class ChatbotAdminSettings(Base):
    __tablename__ = "chatbot_admin_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="nvidia")
    llm_model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    embed_model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    similarity_top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    reindex_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_reindex_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reindex_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    primary_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#00407d")
    accent_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#f27022")
    brand_name: Mapped[str] = mapped_column(String(128), nullable=False, default="Chatbot Facultad")
    brand_subtitle: Mapped[str] = mapped_column(String(128), nullable=False, default="Administración")
    gemini_api_key_enc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    nvidia_api_key_enc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    actor: Mapped[AdminUser | None] = relationship(back_populates="audit_logs")
