"""Contrato comun para proveedores de LLM."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Adaptador de LLM para LlamaIndex"""

    def configure_llm(self) -> None:
        """Configura Settings con el cliente del proveedor."""
        ...

    def get_provider_name(self) -> str:
        """Identificador del proveedor: gemini | nvidia."""
        ...
