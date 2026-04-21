"""Punto de entrada FastAPI para endpoints de ingestion y chat."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import ChatRequest, ChatResponse, IngestResponse
from config import CHROMA_COLLECTION, configure_settings
from generation.query_engine import get_chat_engine
from ingestion.pipeline import (
    load_and_prepare_nodes,
)
from retrieval.postprocessor import extract_source_metadata
from storage.index_store import get_vector_store

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Estado de la API",
    },
    {
        "name": "ingestion",
        "description": "Carga e indexacion de documentos en ChromaDB.",
    },
    {
        "name": "chat",
        "description": "Consultas conversacionales con RAG y citas de fuentes.",
    },
]

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Inicializa las dependencias de la app una vez por inicio del proceso."""
    configure_settings()
    logger.info("event=startup chroma_collection=%s collection_ready=true", CHROMA_COLLECTION)
    yield

app = FastAPI(
    title="Documentos Universitarios RAG API",
    description="Servicio RAG soportado por LlamaIndex y ChromaDB.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/swagger",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters={
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Devuelve el estado de la API.

    Returns:
        dict[str, str]: Estado de la API.
    """
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse, tags=["ingestion"])
def ingest_documents() -> IngestResponse:
    """Ingesta documentos usando IngestionPipeline + IngestionCache.

    Returns:
        IngestResponse: Metricas de ingestion para documentos e indices.

    Raises:
        HTTPException: Si la ingestion falla o no hay documentos disponibles.
    """
    ingest_started = time.perf_counter()
    try:
        load_started = time.perf_counter()
        vector_store = get_vector_store(collection_name=CHROMA_COLLECTION)
        vector_store_ready_seconds = time.perf_counter() - load_started
        
        pipeline_started = time.perf_counter()
        documents, nodes = load_and_prepare_nodes(vector_store=vector_store)
        pipeline_seconds = time.perf_counter() - pipeline_started
        total_documents = len(documents)
        total_seconds = time.perf_counter() - ingest_started

        logger.info(
            "event=ingest_complete collection=%s documents=%s nodes=%s "
            "vector_store_ready_seconds=%.3f pipeline_seconds=%.3f total_seconds=%.3f",
            CHROMA_COLLECTION,
            total_documents,
            len(nodes),
            vector_store_ready_seconds,
            pipeline_seconds,
            total_seconds,
        )
        return IngestResponse(
            indexed_documents=total_documents,
            indexed_nodes=len(nodes),
            total_documents=total_documents,
            collection_name=CHROMA_COLLECTION,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
def chat(request: ChatRequest) -> ChatResponse:
    """Responde una pregunta del usuario usando RAG.

    Args:
        request: Cuerpo de solicitud de chat del usuario.

    Returns:
        ChatResponse: Respuesta del asistente y fuentes extraidas.

    Raises:
        HTTPException: Si la operacion de chat falla.
    """
    started = time.perf_counter()
    try:
        chat_engine = get_chat_engine(
            session_id=request.session_id,
            similarity_top_k=request.similarity_top_k,
        )
        response = chat_engine.chat(request.message)
        sources = extract_source_metadata(getattr(response, "source_nodes", None))
        total_seconds = time.perf_counter() - started
        logger.info(
            "event=chat_complete session_id=%s top_k=%s sources=%s latency_seconds=%.3f",
            request.session_id,
            request.similarity_top_k,
            len(sources),
            total_seconds,
        )
        return ChatResponse(answer=str(response.response), sources=sources)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc
