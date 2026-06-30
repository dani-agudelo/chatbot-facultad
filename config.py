"""Configuracion centralizada para la aplicacion RAG."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.nvidia import NVIDIAEmbedding

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"
DOCSTORE_PATH = CHROMA_DIR / "docstore.json"

CHROMA_COLLECTION = "faculty_docs"

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

DEFAULT_EMBED_MODEL = "baai/bge-m3"
DEFAULT_EMBED_BATCH_SIZE = 32

DEFAULT_CHAT_SIMILARITY_TOP_K = 5
_MAX_CHAT_SIMILARITY_TOP_K = 20

DEFAULT_CHAT_MEMORY_TOKEN_LIMIT = 3500
DEFAULT_SESSION_TTL_HOURS = 24
DEFAULT_LOG_RETENTION_DAYS = 30

_CONFIGURED: bool = False


def _load_env() -> None:
    load_dotenv()


def get_chat_similarity_top_k() -> int:
    """Chunks recuperados por similitud que recibe el LLM (1-20)."""
    _load_env()
    raw = int(os.getenv("CHAT_SIMILARITY_TOP_K", str(DEFAULT_CHAT_SIMILARITY_TOP_K)))
    return max(1, min(_MAX_CHAT_SIMILARITY_TOP_K, raw))


def get_chat_memory_token_limit() -> int:
    _load_env()
    raw = int(os.getenv("CHAT_MEMORY_TOKEN_LIMIT", str(DEFAULT_CHAT_MEMORY_TOKEN_LIMIT)))
    return max(1000, min(6000, raw))


def get_session_ttl_seconds() -> int:
    _load_env()
    hours = float(os.getenv("SESSION_TTL_HOURS", str(DEFAULT_SESSION_TTL_HOURS)))
    return max(1, int(hours * 3600))


def get_log_retention_days() -> int:
    _load_env()
    raw = int(os.getenv("LOG_RETENTION_DAYS", str(DEFAULT_LOG_RETENTION_DAYS)))
    return max(1, raw)


def ensure_runtime_directories() -> None:
    """Crea directorios requeridos por la aplicacion."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)


def get_gemini_api_key() -> str:
    _load_env()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Variable de entorno GEMINI_API_KEY no configurada.")
    return api_key


def get_nvidia_api_key() -> str:
    _load_env()
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Variable de entorno NVIDIA_API_KEY no configurada.")
    return api_key


def configure_settings() -> None:
    """Configura Settings de LlamaIndex una unica vez (LLM + embeddings)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    from llm.factory import get_llm_provider

    ensure_runtime_directories()
    _load_env()

    llm_provider = get_llm_provider()
    llm_provider.configure_llm()

    embed_model_name = os.getenv("EMBED_MODEL", DEFAULT_EMBED_MODEL).strip()
    embed_batch_size = int(os.getenv("EMBED_BATCH_SIZE", str(DEFAULT_EMBED_BATCH_SIZE)))

    Settings.embed_model = NVIDIAEmbedding(
        model=embed_model_name,
        api_key=get_nvidia_api_key(),
        embed_batch_size=embed_batch_size,
        truncate="END",
    )
    _CONFIGURED = True


def get_active_llm_model() -> str:
    """Devuelve el nombre del modelo LLM configurado en Settings."""
    configure_settings()
    llm = Settings.llm
    if llm is None:
        return "unknown"
    model = getattr(llm, "model", None)
    return str(model) if model else "unknown"
