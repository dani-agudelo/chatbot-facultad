"""Configuracion centralizada para la aplicacion RAG."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.google_genai import GoogleGenAI

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"
INGESTION_STATE_FILE = CHROMA_DIR / "ingestion_state.json"

CHROMA_COLLECTION = "faculty_docs"
CHUNK_SIZE = 1024
CHUNK_OVERLAP = 200

LLM_MODEL = "gemini-2.5-flash"
DEFAULT_LOCAL_EMBED_MODEL = str(BASE_DIR / "models" / "multilingual-e5-large")


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


def configure_settings() -> None:
    """Configura las configuraciones globales de LlamaIndex para Gemini y embeddings.

    Raises:
        ValueError: Si GEMINI_API_KEY falta.
    """
    ensure_runtime_directories()
    api_key = get_gemini_api_key()
    local_embed_model = os.getenv("LOCAL_EMBED_MODEL", DEFAULT_LOCAL_EMBED_MODEL).strip()
    Settings.llm = GoogleGenAI(model=LLM_MODEL, api_key=api_key)
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=local_embed_model,
    )
