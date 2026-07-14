# Panel de administración del chatbot RAG

Backend integrado en API FastAPI (`/auth/*`, `/admin/*`).  

## Requisitos

- Python 3.10+
- PostgreSQL local (crear base `chatbot_admin`)
- Node 20+ para el frontend

## Base de datos

En `psql` o pgAdmin:

```sql
CREATE DATABASE chatbot_admin;
```

Variables (`.env`):

```env
DATABASE_URL=postgresql+psycopg://USUARIO:CLAVE@127.0.0.1:5432/chatbot_admin
JWT_SECRET=una-cadena-larga-aleatoria
JWT_EXPIRE_HOURS=12
ADMIN_EMAIL=admin@facultad.local
ADMIN_PASSWORD=ChangeMe123!
ADMIN_FULL_NAME=Administrador Facultad
ADMIN_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
MAX_UPLOAD_MB=25
```

> **`JWT_SECRET`** se usa para firmar tokens **y** como material de cifrado Fernet de las API keys en BD. Cámbiar en producción y **no** rotarlo a la ligera si ya hay keys cifradas (habría que volver a guardarlas).


Migraciones + seed del primer admin:

```bash
pip install -r requirements.txt
alembic upgrade head
python -m admin.seed
```

## Arranque API

```bash
uvicorn api.main:app --reload --port 8000
```

Endpoints públicos: `GET /health`, `POST /chat`.  

## Endpoints admin

| Método | Ruta | Auth | Notas |
|--------|------|------|-------|
| POST | `/auth/login` | No | JWT 12 h (configurable) |
| GET | `/auth/me` | JWT | Perfil del admin |
| GET | `/admin/dashboard` | JWT | Estado, docs, reindex |
| GET | `/admin/branding` | **No** | Branding para login |
| GET/PUT | `/admin/settings` | JWT | LLM, branding, API keys |
| GET | `/admin/documents` | JWT | Lista `data/` |
| POST | `/admin/documents/upload` | JWT | PDF / TXT / MD; marca reindex |
| DELETE | `/admin/documents/{file_name}` | JWT | Marca reindex |
| POST | `/admin/reindex` | JWT | Ingest + limpia `reindex_required` |
| POST | `/admin/chat/test` | JWT | RAG de prueba |
| GET/POST | `/admin/users` | JWT | Listar / crear |
| PATCH | `/admin/users/{id}` | JWT | Activar / desactivar / password |

## Configuración persistida

Guardada en la tabla `chatbot_admin_settings` (fila única):

| Grupo | Campos |
|-------|--------|
| LLM / RAG | `provider`, `llm_model`, `embed_model`, `similarity_top_k` |
| Índice | `reindex_required`, `last_reindex_at`, `last_reindex_result` |
| Branding | `logo_url`, `primary_color`, `accent_color`, `brand_name`, `brand_subtitle` |
| API keys | `gemini_api_key_enc`, `nvidia_api_key_enc` (Fernet; nunca se devuelven en claro) |

### Claves API (cifrado en reposo)

1. El panel puede guardar Gemini y NVIDIA cifradas en BD.
2. Prioridad de resolución: **BD (descifrada) → `.env`**.
3. `GET/PUT /admin/settings` solo expone flags: `gemini_api_key_set`, `nvidia_api_key_set`, `gemini_api_key_env`, `nvidia_api_key_env`.
4. En el PUT, si se envía `gemini_api_key` / `nvidia_api_key`, se cifra y guarda. Campo omitido = no cambia.
5. Opcional vía API: `clear_gemini_api_key` / `clear_nvidia_api_key` (el frontend no muestra checkbox; las keys siguen priorizando BD).
6. Al arrancar, `load_api_keys_from_db()` carga las keys a memoria antes de `configure_settings()`.

Los embeddings **siempre** usan NVIDIA; aunque el LLM sea Gemini, hace falta `NVIDIA_API_KEY` (BD o `.env`).

### Branding

- `GET /admin/branding` es público para pintar login y sidebar sin JWT.
- Logo (PNG/SVG preferible con transparencia).
- Colores institucionales por defecto: primario `#00407d`, acento `#f27022`.

## Frontend

```bash
cd ../chatbot-admin
cp .env.example .env 
npm install
npm run dev
```

Entrar con `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

Páginas: Login, Inicio, Documentos, Configuración (claves + modelo + personalización), Chat de prueba, Usuarios.

## Flujo típico

1. Login  
2. **Configuración** → claves API (si no están en `.env`), proveedor y modelos  
3. **Documentos** → subir PDF/TXT/MD  
4. **Reindexar**  
5. **Chat de prueba**  
6. (Opcional) Personalización: logo URL y colores  

Si se cambia el **modelo de embeddings** o hay upload/delete, la UI avisa **reindex requerido**.

## Pruebas

```bash
pytest tests/ -v
# o solo admin:
pytest tests/test_admin.py -v
```

## Pendientes fuera de MVP

- Refresh token / cookies httpOnly  
- Rate limit en login  
- Progreso en tiempo real del reindex (SSE)  
- RBAC por roles  
