"""Punto de entrada FastAPI: chat publico + panel de administracion."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from admin.router import admin_router, auth_router
from admin.services import load_api_keys_from_db
from admin.settings import get_admin_settings
from api.deps import get_chat_service
from api.exceptions import register_exception_handlers
from api.schemas import ChatRequest, ChatResponse
from config import CHROMA_COLLECTION, configure_settings, get_active_llm_model
from llm.factory import get_llm_provider
from logging_config import PUBLIC_ERROR_MESSAGE, setup_logging
from services.chat_service import ChatService

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "health", "description": "Estado de la API"},
    {"name": "chat", "description": "Consultas conversacionales con RAG y citas de fuentes."},
    {"name": "admin-auth", "description": "Autenticacion del panel de administracion."},
    {"name": "admin", "description": "Operaciones administrativas (documentos, reindex, settings)."},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Inicializa configuracion, logging y dependencias al arranque."""
    load_api_keys_from_db()
    configure_settings()
    setup_logging()
    provider = get_llm_provider()
    logger.info(
        "event=startup chroma_collection=%s llm_provider=%s",
        CHROMA_COLLECTION,
        provider.get_provider_name(),
    )
    yield


app = FastAPI(
    title="Documentos Universitarios RAG API",
    description="Servicio RAG + panel de administracion. La indexacion solo via /admin/reindex.",
    version="1.4.0",
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

admin_settings = get_admin_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=admin_settings.cors_origins_list or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "model": get_active_llm_model()}


def _chat_sync(service: ChatService, request: ChatRequest) -> ChatResponse:
    return service.reply(request)


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
