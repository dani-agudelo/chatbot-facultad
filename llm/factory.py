"""Factory de proveedores LLM segun LLM_PROVIDER."""

from __future__ import annotations

import os

from config import _load_env, get_gemini_api_key, get_nvidia_api_key
from llm.base import LLMProvider
from llm.gemini_provider import GeminiLLMProvider

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_NVIDIA_MODEL = "meta/llama-3.1-8b-instruct"

_SUPPORTED_PROVIDERS = ("gemini", "nvidia")


def _get_llm_model(default: str) -> str:
    _load_env()
    raw = os.getenv("LLM_MODEL", default).strip()
    return raw or default


def _get_nvidia_llm_base_url() -> str | None:
    _load_env()
    raw = os.getenv("NVIDIA_LLM_BASE_URL", "").strip()
    return raw or None


def get_llm_provider() -> LLMProvider:
    """Devuelve el adaptador LLM configurado por LLM_PROVIDER."""
    _load_env()
    provider = os.getenv("LLM_PROVIDER", "nvidia").strip().lower()

    if provider == "gemini":
        return GeminiLLMProvider(
            api_key=get_gemini_api_key(),
            model=_get_llm_model(DEFAULT_GEMINI_MODEL),
        )

    if provider == "nvidia":
        from llm.nvidia_provider import NvidiaLLMProvider

        return NvidiaLLMProvider(
            api_key=get_nvidia_api_key(),
            model=_get_llm_model(DEFAULT_NVIDIA_MODEL),
            base_url=_get_nvidia_llm_base_url(),
        )

    supported = " | ".join(_SUPPORTED_PROVIDERS)
    raise ValueError(
        f"LLM_PROVIDER '{provider}' no soportado. Usa: {supported}"
    )
