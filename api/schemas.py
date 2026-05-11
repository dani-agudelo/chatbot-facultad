"""Modelos para la API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    """Esquema de respuesta para solicitudes de carga e indexacion."""

    indexed_documents: int
    indexed_nodes: int
    total_documents: int
    collection_name: str


class ChatRequest(BaseModel):
    """Esquema de cuerpo de solicitud para el endpoint de chat."""

    session_id: str = Field(..., min_length=1, description="Identificador de conversacion.")
    message: str = Field(..., min_length=1, description="Pregunta del usuario.")


class SourceItem(BaseModel):
    """Metadatos de citacion devueltos con respuestas del modelo."""

    file_name: str
    page_label: str
    score: float | None = None


class ChatResponse(BaseModel):
    """Esquema de cuerpo de respuesta para el endpoint de chat."""

    answer: str
    sources: list[SourceItem]
