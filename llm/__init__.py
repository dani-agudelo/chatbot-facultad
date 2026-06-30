"""Proveedores LLM (adaptador / strategy)."""

from llm.base import LLMProvider
from llm.factory import get_llm_provider

__all__ = ["LLMProvider", "get_llm_provider"]
