"""Punto de entrada FastAPI para carga de documentos y chat."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from api.deps import get_chat_service, get_ingest_service
from api.exceptions import register_exception_handlers
from api.schemas import ChatRequest, ChatResponse, IngestResponse
from config import CHROMA_COLLECTION, configure_settings
from logging_config import PUBLIC_ERROR_MESSAGE, setup_logging
from services.chat_service import ChatService
from services.ingest_service import IngestService

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "health", "description": "Estado de la API"},
    {"name": "carga_documentos", "description": "Carga e indexacion de documentos en ChromaDB."},
    {"name": "chat", "description": "Consultas conversacionales con RAG y citas de fuentes."},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Inicializa configuracion, logging y dependencias al arranque."""
    configure_settings()
    setup_logging()
    logger.info("event=startup chroma_collection=%s", CHROMA_COLLECTION)
    yield


app = FastAPI(
    title="Documentos Universitarios RAG API",
    description="Servicio RAG soportado por LlamaIndex y ChromaDB.",
    version="1.1.0",
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

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _ingest_sync(service: IngestService) -> IngestResponse:
    try:
        return service.run()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _chat_sync(service: ChatService, request: ChatRequest) -> ChatResponse:
    return service.reply(request)


@app.post("/ingest", response_model=IngestResponse, tags=["carga_documentos"])
async def ingest_documents(
    service: IngestService = Depends(get_ingest_service),
) -> IngestResponse:
    try:
        return await run_in_threadpool(_ingest_sync, service)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("event=ingest_failed error=%s", exc)
        raise HTTPException(status_code=500, detail=PUBLIC_ERROR_MESSAGE) from exc


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        return await run_in_threadpool(_chat_sync, service, request)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "event=chat_failed session_id=%s error=%s",
            request.session_id,
            exc,
        )
        raise HTTPException(status_code=500, detail=PUBLIC_ERROR_MESSAGE) from exc
