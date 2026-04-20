"""Helpers post-procesamiento para las salidas de retrieval."""

from __future__ import annotations

from typing import Any

from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.schema import NodeWithScore


def get_similarity_postprocessor(similarity_cutoff: float = 0.55) -> SimilarityPostprocessor:
    """Crea un postprocessor basado en similitud de nodos.

    Args:
        similarity_cutoff: Puntuacion minima de similitud para mantener un nodo.

    Returns:
        SimilarityPostprocessor: Postprocessor configurado.
    """
    return SimilarityPostprocessor(similarity_cutoff=similarity_cutoff)


def extract_source_metadata(source_nodes: list[NodeWithScore] | None) -> list[dict[str, Any]]:
    """Extrae metadatos listos para citacion desde los nodos de origen.

    Args:
        source_nodes: Nodos de origen adjuntos a una respuesta de chat.

    Returns:
        list[dict[str, Any]]: Fuentes duplicadas con archivo, pagina y puntuacion.
    """
    if not source_nodes:
        return []

    sources: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for source in source_nodes:
        metadata = source.node.metadata or {}
        file_name = str(metadata.get("file_name", "desconocido.pdf"))
        page_label = str(metadata.get("page_label", "N/A"))
        key = (file_name, page_label)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "file_name": file_name,
                "page_label": page_label,
                "score": source.score,
            }
        )
    return sources
