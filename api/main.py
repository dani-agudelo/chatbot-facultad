"""Punto de entrada FastAPI para endpoints de ingestion y chat."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import ChatRequest, ChatResponse, IngestResponse
from config import CHROMA_COLLECTION, configure_settings
from generation.query_engine import get_chat_engine
from ingestion.pipeline import (
    compute_current_file_hashes,
    get_incremental_file_changes,
    load_and_prepare_incremental_nodes,
    load_ingestion_state,
    save_ingestion_state,
)
from retrieval.postprocessor import extract_source_metadata
from storage.index_store import upsert_incremental_nodes

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

app = FastAPI(
    title="Documentos Universitarios RAG API",
    description="Servicio RAG soportado por LlamaIndex y ChromaDB.",
    version="1.0.0",
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
    """Ingesta incremental de documentos desde `data/`.

    Returns:
        IngestResponse: Metricas de ingestion incremental para documentos e indices.

    Raises:
        HTTPException: Si la ingestion falla o no hay documentos disponibles.
    """
    try:
        configure_settings()
        previous_hashes = load_ingestion_state()
        current_hashes = compute_current_file_hashes()
        changed_paths, removed_files, new_state = get_incremental_file_changes(
            previous_hashes=previous_hashes,
            current_hashes=current_hashes,
        )

        _documents, nodes = load_and_prepare_incremental_nodes(
            changed_paths=changed_paths,
            current_hashes=current_hashes,
        )
        changed_file_names = [path.name for path in changed_paths]
        upsert_incremental_nodes(
            nodes=nodes,
            changed_file_names=changed_file_names,
            removed_file_names=removed_files,
            collection_name=CHROMA_COLLECTION,
        )
        save_ingestion_state(new_state)

        total_documents = len(current_hashes)
        indexed_documents = len(changed_paths)
        skipped_documents = max(total_documents - indexed_documents, 0)
        return IngestResponse(
            indexed_documents=indexed_documents,
            indexed_nodes=len(nodes),
            removed_documents=len(removed_files),
            skipped_documents=skipped_documents,
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
    try:
        chat_engine = get_chat_engine(
            session_id=request.session_id,
            similarity_top_k=request.similarity_top_k,
        )
        response = chat_engine.chat(request.message)
        sources = extract_source_metadata(getattr(response, "source_nodes", None))
        return ChatResponse(answer=str(response.response), sources=sources)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc
