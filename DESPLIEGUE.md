# Guía de despliegue — Chatbot Facultad

> **Plan actual:** desplegar primero la **API** y el **panel admin** (Fase 1). El plugin **WordPress** se conectará después (Fase 2), cuando el backend ya esté estable.

### Índice

0. [Fase 1 — Ruta rápida (API + panel)](#fase-1--ruta-rápida-api--panel)
1. [¿Qué estamos desplegando?](#1-qué-estamos-desplegando)
2. [¿Qué es Docker?](#2-qué-es-docker-explicado-sin-tecnicismos)
3. [¿Necesito PostgreSQL en mi PC?](#3-necesito-postgresql-u-otras-cosas-instalado-en-mi-pc)
4. [Instalar Docker en Windows Server](#4-instalar-docker-en-windows-server)
5. [Explicación de Dockerfile y docker-compose](#5-explicación-detallada-de-los-archivos-docker)
6. [Despliegue paso a paso (Fase 1)](#6-despliegue-con-docker-paso-a-paso-fase-1)
7. [Qué hace cada contenedor](#7-qué-hace-cada-contenedor)
8. [Comandos útiles](#8-comandos-útiles-del-día-a-día)
9. [Producción en servidor real](#9-despliegue-en-un-servidor-real-producción)
10. [Despliegue manual (sin Docker)](#10-despliegue-manual-sin-docker)
11. [Solución de problemas](#11-solución-de-problemas)
12. [Checklist Fase 1 y Fase 2](#12-checklist-fase-1-y-fase-2)
13. [Fase 2 — WordPress (más adelante)](#13-fase-2--wordpress-más-adelante)
14. [Archivos de despliegue](#14-archivos-de-despliegue-incluidos)

---

## Fase 1 — Ruta rápida (API + panel)

Con Docker levantas **todo lo necesario** para que la facultad administre el chatbot **sin WordPress**:

| Qué levanta `docker compose` | Para qué |
|------------------------------|----------|
| `postgres` | Base de datos del panel (interno) |
| `api` | Chat RAG + endpoints admin → **http://localhost:8000** |
| `admin` | Panel web → **http://localhost:8080** |

**No necesitas** XAMPP, WordPress ni el plugin `chatbot/` en esta fase.

### Comandos (resumen)

```bash
cd chatbot-facultad
cp .env.docker.example .env
# Editar .env: NVIDIA_API_KEY, JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD

docker compose up -d --build
```

### Comprobar

| URL | Qué deberías ver |
|-----|------------------|
| http://localhost:8000/health | `{"status":"ok","model":"..."}` |
| http://localhost:8080 | Pantalla de login del panel |
| Panel → Documentos → Reindexar | PDFs indexados |
| Panel → Chat de prueba | Respuestas del asistente |

WordPress llegará en la **Fase 2** (sección 13): solo apuntará el plugin a la URL pública de la API que ya tengas corriendo.

---

## 1. ¿Qué estamos desplegando?

El ecosistema completo tiene tres piezas, pero **ahora solo desplegamos dos**:

| Fase | Pieza | Carpeta | ¿Desplegar ahora? |
|------|-------|---------|-------------------|
| **1** | **API (cerebro)** | `chatbot-facultad/` | **Sí** — Docker (`api` + `postgres`) |
| **1** | **Panel admin** | `chatbot-admin/` | **Sí** — Docker (`admin`) |
| **2** | Plugin WordPress | `chatbot/` | **Después** — cuando la API esté en producción |

Además, la API usa (incluido en Docker, no los instalas tú):

- **PostgreSQL** → usuarios del panel, configuración y claves API cifradas
- **ChromaDB** → índice de documentos (`chroma_db/`)
- **Carpeta `data/`** → PDFs y textos subidos

### Fase 1 (ahora)

```text
Administrador de la facultad
        │
        ▼
   Panel chatbot-admin (:8080)
        │
        ▼
   API chatbot-facultad (:8000)  ──────►  NVIDIA / Google (IA en la nube)
        │
        ├── PostgreSQL (contenedor interno)
        └── ChromaDB + data/ (volúmenes Docker)
```

Con la Fase 1 ya puedes: login, subir documentos, reindexar, configurar claves y **probar el chat** desde el panel.

### Fase 2 (después)

```text
Visitante del sitio web
        │
        ▼
   WordPress + plugin "chatbot"
        │  (proxy hacia /chat)
        ▼
   API chatbot-facultad  (la misma de la Fase 1)
```

---

## 2. ¿Qué es Docker? (explicado sin tecnicismos)

Imagina que cada programa (Python, PostgreSQL, nginx) viene en una **caja cerrada** con todo lo que necesita para funcionar. Esa caja es un **contenedor**. La **receta** para fabricar la caja se llama **imagen**.

| Concepto | Analogía | En este proyecto |
|----------|----------|------------------|
| **Imagen** | Plano / molde de una caja | `python:3.12`, `postgres:16`, tu `Dockerfile` compilado |
| **Contenedor** | Caja ya fabricada y encendida | El proceso `api` corriendo en el puerto 8000 |
| **Volumen** | Disco duro externo pegado a la caja | Donde se guardan PDFs, ChromaDB y la base de datos |
| **Red Docker** | Cable virtual entre cajas | La API habla con PostgreSQL por el nombre `postgres` |
| **docker compose** | Mando a distancia de varias cajas | Un solo comando levanta postgres + api + admin |

### ¿Qué pasa cuando ejecutas `docker compose up -d --build`?

```text
1. Docker LEE docker-compose.yml  →  "Necesito 3 servicios: postgres, api, admin"

2. Para "api" y "admin", CONSTRUYE imágenes desde los Dockerfile
   (instala Python, pip, npm, etc. dentro de la imagen)

3. DESCARGA la imagen oficial de PostgreSQL (postgres:16-alpine)

4. CREA una red interna y conecta los contenedores

5. CREA volúmenes en disco para que los datos sobrevivan reinicios

6. ARRANCA postgres  →  espera healthcheck  →  arranca api  →  arranca admin

7. EXPONE puertos de tu PC hacia afuera:
   localhost:8000  →  contenedor api
   localhost:8080  →  contenedor admin
```

Con `-d` ("detached") los contenedores quedan en segundo plano. Sin `-d` verías los logs en la terminal.

### Ventajas frente a instalar todo a mano

- **No instalas Python, Node ni PostgreSQL en Windows** — van dentro de contenedores Linux.
- Mismo resultado en tu PC, en un compañero o en un servidor.
- Si algo se rompe, puedes borrar contenedores y volver a levantarlos sin ensuciar el sistema.
- Los datos importantes viven en **volúmenes**, no dentro del contenedor efímero.

---

## 3. ¿Necesito PostgreSQL (u otras cosas) instalado en mi PC?

**Respuesta corta: NO**, si usas Docker como está configurado en este proyecto.

| Software | ¿Instalar en Windows/Server? | ¿Dónde corre con Docker? |
|----------|------------------------------|---------------------------|
| **PostgreSQL** | No | Contenedor `postgres` |
| **Python 3.12 + pip** | No | Contenedor `api` |
| **Node.js + npm** | No (solo para build) | Contenedor `admin` (fase build) |
| **nginx** | No | Contenedor `admin` |
| **Docker** | **Sí — esto es lo único obligatorio** | Motor en el host |

PostgreSQL **sigue existiendo**, pero corre **dentro de Docker**, aislado. Tu API se conecta con:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/chatbot_admin
```

Fíjate en `@postgres`: ese `postgres` **no es tu PC**, es el **nombre del servicio** en `docker-compose.yml`. Docker tiene un DNS interno: cada contenedor se encuentra por su nombre.

### ¿Qué SÍ queda en tu máquina (fuera de Docker)?

| Elemento | Dónde está |
|----------|------------|
| **WordPress + plugin `chatbot`** | **Fase 2** — no hace falta ahora |
| **Archivo `.env`** | Carpeta `chatbot-facultad/` en disco |
| **Volúmenes Docker** | Gestionados por Docker en su almacenamiento interno (p. ej. `C:\ProgramData\Docker\` en Windows) |
| **Código fuente** | Tus carpetas del proyecto |

### ¿Y si NO uso Docker?

Entonces **sí** necesitas instalar manualmente:

- Python 3.10+, PostgreSQL, Node 20+ (para compilar el panel)
- Crear la base `chatbot_admin` tú mismo
- Ejecutar migraciones y uvicorn a mano

Ver sección 10 (despliegue manual).

### Comparación visual

```text
SIN DOCKER (instalación clásica):
┌─────────────────────────────────────────┐
│  Windows Server / tu PC                 │
│  ├── PostgreSQL instalado               │
│  ├── Python + venv + uvicorn            │
│  ├── Node + npm build                   │
│  ├── nginx o IIS sirviendo el panel     │
│  └── WordPress (XAMPP)                  │
└─────────────────────────────────────────┘

CON DOCKER (este proyecto):
┌─────────────────────────────────────────┐
│  Windows Server / tu PC                 │
│  ├── Docker Engine                      │
│  │   ├── contenedor postgres            │
│  │   ├── contenedor api (Python)        │
│  │   └── contenedor admin (nginx)       │
│  └── WordPress (Fase 2, cuando toque)   │
└─────────────────────────────────────────┘
```

---

## 4. Instalar Docker en Windows Server

> **Importante:** **Docker Desktop** es para Windows 10/11 (escritorio). En **Windows Server** se usa **Docker Engine** (Moby), normalmente con **contenedores Linux** vía **WSL 2**.

### 4.1 Requisitos del servidor

| Requisito | Detalle |
|-----------|---------|
| **SO** | Windows Server 2019 o 2022 (64 bits) |
| **Virtualización** | Habilitada en BIOS/UEFI |
| **RAM** | Mínimo 8 GB (4 GB para Windows + contenedores) |
| **Disco** | 40 GB libres recomendados |
| **Roles** | Hyper-V y/o WSL 2 según el método |

### 4.2 Opción recomendada: WSL 2 + Docker Engine

**Paso A — Habilitar WSL y una distro Linux**

Abre **PowerShell como Administrador**:

```powershell
# Instalar WSL con Ubuntu
wsl --install
# Si ya tienes WSL: wsl --install -d Ubuntu-22.04
```

Reinicia el servidor si lo pide. Tras reiniciar, completa el usuario/contraseña de Ubuntu la primera vez que se abra.

**Paso B — Instalar Docker Engine dentro de WSL (Ubuntu)**

En la terminal de **Ubuntu (WSL)**:

```bash
# Actualizar paquetes
sudo apt-get update
sudo apt-get install -y ca-certificates curl

# Repositorio oficial de Docker
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Permitir docker sin sudo (opcional; cierra y abre la terminal)
sudo usermod -aG docker $USER
```

Verifica:

```bash
docker --version
docker compose version
```

**Paso C — Copiar el proyecto a WSL o acceder desde `/mnt/c/`**

El proyecto en XAMPP suele estar en Windows como:

```text
C:\xampp\htdocs\chatbot\wp-content\plugins\chatbot-facultad
```

Desde WSL es:

```bash
cd /mnt/c/xampp/htdocs/chatbot/wp-content/plugins/chatbot-facultad
```

Ahí ejecutas `docker compose up -d --build` igual que en la guía.

> **Nota:** Los volúmenes y rendimiento de I/O son mejores si copias el proyecto a `~/chatbot-facultad` dentro del filesystem de Linux (`/home/...`) en lugar de `/mnt/c/`. Para producción en Server, considera clonar el repo directamente en WSL o en una VM Linux.

### 4.3 Opción alternativa: Docker Engine nativo en Windows Server

Algunos entornos usan el runtime **Moby** directamente en Windows Server (sin WSL). Requiere el rol **Containers** y Hyper-V:

```powershell
# PowerShell como Administrador
Install-WindowsFeature -Name Containers
Install-Module -Name DockerMsftProvider -Force
Install-Package -Name docker -ProviderName DockerMsftProvider -Force
Restart-Computer -Force
```

Tras reiniciar:

```powershell
docker version
```

Para **contenedores Linux** en Server sin WSL puede hacer falta una VM Linux auxiliar; por eso **WSL 2 + Docker en Ubuntu** suele ser más simple para este stack (Python + PostgreSQL + nginx son imágenes **Linux**).

### 4.4 Windows 10/11 (tu PC de desarrollo)

Si desarrollas en un PC normal (no Server):

1. Descarga [Docker Desktop para Windows](https://docs.docker.com/desktop/setup/install/windows-install/).
2. Durante la instalación elige **WSL 2** como backend.
3. Reinicia si lo pide.
4. Abre Docker Desktop y espera "Engine running".
5. En PowerShell o Git Bash:

```bash
docker --version
docker compose version
```

### 4.5 Firewall en Windows Server

Para que otros equipos accedan al chatbot en la red local:

```powershell
# Permitir API (8000) y panel (8080)
New-NetFirewallRule -DisplayName "Chatbot API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Chatbot Admin" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
```

En producción usarás HTTPS (443) delante con un reverse proxy, no puertos crudos expuestos a internet.

### Requisitos generales (cualquier entorno)

| Requisito | Detalle |
|-----------|---------|
| **Docker + Compose** | Ver secciones 4.2–4.4 según tu SO |
| **RAM** | Mínimo 4 GB libres (8 GB recomendado) |
| **Disco** | 10–20 GB libres (más si hay muchos PDFs) |
| **Internet** | Salida HTTPS hacia NVIDIA y/o Google |
| **Claves API** | Cuenta en [NVIDIA Build](https://build.nvidia.com/) (obligatoria para embeddings) |

---

## 5. Explicación detallada de los archivos Docker

Esta sección explica **línea por línea** qué hace cada archivo que creamos.

### 5.1 `Dockerfile` (API — carpeta `chatbot-facultad/`)

```dockerfile
FROM python:3.12-slim-bookworm
```

Empieza desde una imagen oficial de Python 3.12 sobre Debian "slim" (ligera). Es la base del contenedor `api`.

```dockerfile
WORKDIR /app
```

Dentro del contenedor, el directorio de trabajo será `/app`. Todo lo que copies y ejecutes ocurre ahí.

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
```

Variables de entorno de Python:

- No generar archivos `.pyc` innecesarios.
- Mostrar logs en consola al instante (útil con `docker compose logs`).
- No cachear paquetes pip en la imagen (imagen más limpia).

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
```

Instala compiladores del sistema; algunas librerías de Python (p. ej. dependencias de `cryptography`) los necesitan al instalarse.

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
```

Copia solo `requirements.txt` primero (capa cacheada) e instala FastAPI, ChromaDB, LlamaIndex, etc. Si cambias código pero no dependencias, Docker reutiliza esta capa y el build es más rápido.

```dockerfile
COPY . .
```

Copia el resto del proyecto (API, admin, alembic, `docker-entrypoint.sh`, etc.) respetando `.dockerignore` (excluye `.venv`, `.env`, tests…).

```dockerfile
RUN mkdir -p data chroma_db logs \
    && chmod +x docker-entrypoint.sh
```

Crea carpetas persistentes y hace ejecutable el script de arranque.

```dockerfile
EXPOSE 8000
```

Documenta que el proceso escucha en el puerto 8000. **No abre el puerto solo** — eso lo hace `docker-compose.yml` con `ports:`.

```dockerfile
ENTRYPOINT ["./docker-entrypoint.sh"]
```

Cada vez que el contenedor arranca, ejecuta ese script (esperar BD, migrar, seed, uvicorn).

---

### 5.2 `docker-entrypoint.sh` (arranque de la API)

| Bloque | Qué hace |
|--------|----------|
| `set -e` | Si un comando falla, el script se detiene (el contenedor no arranca "medio roto"). |
| Bucle Python + `psycopg` | Intenta conectar a PostgreSQL hasta 30 veces (cada 2 s). PostgreSQL tarda unos segundos en estar listo. |
| `alembic upgrade head` | Crea/actualiza tablas en PostgreSQL (usuarios, settings, branding, api_keys…). |
| `python -m admin.seed` | Crea el primer admin si no existe (idempotente: no duplica). |
| `exec uvicorn ...` | Arranca FastAPI en `0.0.0.0:8000` (acepta conexiones desde fuera del contenedor). |

`exec` reemplaza el proceso del shell por uvicorn — señales de parada (SIGTERM) llegan bien a la API.

---

### 5.3 `docker-compose.yml` (orquestador)

Define **3 servicios** y **4 volúmenes**.

#### Servicio `postgres`

```yaml
image: postgres:16-alpine
```

Usa imagen oficial; no hay Dockerfile propio. Alpine = imagen pequeña.

```yaml
environment:
  POSTGRES_USER: ${POSTGRES_USER:-postgres}
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
  POSTGRES_DB: ${POSTGRES_DB:-chatbot_admin}
```

Credenciales leídas de tu `.env`. La sintaxis `${VAR:-default}` usa `VAR` si existe, si no el valor por defecto.

```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

Los datos de la BD viven en el volumen `postgres_data`, **no** dentro del contenedor. Si borras el contenedor pero no el volumen, **conservas la base de datos**.

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres -d chatbot_admin"]
```

Docker pregunta cada 5 s si PostgreSQL acepta conexiones. Hasta que responde OK, el servicio `api` **no arranca** (`depends_on: condition: service_healthy`).

**No hay `ports:`** → PostgreSQL **no está expuesto** a internet ni a tu PC directamente. Solo otros contenedores en la red Docker pueden conectarse (más seguro).

#### Servicio `api`

```yaml
build:
  context: .
  dockerfile: Dockerfile
```

Construye la imagen desde el `Dockerfile` de esta carpeta.

```yaml
env_file:
  - .env
```

Carga todas las variables del `.env`, incluida `DATABASE_URL`. **No hay credenciales de BD en el compose** — deben estar en `.env` (ver `.env.docker.example`). El host debe ser `postgres` (nombre del servicio), no `127.0.0.1`.

> `DATABASE_URL` debe usar el mismo usuario y contraseña que `POSTGRES_USER` y `POSTGRES_PASSWORD`.

```yaml
ports:
  - "${API_PORT:-8000}:8000"
```

Formato `PUERTO_EN_TU_PC:PUERTO_EN_CONTENEDOR`. Por defecto `8000:8000` → [http://localhost:8000](http://localhost:8000).

```yaml
volumes:
  - api_data:/app/data
  - api_chroma:/app/chroma_db
  - api_logs:/app/logs
```

PDFs, índice Chroma y logs persisten aunque reinicies o reconstruyas el contenedor `api`.

```yaml
depends_on:
  postgres:
    condition: service_healthy
```

Orden de arranque: primero postgres sano, luego api.

#### Servicio `admin`

```yaml
build:
  context: ../chatbot-admin
  args:
    VITE_API_BASE_URL: ${VITE_API_BASE_URL:-http://localhost:8000}
```

Construye el frontend React desde la carpeta hermana. `VITE_API_BASE_URL` se **incrusta en el JavaScript en tiempo de build** — por eso, si cambias la URL pública de la API, debes **reconstruir** `admin`.

```yaml
ports:
  - "${ADMIN_PORT:-8080}:80"
```

El contenedor nginx escucha en 80; tú accedes por 8080 en el host.

```yaml
depends_on:
  - api
```

Arranca después de `api` (no espera healthcheck de la API; solo que el contenedor haya iniciado).

#### Bloque `volumes:`

Declara volúmenes con nombre gestionados por Docker. Puedes listarlos con:

```bash
docker volume ls
```

---

### 5.4 `Dockerfile` del panel (`chatbot-admin/`)

Build en **dos etapas** (multi-stage):

**Etapa 1 — `build` (Node):**

```dockerfile
FROM node:20-alpine AS build
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
```

Instala dependencias, compila TypeScript + Vite → carpeta `dist/` con HTML/JS/CSS estáticos. La URL de la API queda fija en esos archivos JS.

**Etapa 2 — nginx:**

```dockerfile
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
```

Solo copia los archivos compilados a nginx. **La imagen final no incluye Node** — más pequeña y segura.

---

### 5.5 `nginx.conf` (panel admin)

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

El panel es una SPA (React Router). Rutas como `/documentos` o `/configuracion` deben devolver `index.html` para que React maneje la navegación. Sin esto, refrescar la página daría 404.

---

### 5.6 `.env.docker.example` y `.dockerignore`

- **`.env.docker.example`**: plantilla con valores para Docker (`DATABASE_URL` con host `postgres`, CORS para puerto 8080, etc.). Lo copias a `.env`.
- **`.dockerignore`**: archivos que **no** entran en la imagen (`.venv`, `.env` real, tests, `chroma_db` local…). Evita copiar basura y secretos al build.

---

### 5.7 Flujo completo al ejecutar `docker compose up -d --build`

```text
┌──────────────┐     build      ┌─────────────────┐
│  Dockerfile  │ ─────────────► │  Imagen "api"   │
│  (api)       │                └────────┬────────┘
└──────────────┘                         │
                                         ▼
┌──────────────┐     pull       ┌─────────────────┐     healthcheck
│ postgres:16  │ ─────────────► │ Contenedor      │ ────────────────┐
└──────────────┘                │ postgres        │                 │
                                └─────────────────┘                 │
                                         ▲                          │
                                         │ DATABASE_URL             │
┌──────────────┐     build              │                          │
│  Dockerfile  │ ─────────────► ┌───────┴─────────┐                │
│  (admin)     │                │ Contenedor api   │ ◄───────────────┘
└──────────────┘                │ entrypoint.sh    │
                                │ uvicorn :8000    │
                                └────────┬─────────┘
                                         │
                                ┌────────┴─────────┐
                                │ Contenedor admin │
                                │ nginx :80        │
                                └──────────────────┘

Tu navegador (Fase 1):
  localhost:8080 → admin → llama a VITE_API_BASE_URL (localhost:8000) → api

Fase 2 (después):
  WordPress plugin → URL pública de la API → /chat
```

---

## 6. Despliegue con Docker (paso a paso — Fase 1)

Estos pasos cubren **solo API + panel**. WordPress queda para la [sección 13](#13-fase-2--wordpress-más-adelante).

### Paso 1 — Tener Docker funcionando

Sigue la **sección 4** según tu caso (Windows Server con WSL, Server nativo, o Windows 10/11 con Docker Desktop).

Verifica:

```bash
docker --version
docker compose version
```

Deberías ver números de versión, no un error.

---

### Paso 2 — Ir a la carpeta del proyecto

```bash
cd c:/xampp/htdocs/chatbot/wp-content/plugins/chatbot-facultad
```

(Ajusta la ruta si tu proyecto está en otro sitio.)

---

### Paso 3 — Crear el archivo de configuración `.env`

Copia el ejemplo preparado para Docker:

```bash
cp .env.docker.example .env
```

Abre `.env` con un editor de texto y **cambia al menos esto**:

```env
# Obligatorio: clave de NVIDIA (embeddings + LLM si usas nvidia)
NVIDIA_API_KEY=tu_clave_real_aqui

# Obligatorio: contraseña secreta larga (firma login y cifra claves en BD)
JWT_SECRET=pon-aqui-una-frase-larga-y-aleatoria-de-mas-de-32-caracteres

# Credenciales del primer administrador del panel
ADMIN_EMAIL=admin@facultad.edu
ADMIN_PASSWORD=TuPasswordSeguro123!
ADMIN_FULL_NAME=Administrador Facultad
```

**¿Qué es cada cosa?**

| Variable | Para qué sirve |
|----------|----------------|
| `NVIDIA_API_KEY` | Conecta con la IA de NVIDIA (embeddings siempre; LLM si `LLM_PROVIDER=nvidia`) |
| `GEMINI_API_KEY` | Solo si usas Google Gemini como LLM (`LLM_PROVIDER=gemini`) |
| `JWT_SECRET` | Seguridad del panel: tokens de login y cifrado de claves guardadas |
| `DATABASE_URL` | Ya viene bien para Docker (`postgres` es el nombre del contenedor) |
| `ADMIN_CORS_ORIGINS` | Deja los valores por defecto si usas puertos 8080 y 8000 en local |
| `VITE_API_BASE_URL` | URL que el navegador usa para llamar a la API (`http://localhost:8000` en local) |

---

### Paso 4 — Construir e iniciar todo

```bash
docker compose up -d --build
```

- `up` → inicia los servicios  
- `-d` → en segundo plano  
- `--build` → construye las imágenes la primera vez (o tras cambios)

**La primera vez puede tardar varios minutos** (descarga imágenes e instala dependencias).

---

### Paso 5 — Comprobar que funciona

**API (salud del servicio):**

```bash
curl http://localhost:8000/health
```

Respuesta esperada:

```json
{"status":"ok","model":"meta/llama-3.1-8b-instruct"}
```

También puedes abrir en el navegador:

- API / documentación: [http://localhost:8000/swagger](http://localhost:8000/swagger)
- Panel admin: [http://localhost:8080](http://localhost:8080)

**Ver logs si algo falla:**

```bash
docker compose logs -f api
```

(Ctrl+C para salir de los logs.)

---

### Paso 6 — Entrar al panel y configurar

1. Abre [http://localhost:8080](http://localhost:8080)
2. Inicia sesión con `ADMIN_EMAIL` y `ADMIN_PASSWORD` del `.env`
3. Ve a **Configuración → Claves API** y guarda las claves si no las pusiste en `.env`
4. Ve a **Documentos** → sube PDFs oficiales → pulsa **Reindexar**
5. Prueba en **Chat de prueba**

Sin documentos indexados, el asistente responderá que no tiene información.

**Con esto la Fase 1 está completa.** Cuando quieras el widget en la web de la facultad, sigue la sección 13.

---

## 7. Qué hace cada contenedor

| Servicio en `docker-compose.yml` | Puerto en tu PC | Función |
|----------------------------------|-----------------|---------|
| `postgres` | (interno, no expuesto) | Base de datos del panel |
| `api` | **8000** | FastAPI: `/chat`, `/health`, `/admin/*` |
| `admin` | **8080** | Panel React servido por nginx |

### Datos que NO se pierden al reiniciar

Docker guarda estos volúmenes:

| Volumen | Contenido |
|---------|-----------|
| `postgres_data` | Usuarios, settings, claves cifradas |
| `api_data` | PDFs en `data/` |
| `api_chroma` | Índice vectorial ChromaDB |
| `api_logs` | Archivos de log |

---

## 8. Comandos útiles del día a día

```bash
# Ver estado de los contenedores
docker compose ps

# Parar todo (los datos se conservan)
docker compose down

# Parar y BORRAR volúmenes (¡cuidado! pierdes BD, PDFs e índice)
docker compose down -v

# Reiniciar solo la API tras cambiar .env
docker compose up -d --build api

# Reconstruir panel admin tras cambiar VITE_API_BASE_URL
docker compose build --no-cache admin
docker compose up -d admin
```

---

## 9. Despliegue en un servidor real (producción)

En la facultad normalmente tendrás un **Windows Server** o un **servidor Linux** (VPS o máquina virtual), con dominio propio.

**Fase 1 (ahora)** — expón solo API y panel:

  - `https://api.facultad.edu` → API (puerto 8000 interno)
  - `https://admin.facultad.edu` → panel (puerto 8080 interno)

**Fase 2 (después)** — WordPress en su propio hosting:

  - `https://www.facultad.edu` → sitio con plugin apuntando a `https://api.facultad.edu`

En **Windows Server**, el flujo Docker es el mismo (sección 4); lo habitual es ejecutar `docker compose` desde WSL Ubuntu o planificar una VM Linux dedicada si el área de sistemas lo prefiere.

### Cambios en `.env` para producción

```env
# URL pública de la API (la verá el navegador y WordPress)
VITE_API_BASE_URL=https://api.facultad.edu

# Origen permitido del panel (CORS)
ADMIN_CORS_ORIGINS=https://admin.facultad.edu

# Claves y JWT con valores fuertes de producción
JWT_SECRET=...
NVIDIA_API_KEY=...
```

Después de cambiar `VITE_API_BASE_URL` **debes reconstruir** el contenedor `admin`:

```bash
docker compose build --no-cache admin
docker compose up -d
```

### HTTPS

Delante de Docker suele ir **nginx** o **Caddy** en el servidor host, con certificado Let's Encrypt, redirigiendo:

- `api.facultad.edu` → `localhost:8000`
- `admin.facultad.edu` → `localhost:8080`

WordPress apunta la URL del plugin a `https://api.facultad.edu` (Fase 2).

### Requisitos mínimos del servidor (Fase 1)

| Recurso | Recomendación |
|---------|---------------|
| CPU | 2–4 vCPU |
| RAM | 4–8 GB |
| Disco | 20–50 GB SSD |
| GPU | **No necesaria** |
| SO | Ubuntu 22.04 LTS o similar |

---

## 10. Despliegue manual (sin Docker)

Si no puedes usar Docker, instala todo a mano:

### 10.1 API

```bash
cd chatbot-facultad
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env             # editar DATABASE_URL, JWT_SECRET, claves
alembic upgrade head
python -m admin.seed
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Necesitas **PostgreSQL** instalado y una base `chatbot_admin` creada.

### 10.2 Panel admin

```bash
cd ../chatbot-admin
cp .env.example .env             # VITE_API_BASE_URL=http://tu-servidor:8000
npm install
npm run build
```

Sirve la carpeta `dist/` con nginx o Apache.

### 10.3 WordPress (Fase 2)

Ver [sección 13](#13-fase-2--wordpress-más-adelante).

---

## 11. Solución de problemas

### “Cannot connect to Docker daemon”

Docker Desktop no está abierto. Inícialo y espera a que diga “Running”.

### El panel carga pero el login falla / errores CORS

- Revisa que `ADMIN_CORS_ORIGINS` incluya la URL exacta del panel (con `http://` y puerto).
- Reinicia la API: `docker compose restart api`

### `/health` responde pero el chat no funciona

- ¿Hay documentos subidos y **reindexados**?
- ¿`NVIDIA_API_KEY` es válida? (embeddings siempre la necesitan)
- Mira logs: `docker compose logs api`

### WordPress no conecta con la API (Fase 2)

Aplica cuando conectes el plugin. La URL en ajustes debe ser accesible **desde el servidor WordPress** (no solo desde tu PC).

### Cambié `.env` y no pasa nada

Algunas variables solo se leen al arrancar:

```bash
docker compose up -d --force-recreate api
```

### Puerto 8000 u 8080 ya en uso

En `.env` cambia:

```env
API_PORT=8001
ADMIN_PORT=8081
```

Y actualiza `VITE_API_BASE_URL` y `ADMIN_CORS_ORIGINS` con los puertos nuevos.

---

## 12. Checklist Fase 1 y Fase 2

### Fase 1 — API + panel (ahora)

- [ ] Docker instalado y funcionando
- [ ] `.env` con `JWT_SECRET`, `NVIDIA_API_KEY` y credenciales admin
- [ ] `docker compose up -d --build` sin errores
- [ ] `http://...:8000/health` responde OK
- [ ] Login en el panel OK
- [ ] Documentos subidos y **reindexados**
- [ ] Chat de prueba en el panel OK
- [ ] Backups planificados (volúmenes Docker)
- [ ] HTTPS en producción (api + admin)

### Fase 2 — WordPress (después)

- [ ] API accesible desde internet con URL pública estable
- [ ] Plugin activado y URL base = API pública
- [ ] Widget probado en una página real del sitio

---

## 13. Fase 2 — WordPress (más adelante)

Cuando la API y el panel estén estables en el servidor, conecta el widget al sitio web.

### Requisito previo

La API debe tener una **URL pública** accesible desde donde esté WordPress, por ejemplo:

```text
https://api.facultad.edu
```

Si WordPress está en un hosting remoto y la API solo en `localhost` de tu PC, el plugin **no podrá conectar**.

### Pasos

1. Copiar la carpeta `chatbot/` a `wp-content/plugins/` del sitio WordPress
2. **Plugins → Activar “Chatbot Facultad”**
3. **Ajustes → Chatbot Facultad**
4. **URL base de la API:** la URL pública de la Fase 1 (p. ej. `https://api.facultad.edu`)
5. Guardar y probar el widget en una página del sitio

El plugin usa un **proxy REST** de WordPress: el navegador del visitante habla con WordPress, y WordPress reenvía la pregunta a `POST /chat` de la API.

### Probar la API sin WordPress (Fase 1)

Puedes validar el chat desde:

- **Panel admin → Chat de prueba**
- **Swagger:** [http://localhost:8000/swagger](http://localhost:8000/swagger) → `POST /chat`
- **curl:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-1","message":"Hola"}'
```

---

## 14. Archivos de despliegue incluidos

| Archivo | Descripción |
|---------|-------------|
| `Dockerfile` | Imagen de la API Python |
| `docker-entrypoint.sh` | Espera PostgreSQL, migraciones, seed y arranca uvicorn |
| `docker-compose.yml` | Orquesta postgres + api + admin |
| `.env.docker.example` | Plantilla de variables para Docker |
| `../chatbot-admin/Dockerfile` | Build del panel + nginx |
| `../chatbot-admin/nginx.conf` | Configuración SPA del panel |

Documentación adicional del backend: [ADMIN.md](ADMIN.md) y [README.md](README.md).

---

## 15. Resumen en una frase

**Fase 1:** Instalas Docker → copias `.env.docker.example` a `.env` → pones tus claves → `docker compose up -d --build` → entras a `localhost:8080` → subes PDFs → pruebas el chat en el panel.

**Fase 2 (después):** Conectas el plugin WordPress a la URL pública de la API.

Si te atascas en un paso concreto, revisa la sección 11 o los logs con `docker compose logs -f`.
