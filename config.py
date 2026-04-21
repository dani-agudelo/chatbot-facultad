"""Configuracion centralizada para la aplicacion RAG."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.nvidia import NVIDIAEmbedding
from llama_index.llms.google_genai import GoogleGenAI

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"
DOCSTORE_PATH = CHROMA_DIR / "docstore.json"

CHROMA_COLLECTION = "faculty_docs"

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

LLM_MODEL = "gemini-2.5-flash"

DEFAULT_EMBED_MODEL = "baai/bge-m3"

DEFAULT_EMBED_BATCH_SIZE = 32


def ensure_runtime_directories() -> None:
    """Crea directorios requeridos por la aplicacion."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)


def get_gemini_api_key() -> str:
    """Devuelve la API key de Gemini desde las variables de entorno.

    Returns:
        str: La API key de Gemini configurada.

    Raises:
        ValueError: Si GEMINI_API_KEY falta.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY environment variable.")
    return api_key


def get_nvidia_api_key() -> str:
    """Devuelve la API key de NVIDIA desde el entorno.

    Returns:
        str: La API key de NVIDIA configurada.

    Raises:
        ValueError: Si NVIDIA_API_KEY falta.
    """
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing NVIDIA_API_KEY environment variable.")
    return api_key


_CONFIGURED: bool = False


def configure_settings() -> None:
    """Configura Settings de LlamaIndex una unica vez.

    Raises:
        ValueError: Si GEMINI_API_KEY o NVIDIA_API_KEY faltan.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    ensure_runtime_directories()
    gemini_api_key = get_gemini_api_key()
    nvidia_api_key = get_nvidia_api_key()
    embed_model_name = os.getenv("EMBED_MODEL", DEFAULT_EMBED_MODEL).strip()
    embed_batch_size = int(os.getenv("EMBED_BATCH_SIZE", str(DEFAULT_EMBED_BATCH_SIZE)))

    Settings.llm = GoogleGenAI(model=LLM_MODEL, api_key=gemini_api_key)
    Settings.embed_model = NVIDIAEmbedding(
        model=embed_model_name,
        api_key=nvidia_api_key,
        embed_batch_size=embed_batch_size,
        truncate="END",
    )
    _CONFIGURED = True
