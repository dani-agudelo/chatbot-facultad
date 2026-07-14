# RAG para documentos universitarios

API en **FastAPI** + **LlamaIndex** + **ChromaDB** para consultar documentos universitarios. El LLM es configurable (**NVIDIA NIM** por defecto o **Google Gemini**); los embeddings se calculan con la **API de NVIDIA** (modelo configurable, por defecto `baai/bge-m3`).

Incluye un **panel de administración** documentado en **[ADMIN.md](ADMIN.md)**.

## Estructura del proyecto

```text
chatbot-facultad/
├── api/
│   ├── main.py              
│   ├── deps.py
│   ├── exceptions.py
│   └── schemas.py
├── admin/                 
│   ├── router.py
│   ├── models.py
│   ├── schemas.py
│   ├── services.py
│   ├── secrets_crypto.py    
│   ├── runtime_keys.py      
│   └── ...
├── alembic/versions/        
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
│   ├── test_api.py
│   └── test_admin.py
├── data/                    # Corpus (.pdf / .txt / .md)
├── chroma_db/
├── logs/
├── config.py
├── logging_config.py
├── ADMIN.md
└── requirements.txt
```

---



## Requisitos

- **Python 3.10+**
- **Embeddings (siempre):** cuenta en [NVIDIA Build](https://build.nvidia.com/) → `NVIDIA_API_KEY`
- **LLM Gemini:** cuenta en [Google AI Studio](https://aistudio.google.com/) → `GEMINI_API_KEY`
- **LLM NVIDIA:** misma `NVIDIA_API_KEY` del catálogo NIM (modelo en `LLM_MODEL`)
- **Panel admin:** PostgreSQL + `JWT_SECRET` (ver [ADMIN.md](ADMIN.md))

---



## Instalación

```bash
python -m venv .venv
source .venv/Scripts/activate   
pip install -r requirements.txt
```

Para el panel:

```bash
# crear DB chatbot_admin y configurar DATABASE_URL / JWT_SECRET en .env
alembic upgrade head
python -m admin.seed
```

---



## Variables de entorno (`.env`)

Crea `.env` en la raíz del proyecto (ver `.env.example`).

### Proveedor LLM


| Variable              | Descripción                              | Valor por defecto                                                   |
| --------------------- | ---------------------------------------- | ------------------------------------------------------------------- |
| `LLM_PROVIDER`        | Proveedor del LLM: `gemini` | `nvidia`   | `nvidia`                                                            |
| `LLM_MODEL`           | Nombre del modelo según el proveedor     | `meta/llama-3.1-8b-instruct` (NVIDIA) o `gemini-2.5-flash` (Gemini) |
| `NVIDIA_LLM_BASE_URL` | URL de NIM self-hosted (solo NVIDIA LLM) | Catálogo NVIDIA                                                     |




### Claves API


| Variable         | Cuándo es necesaria                              |
| ---------------- | ------------------------------------------------ |
| `NVIDIA_API_KEY` | Embeddings siempre; LLM si `LLM_PROVIDER=nvidia` |
| `GEMINI_API_KEY` | Si `LLM_PROVIDER=gemini`                         |


**Prioridad:** claves guardadas en el panel (cifradas en PostgreSQL) → variables de `.env` como fallback.

Se ouede dejar `.env` vacío para las keys y configurarlas solo desde **Configuración → Claves API** en el admin.

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



### Opcionales (RAG)


| Variable                  | Descripción                                    | Valor por defecto |
| ------------------------- | ---------------------------------------------- | ----------------- |
| `EMBED_MODEL`             | Modelo de embeddings en el catálogo NVIDIA     | `baai/bge-m3`     |
| `EMBED_BATCH_SIZE`        | Textos por request (máx. 259 en la API NVIDIA) | `32`              |
| `CHAT_SIMILARITY_TOP_K`   | Chunks recuperados enviados al LLM (1–20)      | `5`               |
| `CHAT_MEMORY_TOKEN_LIMIT` | Límite de tokens del historial (condense)      | `3500`            |
| `SESSION_TTL_HOURS`       | TTL de sesiones en memoria                     | `24`              |
| `LOG_RETENTION_DAYS`      | Días de retención de `logs/log-*.log`          | `30`              |




### Panel de administración


| Variable                                             | Descripción                                |
| ---------------------------------------------------- | ------------------------------------------ |
| `DATABASE_URL`                                       | PostgreSQL (`postgresql+psycopg://…`)      |
| `JWT_SECRET`                                         | Firma JWT **y** cifrado Fernet de API keys |
| `JWT_EXPIRE_HOURS`                                   | Caducidad del token (default 12)           |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_FULL_NAME` | Seed del primer admin                      |
| `ADMIN_CORS_ORIGINS`                                 | Orígenes del frontend Vite                 |
| `MAX_UPLOAD_MB`                                      | Límite de subida (default 25)              |


> Si se cambia el modelo de embeddings o el parser de chunks (`CHUNK_SIZE` / `StructuredParagraphNodeParser`), **reindexar** desde el panel (`POST /admin/reindex`) o borrar `chroma_db/` y volver a reindexar.

Los logs de WARNING/ERROR se guardan en `logs/log-YYYY-MM-DD.log`.

---



## Uso



### 1. Colocar documentos

Copiar PDFs (o `.txt` / `.md`) en `data/`, o subirlos desde el panel **Documentos**.

### 2. Arrancar la API

```bash
uvicorn api.main:app --reload --port 8000
```



### 3. Ingesta / reindex

Solo desde el panel (**Documentos → Reindexar**) o con JWT:

```bash
curl -X POST http://127.0.0.1:8000/admin/reindex \
  -H "Authorization: Bearer TU_JWT"
```



### 4. Chat (con memoria por sesión)

Mismo `session_id` en varias llamadas = misma conversación.

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "alumno-1",
    "message": "¿Qué título otorga la carrera de Ingeniería en Inteligencia Artificial?"
  }'
```


| Campo        | Obligatorio | Descripción                   |
| ------------ | ----------- | ----------------------------- |
| `session_id` | Sí          | Identificador de conversación |
| `message`    | Sí          | Pregunta del usuario          |


---



## Endpoints públicos


| Método | Ruta            | Descripción                                                 |
| ------ | --------------- | ----------------------------------------------------------- |
| `GET`  | `/health`       | Estado del servicio y modelo LLM activo (`status`, `model`) |
| `POST` | `/chat`         | RAG conversacional + lista de fuentes                       |
| `GET`  | `/swagger`      | Swagger UI                                                  |
| `GET`  | `/redoc`        | ReDoc                                                       |
| `GET`  | `/openapi.json` | Esquema OpenAPI                                             |


La indexación **no** es pública: usa `POST /admin/reindex` (JWT). Rutas de administración: **[ADMIN.md](ADMIN.md)**.

---



## Parámetros relevantes (`config.py`)


| Constante                       | Valor por defecto | Nota                                         |
| ------------------------------- | ----------------- | -------------------------------------------- |
| `CHUNK_SIZE`                    | `512`             | Alineado con modelos que truncan ~512 tokens |
| `CHUNK_OVERLAP`                 | `64`              | Solape entre chunks                          |
| `DEFAULT_EMBED_MODEL`           | `baai/bge-m3`     | Multilingüe; configurable con `EMBED_MODEL`  |
| `DEFAULT_CHAT_SIMILARITY_TOP_K` | `5`               | Sobrescribible con env / panel (1–20)        |
| `CHROMA_COLLECTION`             | `faculty_docs`    | Nombre de la colección en Chroma             |


Modelos LLM por defecto en `llm/factory.py`: `meta/llama-3.1-8b-instruct` (NVIDIA), `gemini-2.5-flash` (Gemini).

### Health check

```bash
curl http://127.0.0.1:8000/health
```

```json
{
  "status": "ok",
  "model": "meta/llama-3.1-8b-instruct"
}
```

---



## Tests

```bash
pytest tests/ -v
```

Incluye pruebas de API pública (factory LLM, health, ausencia de `/ingest`) y del panel (auth, settings, branding, API keys cifradas, documentos, reindex/chat mockeados).

---



## Panel de administración

Ver **[ADMIN.md](ADMIN.md)**.

Resumen: login JWT, documentos + reindex, configuración de proveedor/modelos, **claves API cifradas**, personalización (logo URL + colores), chat de prueba y gestión de usuarios.

Frontend:

```bash
cd ../chatbot-admin
npm install && npm run dev
```

---



## Comportamiento del asistente

Definido en `generation/prompt.py`:

- Responde solo con información **recuperada** de los documentos indexados.
- Si la respuesta no está en el contexto recuperado, debe responder exactamente: **"No tengo esa información en los documentos."**

