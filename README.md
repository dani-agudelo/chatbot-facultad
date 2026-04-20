# RAG para documentos universitarios

Sistema RAG en Python usando LlamaIndex y ChromaDB.

## Estructura del proyecto

```text
chatbot-facultad/
├── api/
│   ├── main.py
│   └── schemas.py
├── generation/
│   ├── prompt.py
│   └── query_engine.py
├── ingestion/
│   ├── loader.py
│   ├── node_parsers.py
│   └── pipeline.py
├── retrieval/
│   ├── postprocessor.py
│   └── retriever.py
├── storage/
│   ├── chroma_store.py
│   └── index_store.py
├── data/              # PDFs universitarios
├── chroma_db/         # persistencia local de Chroma
├── config.py
└── requirements.txt
```

## Requisitos

- Python 3.10+
- Clave de Google AI Studio (`GEMINI_API_KEY`)
- Embeddings locales con HuggingFace (`models/multilingual-e5-large` por defecto)

Instalación (desde `requirements.txt`):

```bash
python -m venv .venv
source .venv/Scripts/activate   
pip install -r requirements.txt
```

## Configuración

1. Crea un archivo `.env` en la raíz del proyecto.
2. Define la variable obligatoria:

```env
GEMINI_API_KEY=tu_api_key
```

3. Opcional: cambia el modelo local de embeddings (por defecto se usa `models/multilingual-e5-large`):

```env
LOCAL_EMBED_MODEL=models/multilingual-e5-large
```

## Uso

### 1) Iniciar API

```bash
uvicorn api.main:app --reload
```

### 2) Ingestar documentos (PDFs en `data/`)

```bash
curl -X POST http://127.0.0.1:8000/ingest
```

La ingesta es incremental: solo reindexa PDFs nuevos/actualizados y limpia del indice los archivos eliminados de `data/`.

### 3) Consultar por chat con memoria por sesión

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"alumno-1\",\"message\":\"¿Cuántos créditos necesito para titularme?\"}"
```

## Endpoints

- `GET /health`: estado del servicio.
- `POST /ingest`: ingesta incremental de PDFs en `data/`.
- `POST /chat`: responde preguntas con RAG y devuelve fuentes.
- `GET /swagger`: documentacion Swagger UI.
- `GET /redoc`: documentacion alternativa ReDoc.

## Comportamiento del asistente

- Responde solo con información de los documentos indexados.
- Debe citar fuentes en formato como: `Según el archivo X, página Y...`.
- Si no encuentra evidencia en el contexto recuperado, debe responder: `No tengo esa información en los reglamentos`.
