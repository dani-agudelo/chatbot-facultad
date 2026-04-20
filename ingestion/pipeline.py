"""Funciones de pipeline de ingestion"""

from __future__ import annotations

import json
from pathlib import Path

from llama_index.core.schema import BaseNode, Document

from config import DATA_DIR, INGESTION_STATE_FILE
from ingestion.loader import (
    compute_file_sha256,
    list_pdf_files,
    load_pdf_documents,
    load_pdf_documents_from_paths,
)
from ingestion.node_parsers import parse_documents_into_nodes


def load_ingestion_state(state_file: Path = INGESTION_STATE_FILE) -> dict[str, str]:
    """Carga el estado de hashes procesados de ingesta.

    Args:
        state_file: Ruta al archivo JSON de estado.

    Returns:
        dict[str, str]: Mapa de nombre de archivo a hash SHA-256.
    """
    if not state_file.exists():
        return {}
    with state_file.open("r", encoding="utf-8") as file_obj:
        data = json.load(file_obj)
    return {str(key): str(value) for key, value in data.items()}


def save_ingestion_state(
    state: dict[str, str],
    state_file: Path = INGESTION_STATE_FILE,
) -> None:
    """Guarda el estado de hashes de ingesta.

    Args:
        state: Mapa de nombre de archivo a hash SHA-256.
        state_file: Ruta al archivo JSON de estado.
    """
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.open("w", encoding="utf-8") as file_obj:
        json.dump(state, file_obj, ensure_ascii=True, indent=2)


def compute_current_file_hashes(data_dir: Path = DATA_DIR) -> dict[str, str]:
    """Construye el mapa de hashes SHA-256 de todos los PDFs actuales.

    Args:
        data_dir: Directorio con PDFs de origen.

    Returns:
        dict[str, str]: Mapa de nombre de archivo a hash SHA-256.
    """
    file_hashes: dict[str, str] = {}
    for file_path in list_pdf_files(data_dir=data_dir):
        file_hashes[file_path.name] = compute_file_sha256(file_path)
    return file_hashes


def get_incremental_file_changes(
    previous_hashes: dict[str, str],
    current_hashes: dict[str, str],
    data_dir: Path = DATA_DIR,
) -> tuple[list[Path], list[str], dict[str, str]]:
    """Determina archivos nuevos/actualizados y eliminados.

    Args:
        previous_hashes: Hashes guardados de la ingesta anterior.
        current_hashes: Hashes calculados sobre el estado actual de `data/`.
        data_dir: Directorio con PDFs de origen.

    Returns:
        tuple[list[Path], list[str], dict[str, str]]: Rutas a reindexar, archivos removidos y nuevo estado.
    """
    changed_paths: list[Path] = []
    for file_name, file_hash in current_hashes.items():
        if previous_hashes.get(file_name) != file_hash:
            changed_paths.append(data_dir / file_name)

    removed_files = [file_name for file_name in previous_hashes if file_name not in current_hashes]
    return changed_paths, removed_files, current_hashes


def enrich_node_metadata(
    nodes: list[BaseNode],
    documents: list[Document],
) -> list[BaseNode]:
    """Asegura que cada nodo incluya metadatos estandarizados de origen.

    Args:
        nodes: Nodos generados a partir de documentos de origen.
        documents: Documentos originales utilizados para crear los nodos.

    Returns:
        list[BaseNode]: Nodos con `file_name` y `page_label`.
    """
    documents_by_id = {
        document.doc_id: document for document in documents if getattr(document, "doc_id", None)
    }

    for node in nodes:
        source_document = documents_by_id.get(node.ref_doc_id)
        node.metadata = dict(node.metadata or {})

        file_name = (
            node.metadata.get("file_name")
            or (source_document.metadata.get("file_name") if source_document else None)
            or "desconocido.pdf"
        )
        page_label = (
            node.metadata.get("page_label")
            or (source_document.metadata.get("page_label") if source_document else None)
            or "N/A"
        )

        node.metadata["file_name"] = str(file_name)
        node.metadata["page_label"] = str(page_label)
        if source_document:
            node.metadata["file_hash"] = str(source_document.metadata.get("file_hash", ""))

    return nodes


def load_and_prepare_nodes() -> tuple[list[Document], list[BaseNode]]:
    """Carga los documentos PDF de origen y los convierte en nodos.

    Returns:
        tuple[list[Document], list[BaseNode]]: Documentos cargados y nodos con metadatos.
    """
    documents = load_pdf_documents()
    nodes = parse_documents_into_nodes(documents)
    enriched_nodes = enrich_node_metadata(nodes, documents)
    return documents, enriched_nodes


def load_and_prepare_incremental_nodes(
    changed_paths: list[Path],
    current_hashes: dict[str, str],
) -> tuple[list[Document], list[BaseNode]]:
    """Carga y prepara nodos solo para archivos nuevos/actualizados.

    Args:
        changed_paths: Rutas de PDFs nuevos o modificados.
        current_hashes: Mapa actual de hashes por archivo.

    Returns:
        tuple[list[Document], list[BaseNode]]: Documentos y nodos listos para indexar.
    """
    documents = load_pdf_documents_from_paths(changed_paths)
    for document in documents:
        file_name = str(document.metadata.get("file_name", ""))
        document.metadata["file_hash"] = current_hashes.get(file_name, "")

    nodes = parse_documents_into_nodes(documents)
    enriched_nodes = enrich_node_metadata(nodes, documents)
    return documents, enriched_nodes
