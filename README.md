# RAG para documentos universitarios

API en **FastAPI** + **LlamaIndex** + **ChromaDB** para consultar documentos universitarios. El LLM es **Google Gemini**; los embeddings se calculan con la **API de NVIDIA** (modelo configurable, por defecto `baai/bge-m3`).

## Estructura del proyecto

```text
chatbot-facultad/
├── api/
│   ├── main.py
│   └── schemas.py
├── generation/
│   ├── prompt.py
│   └── query_engine.py
├── carga_documentos/
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

---

## Requisitos

- **Python 3.10+**
- Cuenta en [Google AI Studio](https://aistudio.google.com/) → `GEMINI_API_KEY`
- Cuenta en [NVIDIA Build](https://build.nvidia.com/) → `NVIDIA_API_KEY`

---

## Instalación

```bash
python -m venv .venv
source .venv/Scripts/activate  
pip install -r requirements.txt
```

---

## Variables de entorno (`.env`)

Crea `.env` en la raíz del proyecto.

### Obligatorias

```env
GEMINI_API_KEY=tu_clave_de_google_ai_studio
NVIDIA_API_KEY=tu_clave_de_build_nvidia_com
```

### Opcionales

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `EMBED_MODEL` | Modelo de embeddings en el catálogo NVIDIA | `baai/bge-m3` |
| `EMBED_BATCH_SIZE` | Textos por request (máx. 259 en la API NVIDIA) | `32` |
| `CHAT_SIMILARITY_TOP_K` | Chunks finales al LLM tras rerank (1–20) | `5` |
| `RETRIEVAL_CANDIDATES` | Candidatos vectoriales antes de rerank | `10` |
| `RERANK_ENABLED` | Activa rerank local (`true`/`false`) | `true` |
| `RERANK_MODEL` | Modelo cross-encoder local (sin coste LLM) | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `CHAT_MEMORY_TOKEN_LIMIT` | Límite de tokens del historial (condense) | `3500` |
| `SESSION_TTL_HOURS` | TTL de sesiones en memoria | `24` |
| `LOG_RETENTION_DAYS` | Días de retención de `logs/log-*.log` | `30` |

Ejemplo para otro modelo del catálogo:

```env
EMBED_MODEL=nvidia/nv-embedqa-e5-v5
```

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
| `GET` | `/health` | Estado del servicio |
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
| `LLM_MODEL` | `gemini-2.5-flash` | Nombre de modelo para la API de Google GenAI |
| `DEFAULT_EMBED_MODEL` | `baai/bge-m3` | Multilingüe; configurable con `EMBED_MODEL` |
| `DEFAULT_CHAT_SIMILARITY_TOP_K` | `5` | Sobrescribible con env `CHAT_SIMILARITY_TOP_K` (1–20) |
| `CHROMA_COLLECTION` | `faculty_docs` | Nombre de la colección en Chroma |

---

## Comportamiento del asistente

Definido en `generation/prompt.py`:

- Responde solo con información **recuperada** de los documentos indexados.
- Si la respuesta no está en el contexto recuperado, debe responder exactamente: **"No tengo esa información en los documentos."**
