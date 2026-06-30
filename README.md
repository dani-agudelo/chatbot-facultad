# RAG para documentos universitarios

API en **FastAPI** + **LlamaIndex** + **ChromaDB** para consultar documentos universitarios. El LLM es configurable (**NVIDIA NIM** por defecto o **Google Gemini**); los embeddings se calculan con la **API de NVIDIA** (modelo configurable, por defecto `baai/bge-m3`).

## Estructura del proyecto

```text
chatbot-facultad/
├── api/
│   ├── main.py
│   ├── deps.py
│   ├── exceptions.py
│   └── schemas.py
├── llm/
│   ├── base.py
│   ├── gemini_provider.py
│   ├── nvidia_provider.py
│   └── factory.py
├── services/
│   ├── chat_service.py
│   └── ingest_service.py
├── generation/
│   ├── engine_factory.py
│   ├── prompt.py
│   └── session_store.py
├── carga_documentos/
│   ├── loader.py
│   ├── node_parsers.py
│   └── pipeline.py
├── retrieval/
│   ├── retriever.py
│   └── sources.py
├── storage/
│   ├── chroma_store.py
│   ├── index_cache.py
│   └── index_store.py
├── tests/
│   └── test_api.py
├── documentation/
│   └── diagram.md
├── data/              # PDFs universitarios (.pdf / .PDF)
├── chroma_db/
├── logs/
├── config.py
├── logging_config.py
└── requirements.txt
```

---

## Requisitos

- **Python 3.10+**
- **Embeddings (siempre):** cuenta en [NVIDIA Build](https://build.nvidia.com/) → `NVIDIA_API_KEY`
- **LLM Gemini:** cuenta en [Google AI Studio](https://aistudio.google.com/) → `GEMINI_API_KEY`
- **LLM NVIDIA:** misma `NVIDIA_API_KEY` del catálogo NIM (modelo en `LLM_MODEL`)

---

## Instalación

```bash
python -m venv .venv
source .venv/Scripts/activate  
pip install -r requirements.txt
```

---

## Variables de entorno (`.env`)

Crea `.env` en la raíz del proyecto (ver `.env.example`).

### Proveedor LLM

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `LLM_PROVIDER` | Proveedor del LLM: `gemini` \| `nvidia` | `nvidia` |
| `LLM_MODEL` | Nombre del modelo según el proveedor | `meta/llama-3.1-8b-instruct` (NVIDIA) o `gemini-2.5-flash` (Gemini) |
| `NVIDIA_LLM_BASE_URL` | URL de NIM self-hosted (solo NVIDIA LLM) | Catálogo NVIDIA |

### Claves API

| Variable | Cuándo es obligatoria |
|----------|----------------------|
| `NVIDIA_API_KEY` | Siempre (embeddings; y LLM si `LLM_PROVIDER=nvidia`) |
| `GEMINI_API_KEY` | Solo si `LLM_PROVIDER=gemini` |

Ejemplo con NVIDIA NIM (por defecto):

```env
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=tu_clave_nvidia
LLM_MODEL=meta/llama-3.1-8b-instruct
```

Ejemplo con Gemini:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=tu_clave_google
NVIDIA_API_KEY=tu_clave_nvidia
LLM_MODEL=gemini-2.5-flash
```

### Opcionales

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `EMBED_MODEL` | Modelo de embeddings en el catálogo NVIDIA | `baai/bge-m3` |
| `EMBED_BATCH_SIZE` | Textos por request (máx. 259 en la API NVIDIA) | `32` |
| `CHAT_SIMILARITY_TOP_K` | Chunks recuperados enviados al LLM (1–20) | `5` |
| `CHAT_MEMORY_TOKEN_LIMIT` | Límite de tokens del historial (condense) | `3500` |
| `SESSION_TTL_HOURS` | TTL de sesiones en memoria | `24` |
| `LOG_RETENTION_DAYS` | Días de retención de `logs/log-*.log` | `30` |

> Si se cambia el modelo de embeddings o el parser de chunks (`CHUNK_SIZE` / `StructuredParagraphNodeParser`), **borrar `chroma_db/`** y volver a ejecutar `/ingest`.

Los logs de WARNING/ERROR se guardan en `logs/log-YYYY-MM-DD.log`.

## Uso

### 1. Colocar PDFs

Copiar los documentos en `data/` con extensión `.pdf`.

### 2. Arrancar la API

```bash
uvicorn api.main:app --reload
```


### 3. Ingesta

```bash
curl -X POST http://127.0.0.1:8000/ingest
```


### 4. Chat (con memoria por sesión)

Mismo `session_id` en varias llamadas = misma conversación.

**Git Bash / macOS / Linux:**

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "alumno-1",
    "message": "¿Qué título otorga la carrera de Ingeniería en Inteligencia Artificial?"
  }'
```

Campos del cuerpo:

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| `session_id` | Sí | Identificador de conversación |
| `message` | Sí | Pregunta del usuario |

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servicio y modelo LLM activo (`status`, `model`) |
| `POST` | `/ingest` | Lee `data/*.pdf`, pipeline, upsert en Chroma |
| `POST` | `/chat` | RAG conversacional + lista de fuentes |
| `GET` | `/swagger` | Swagger UI |
| `GET` | `/redoc` | ReDoc |
| `GET` | `/openapi.json` | Esquema OpenAPI |

---

## Parámetros relevantes (`config.py`)

| Constante | Valor por defecto | Nota |
|-----------|------------------|------|
| `CHUNK_SIZE` | `512` | Alineado con modelos que truncan ~512 tokens |
| `CHUNK_OVERLAP` | `64` | Solape entre chunks |
| `DEFAULT_EMBED_MODEL` | `baai/bge-m3` | Multilingüe; configurable con `EMBED_MODEL` |
| `DEFAULT_CHAT_SIMILARITY_TOP_K` | `5` | Sobrescribible con env `CHAT_SIMILARITY_TOP_K` (1–20) |
| `CHROMA_COLLECTION` | `faculty_docs` | Nombre de la colección en Chroma |

Modelos LLM por defecto en `llm/factory.py`: `meta/llama-3.1-8b-instruct` (NVIDIA), `gemini-2.5-flash` (Gemini).

### Health check

```bash
curl http://127.0.0.1:8000/health
```

Respuesta:

```json
{
  "status": "ok",
  "model": "meta/llama-3.1-8b-instruct"
}
```

---

## Tests

```bash
python -m unittest discover -s tests -v
```

---

## Comportamiento del asistente

Definido en `generation/prompt.py`:

- Responde solo con información **recuperada** de los documentos indexados.
- Si la respuesta no está en el contexto recuperado, debe responder exactamente: **"No tengo esa información en los documentos."**
