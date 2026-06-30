flowchart TD
    docs[Documentos PDF] --> chunker[Chunking]
    chunker --> embedDocs[Embeddings NVIDIA]
    embedDocs --> chroma[(ChromaDB)]

    userQ[PreguntaUsuario] --> condense[CondensePlusContext]
    userQ --> embedQ[Embedding consulta]
    embedQ --> retriever[BusquedaSimilitudTopK]
    chroma --> retriever

    retriever --> context[ChunksRecuperados]
    condense --> llm[LLM gemini o NVIDIA NIM]
    context --> llm
    llm --> answer[RespuestaConFuentes]

## Lectura del diagrama

- **Embeddings NVIDIA** se usan para documentos (ingesta) y para la pregunta (chat).
- Con eso se hace búsqueda vectorial en Chroma (`CHAT_SIMILARITY_TOP_K` chunks).
- El **LLM** (`LLM_PROVIDER=gemini|nvidia`) condensa el historial y genera la respuesta con el contexto recuperado.
- El LLM no busca en el corpus; solo redacta con los fragmentos que devuelve el retriever.
