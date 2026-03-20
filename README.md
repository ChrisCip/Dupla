# Grupo Dupla — Módulo Arquitectura

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

Usuario semilla (tras `seed` en el contenedor backend):

- Email: `master@dupla.demo`
- Password: `master123`

## Variables de entorno (opcional)

El backend usa `pydantic-settings` con valores por defecto para demo (ver `backend/app/config.py`). En producción:

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

## Plantillas GA-FO (Excel 1:1)

Coloca los archivos oficiales como:

- `backend/app/templates/GA-FO-01-pliego.xlsx`
- `backend/app/templates/GA-FO-03-control-planos.xlsx`

Si existen, el backend los usa como base (relleno futuro); si no, genera un XLSX estructurado desde los datos del proyecto.

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
