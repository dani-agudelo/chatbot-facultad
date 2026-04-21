"""Utilidades para cargar los documentos PDF de origen."""

from __future__ import annotations

from pathlib import Path

from llama_index.core import SimpleDirectoryReader
from llama_index.core.schema import Document

from config import DATA_DIR


def list_pdf_files(data_dir: Path = DATA_DIR) -> list[Path]:
    """Lista archivos PDF en el directorio de datos.

    Args:
        data_dir: Directorio que contiene los documentos PDF de la universidad.

    Returns:
        list[Path]: Rutas ordenadas de los PDFs encontrados.
    """
    return sorted(path for path in data_dir.glob("*.pdf") if path.is_file())


def load_pdf_documents_from_paths(file_paths: list[Path]) -> list[Document]:
    """Carga documentos PDF a partir de rutas explicitas.

    Args:
        file_paths: Rutas de archivos PDF a cargar.

    Returns:
        list[Document]: Documentos cargados con metadatos.
    """
    if not file_paths:
        return []

    reader = SimpleDirectoryReader(
        input_files=[str(path) for path in file_paths],
        filename_as_id=True,
    )
    return reader.load_data()


def load_pdf_documents(data_dir: Path = DATA_DIR) -> list[Document]:
    """Carga todos los documentos PDF desde el directorio de datos configurado.

    Args:
        data_dir: Directorio que contiene los documentos PDF de la universidad.

    Returns:
        list[Document]: Documentos cargados con metadatos.

    Raises:
        ValueError: Si no se encuentran documentos PDF.
    """
    file_paths = list_pdf_files(data_dir=data_dir)
    documents = load_pdf_documents_from_paths(file_paths)

    if not documents:
        raise ValueError(f"No se encontraron documentos PDF en {data_dir}.")
    return documents
