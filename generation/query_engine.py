"""Construccion de chat engine para RAG conversacional."""

from __future__ import annotations

from llama_index.core import Settings
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core.memory import ChatMemoryBuffer

from generation.prompt import SYSTEM_PROMPT
from retrieval.retriever import build_retriever
from storage.index_store import get_or_create_index

_SESSION_MEMORIES: dict[str, ChatMemoryBuffer] = {}


def get_session_memory(session_id: str) -> ChatMemoryBuffer:
    """Obtiene o crea memoria de chat para una sesion especifica.

    Args:
        session_id: Identificador de una conversacion de usuario.

    Returns:
        ChatMemoryBuffer: Objeto de memoria especifica para la sesion.
    """
    if session_id not in _SESSION_MEMORIES:
        _SESSION_MEMORIES[session_id] = ChatMemoryBuffer.from_defaults(token_limit=6000)
    return _SESSION_MEMORIES[session_id]


def get_chat_engine(
    session_id: str,
    similarity_top_k: int = 5,
) -> CondensePlusContextChatEngine:
    """Construye un chat engine conversacional con retrieval y memoria.

    Args:
        session_id: Identificador estable para la persistencia de memoria.
        similarity_top_k: Numero de nodos a recuperar por consulta.

    Returns:
        CondensePlusContextChatEngine: Instancia de chat engine configurada.
    """
    index = get_or_create_index()
    retriever = build_retriever(index=index, similarity_top_k=similarity_top_k)
    memory = get_session_memory(session_id=session_id)

    return CondensePlusContextChatEngine.from_defaults(
        retriever=retriever,
        llm=Settings.llm,
        memory=memory,
        system_prompt=SYSTEM_PROMPT,
    )
