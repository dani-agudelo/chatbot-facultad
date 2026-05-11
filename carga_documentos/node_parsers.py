"""Utilidades para parsear los documentos de origen en nodos."""

from __future__ import annotations

from llama_index.core.node_parser import SentenceSplitter

from config import CHUNK_OVERLAP, CHUNK_SIZE


def get_sentence_splitter() -> SentenceSplitter:
    """Crea el splitter de oraciones utilizado al fragmentar documentos.

    Returns:
        SentenceSplitter: Splitter configurado con configuraciones fijas de chunk.
    """
    return SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
