"""Fabrica de chat engines con retriever cacheado y rerank opcional."""

from __future__ import annotations

from functools import lru_cache

from llama_index.core import Settings
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core.memory import ChatMemoryBuffer

from config import get_retrieval_candidates
from generation.prompt import SYSTEM_PROMPT
from retrieval.rerank import get_rerank_postprocessors
from retrieval.retriever import build_retriever
from storage.index_cache import get_shared_index


@lru_cache(maxsize=1)
def get_shared_retriever() -> BaseRetriever:
    """Retriever singleton; se invalida tras re-ingesta."""
    index = get_shared_index()
    return build_retriever(
        index=index,
        similarity_top_k=get_retrieval_candidates(),
    )


def reset_shared_retriever() -> None:
    """Limpia el retriever cacheado para reconstruirlo con el indice nuevo."""
    get_shared_retriever.cache_clear()


def build_chat_engine(memory: ChatMemoryBuffer) -> CondensePlusContextChatEngine:
    """Construye un motor conversacional con condense, memoria y rerank local."""
    return CondensePlusContextChatEngine.from_defaults(
        retriever=get_shared_retriever(),
        llm=Settings.llm,
        memory=memory,
        system_prompt=SYSTEM_PROMPT,
        node_postprocessors=get_rerank_postprocessors(),
    )
