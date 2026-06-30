"""Adaptador LLM para NVIDIA Build / NIM (llama-index-llms-nvidia)."""

from __future__ import annotations

from llama_index.core import Settings
from llama_index.llms.nvidia import NVIDIA


class NvidiaLLMProvider:
    """Configura NVIDIA NIM como LLM de LlamaIndex."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Variable de entorno NVIDIA_API_KEY no configurada.")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    def configure_llm(self) -> None:
        kwargs: dict[str, object] = {
            "model": self._model,
            "api_key": self._api_key,
            "is_chat_model": True,
        }
        if self._base_url:
            kwargs["base_url"] = self._base_url
        Settings.llm = NVIDIA(**kwargs)

    def get_provider_name(self) -> str:
        return "nvidia"
