"""Reranking local."""

from __future__ import annotations

from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.postprocessor.types import BaseNodePostprocessor

from config import get_chat_similarity_top_k, get_rerank_model_name, is_rerank_enabled

_RERANK_INSTANCE: BaseNodePostprocessor | None = None


def get_rerank_postprocessors() -> list[BaseNodePostprocessor]:
    """Devuelve postprocesadores de rerank activos para el chat engine."""
    global _RERANK_INSTANCE

    if not is_rerank_enabled():
        return []

    if _RERANK_INSTANCE is None:
        _RERANK_INSTANCE = SentenceTransformerRerank(
            model=get_rerank_model_name(),
            top_n=get_chat_similarity_top_k(),
        )

    return [_RERANK_INSTANCE]


def reset_rerank_postprocessor() -> None:
    """Reinicia el reranker (por ejemplo tras cambiar configuracion)."""
    global _RERANK_INSTANCE
    _RERANK_INSTANCE = None
