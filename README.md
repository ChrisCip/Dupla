# Grupo Dupla — Core

Monorepo: **FastAPI** (PostgreSQL + Redis) + **Vite/React** (Tailwind, Zod, Zustand).

## Requisitos

- **Docker + Docker Compose** (recomendado para demo completa)
- Para desarrollo local del backend: **Python 3.12 o 3.13** (3.14 puede fallar al instalar `pydantic-core` sin ruedas precompiladas)

## Levantar en demo (Docker)

```bash
docker compose up --build
```

- API: `http://localhost:8000` — Swagger: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173` (Nginx sirve `dist` y proxy `/api` → backend)

Usuarios semilla (tras `python -m app.seed` o el entrypoint Docker del backend):

| Usuario | Contraseña | Rol | Uso |
|--------|------------|-----|-----|
| `master@dupla.demo` | `master123` | MASTER | Administración de usuarios; tablero solo lectura |
| `tester@dupla.demo` | `testpass123` | COORDINATOR | Proyectos, chat, tablero con escritura |
| `worker@dupla.demo` | `workerpass123` | WORKER | Proyectos, chat, tablero con escritura |

El seed es **idempotente**: si ya existía `master@dupla.demo` de una versión anterior, al volver a ejecutar el seed se añaden `tester` y `worker` si faltan.

## Variables de entorno (opcional)

El backend usa `pydantic-settings` con valores por defecto para demo (ver `backend/app/config.py`). Por defecto **Postgres y Redis apuntan a `127.0.0.1`** para poder ejecutar `alembic`, `seed` o `uvicorn` en tu máquina mientras los contenedores publican los puertos 5432 y 6379. En **Docker Compose**, el servicio `backend` define `DATABASE_URL` / `REDIS_URL` con los hostnames `postgres` y `redis`.

En producción:

- `JWT_SECRET`
- `DATABASE_URL`
- `REDIS_URL`
- `CORS_ORIGINS`

## Desarrollo frontend (sin Docker)

```bash
cd frontend
pnpm install
pnpm dev
```

Proxy Vite: `/api` → `http://127.0.0.1:8000` (levanta el backend aparte).

## Backend local (sin Docker)

Con Postgres en `127.0.0.1:5432` (por ejemplo `docker compose up -d postgres redis`):

```bash
cd backend
source venv/bin/activate   # o tu entorno
alembic upgrade head       # crea tablas; obligatorio antes del seed
python -m app.seed         # master, tester (COORDINATOR), worker — ver tabla arriba
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Si ejecutas `seed` sin migraciones, verás un error indicando que falta `alembic upgrade head`.

## Plantillas GA-FO (Excel 1:1)

Coloca el Excel oficial del pliego como (nombre recomendado):

- `backend/app/templates/GA-FO-01-(06-2025)-V02- Pliego de Condiciones - Arquitectura.xlsx`

También se acepta `GA-FO-01-pliego.xlsx` como alias. Opcional: `GA-FO-03-control-planos.xlsx` para control de planos.

Si el pliego oficial está presente, la exportación rellena esa plantilla (cabeceras reconocidas por texto, filas antes de `TOTAL`). Si no, el backend genera un XLSX genérico.

## Pruebas

**Frontend**

```bash
cd frontend
pnpm test
pnpm build
```

**Backend (requiere PostgreSQL en `127.0.0.1:5432`; Redis es opcional gracias a fallback en caché)**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

Si no hay Postgres local, los tests se saltan con un mensaje explícito.

## Estructura

- `backend/app/routes` — rutas HTTP
- `backend/app/services` — reglas de negocio
- `backend/app/repositories` — acceso a datos
- `frontend/src` — UI, stores Zustand, esquemas Zod
