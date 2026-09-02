#!/bin/sh
set -e

echo ">> Esperando a que PostgreSQL este disponible..."
python <<'PY'
import os
import sys
import time

import psycopg

url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not url:
    print("ERROR: DATABASE_URL no esta definida.", file=sys.stderr)
    sys.exit(1)

for attempt in range(1, 31):
    try:
        with psycopg.connect(url, connect_timeout=3):
            break
    except Exception as exc:
        print(f"   intento {attempt}/30: {exc}")
        time.sleep(2)
else:
    print("ERROR: no se pudo conectar a PostgreSQL.", file=sys.stderr)
    sys.exit(1)
PY

echo ">> Ejecutando migraciones (alembic)..."
alembic upgrade head

echo ">> Creando admin inicial si no existe..."
python -m admin.seed

echo ">> Iniciando API en el puerto 8000..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
