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
        list[dict[str, Any]]: Fuentes agrupadas por archivo con paginas y puntuacion.
    """
    if not source_nodes:
        return []

    grouped_sources: dict[str, dict[str, Any]] = {}
    for source in source_nodes:
        metadata = source.node.metadata or {}
        file_name = str(metadata.get("file_name", "desconocido.pdf"))
        page_label = str(metadata.get("page_label", "N/A"))
        score = source.score

        if file_name not in grouped_sources:
            grouped_sources[file_name] = {
                "file_name": file_name,
                "pages": set(),
                "score": score,
            }

        grouped_sources[file_name]["pages"].add(page_label)
        previous_score = grouped_sources[file_name]["score"]
        if previous_score is None or (score is not None and score > previous_score):
            grouped_sources[file_name]["score"] = score

    def page_sort_key(value: str) -> tuple[int, int | str]:
        """Ordena paginas numericas primero y etiquetas no numericas al final."""
        return (0, int(value)) if value.isdigit() else (1, value)

    sources: list[dict[str, Any]] = []
    for grouped in grouped_sources.values():
        sorted_pages = sorted(grouped["pages"], key=page_sort_key)
        sources.append(
            {
                "file_name": grouped["file_name"],
                "page_label": ", ".join(sorted_pages),
                "score": grouped["score"],
            }
        )

    # Conserva primero los archivos con mayor score para mantener relevancia.
    sources.sort(key=lambda item: item["score"] if item["score"] is not None else float("-inf"), reverse=True)
    return sources
