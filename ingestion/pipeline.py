"""Funciones de pipeline de ingestion"""

from __future__ import annotations

import logging
import time
from threading import Lock

from llama_index.core import Settings
from llama_index.core.ingestion import IngestionCache, IngestionPipeline
from llama_index.core.ingestion.pipeline import DocstoreStrategy
from llama_index.core.schema import BaseNode, Document
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.vector_stores.types import BasePydanticVectorStore

from config import DOCSTORE_PATH
from ingestion.loader import load_pdf_documents
from ingestion.node_parsers import get_sentence_splitter

logger = logging.getLogger(__name__)

_INGESTION_CACHE: IngestionCache | None = None
_INGESTION_CACHE_LOCK = Lock()
_DOCSTORE: SimpleDocumentStore | None = None
_DOCSTORE_LOCK = Lock()


def get_ingestion_cache() -> IngestionCache:
    """ Devuelve un cache de ingesta singleton para este proceso.

    Returns:
        IngestionCache: Cache compartido utilizado por la pipeline de ingesta.
    """
    global _INGESTION_CACHE
    with _INGESTION_CACHE_LOCK:
        if _INGESTION_CACHE is None:
            _INGESTION_CACHE = IngestionCache()
    return _INGESTION_CACHE


def get_docstore() -> SimpleDocumentStore:
    """Return a process singleton document store with disk persistence."""
    global _DOCSTORE
    with _DOCSTORE_LOCK:
        if _DOCSTORE is None:
            if DOCSTORE_PATH.exists():
                _DOCSTORE = SimpleDocumentStore.from_persist_path(str(DOCSTORE_PATH))
            else:
                _DOCSTORE = SimpleDocumentStore()
    return _DOCSTORE


def run_ingestion_pipeline(
    documents: list[Document],
    vector_store: BasePydanticVectorStore | None = None,
) -> list[BaseNode]:
    """Ejecuta la pipeline de ingesta con caching para parsing y embeddings.

    Args:
        documents: Documentos de origen a transformar.

    Returns:
        list[BaseNode]: Nodos transformados listos para indexar.
    """
    pipeline = IngestionPipeline(
        transformations=[
            get_sentence_splitter(),
            Settings.embed_model,
        ],
        cache=get_ingestion_cache(),
        docstore=get_docstore(),
        docstore_strategy=DocstoreStrategy.UPSERTS_AND_DELETE,
        vector_store=vector_store,
    )

    started = time.perf_counter()
    logger.info(
        "event=pipeline_start documents=%s batch_size=%s",
        len(documents),
        getattr(Settings.embed_model, "embed_batch_size", "?"),
    )
    nodes = pipeline.run(documents=documents, show_progress=True)
    elapsed = time.perf_counter() - started

    persist_started = time.perf_counter()
    get_docstore().persist(str(DOCSTORE_PATH))
    persist_elapsed = time.perf_counter() - persist_started

    logger.info(
        "event=pipeline_complete nodes=%s elapsed_seconds=%.2f persist_seconds=%.3f",
        len(nodes),
        elapsed,
        persist_elapsed,
    )
    return nodes


def enrich_node_metadata(
    nodes: list[BaseNode],
    documents: list[Document],
) -> list[BaseNode]:
    """Asegura que cada nodo incluya metadatos estandarizados de origen.

    Args:
        nodes: Nodos generados a partir de documentos de origen.
        documents: Documentos originales utilizados para crear los nodos.

    Returns:
        list[BaseNode]: Nodos con `file_name` y `page_label`.
    """
    documents_by_id = {
        document.doc_id: document for document in documents if getattr(document, "doc_id", None)
    }

    for node in nodes:
        source_document = documents_by_id.get(node.ref_doc_id)
        node.metadata = dict(node.metadata or {})

        file_name = (
            node.metadata.get("file_name")
            or (source_document.metadata.get("file_name") if source_document else None)
            or "desconocido.pdf"
        )
        page_label = (
            node.metadata.get("page_label")
            or (source_document.metadata.get("page_label") if source_document else None)
            or "N/A"
        )

        node.metadata["file_name"] = str(file_name)
        node.metadata["page_label"] = str(page_label)

    return nodes


def load_and_prepare_nodes(
    vector_store: BasePydanticVectorStore | None = None,
) -> tuple[list[Document], list[BaseNode]]:
    """Carga los documentos PDF de origen y los convierte en nodos.

    Returns:
        tuple[list[Document], list[BaseNode]]: Documentos cargados y nodos con metadatos.
    """
    documents = load_pdf_documents()
    nodes = run_ingestion_pipeline(documents, vector_store=vector_store)
    enriched_nodes = enrich_node_metadata(nodes, documents)
    return documents, enriched_nodes
