"""Creacion, helpers de persistencia de indices construidos en Chroma."""

from __future__ import annotations

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import BaseNode
from llama_index.vector_stores.chroma import ChromaVectorStore

from config import CHROMA_COLLECTION, configure_settings
from storage.chroma_store import get_or_create_collection, reset_collection


def get_vector_store(collection_name: str = CHROMA_COLLECTION) -> ChromaVectorStore:
    """Crea un wrapper de vector store Chroma desde una coleccion.

    Args:
        collection_name: Nombre de la coleccion Chroma.

    Returns:
        ChromaVectorStore: Adaptador de vector store LlamaIndex.
    """
    collection = get_or_create_collection(collection_name=collection_name)
    return ChromaVectorStore(chroma_collection=collection)


def get_or_create_index(collection_name: str = CHROMA_COLLECTION) -> VectorStoreIndex:
    """Crea un objeto indice vinculado al vector store persistido.

    Args:
        collection_name: Nombre de la coleccion Chroma.

    Returns:
        VectorStoreIndex: Indice conectado al almacenamiento persistido de Chroma.
    """
    configure_settings()
    vector_store = get_vector_store(collection_name=collection_name)
    return VectorStoreIndex.from_vector_store(vector_store=vector_store)


def rebuild_index(
    nodes: list[BaseNode],
    collection_name: str = CHROMA_COLLECTION,
) -> VectorStoreIndex:
    """Recrea la coleccion de vector store e indexa todos los nodos.

    Args:
        nodes: Nodos a insertar en el indice vectorial.
        collection_name: Nombre de la coleccion Chroma.

    Returns:
        VectorStoreIndex: Indice reconstruido que contiene los nodos proporcionados.
    """
    configure_settings()
    collection = reset_collection(collection_name=collection_name)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex(nodes=[], storage_context=storage_context)
    if nodes:
        index.insert_nodes(nodes)
    return index


def delete_nodes_for_files(
    file_names: list[str],
    collection_name: str = CHROMA_COLLECTION,
) -> int:
    """Elimina nodos en Chroma asociados a una lista de archivos.

    Args:
        file_names: Lista de nombres de archivo a eliminar del indice.
        collection_name: Nombre de la coleccion Chroma.

    Returns:
        int: Cantidad de archivos para los que se intento borrar nodos.
    """
    if not file_names:
        return 0

    collection = get_or_create_collection(collection_name=collection_name)
    for file_name in file_names:
        try:
            collection.delete(where={"file_name": file_name})
        except Exception:
            collection.delete(where={"file_name": {"$eq": file_name}})
    return len(file_names)


def upsert_incremental_nodes(
    nodes: list[BaseNode],
    changed_file_names: list[str],
    removed_file_names: list[str],
    collection_name: str = CHROMA_COLLECTION,
) -> VectorStoreIndex:
    """Actualiza incrementalmente el indice sin reiniciar la coleccion completa.

    Args:
        nodes: Nodos de documentos nuevos/modificados.
        changed_file_names: Archivos que deben reindexarse.
        removed_file_names: Archivos eliminados del directorio fuente.
        collection_name: Nombre de la coleccion Chroma.

    Returns:
        VectorStoreIndex: Indice listo para consultas tras la actualizacion.
    """
    configure_settings()
    files_to_delete = list(dict.fromkeys([*changed_file_names, *removed_file_names]))
    delete_nodes_for_files(file_names=files_to_delete, collection_name=collection_name)

    vector_store = get_vector_store(collection_name=collection_name)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
    if nodes:
        index.insert_nodes(nodes)
    return index
