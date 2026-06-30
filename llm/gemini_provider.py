"""Adaptador LLM para Google Gemini (Google AI Studio)."""

from __future__ import annotations

from llama_index.core import Settings
from llama_index.llms.google_genai import GoogleGenAI


class GeminiLLMProvider:
    """Configura GoogleGenAI como LLM de LlamaIndex."""

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("Variable de entorno GEMINI_API_KEY no configurada.")
        self._api_key = api_key
        self._model = model

    def configure_llm(self) -> None:
        Settings.llm = GoogleGenAI(model=self._model, api_key=self._api_key)

    def get_provider_name(self) -> str:
        return "gemini"
