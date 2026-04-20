"""Utilidades para cargar los documentos PDF de origen."""

from __future__ import annotations

import hashlib
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


def compute_file_sha256(file_path: Path) -> str:
    """Calcula el hash SHA-256 de un archivo.

    Args:
        file_path: Ruta absoluta al archivo.

    Returns:
        str: Hash SHA-256 en hexadecimal.
    """
    hasher = hashlib.sha256()
    with file_path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


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
        required_exts=[".pdf"],
        filename_as_id=True,
    )
    documents = reader.load_data()
    for document in documents:
        file_name = document.metadata.get("file_name")
        if not file_name:
            file_path = document.metadata.get("file_path", "")
            document.metadata["file_name"] = Path(file_path).name or "desconocido.pdf"
    return documents


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
