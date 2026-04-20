"""Utilidades para parsear los documentos de origen en nodos."""

from __future__ import annotations

from collections.abc import Sequence

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode, Document

from config import CHUNK_OVERLAP, CHUNK_SIZE


def get_sentence_splitter() -> SentenceSplitter:
    """Crea el splitter de oraciones utilizado durante la ingestion.

    Returns:
        SentenceSplitter: Splitter configurado con configuraciones fijas de chunk.
    """
    return SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


def parse_documents_into_nodes(
    documents: Sequence[Document],
    splitter: SentenceSplitter | None = None,
) -> list[BaseNode]:
    """Parsea los documentos cargados en nodos chunked.

    Args:
        documents: Documentos a dividir en nodos.
        splitter: Opcional para sobreescribir el splitter.

    Returns:
        list[BaseNode]: Nodos chunked generados a partir de los documentos de entrada.
    """
    parser = splitter or get_sentence_splitter()
    return parser.get_nodes_from_documents(list(documents))
