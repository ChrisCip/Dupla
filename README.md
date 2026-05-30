# Grupo Dupla — Core

## Descripción del sistema

**Dupla** es una plataforma web de gestión de **obras y proyectos de arquitectura** pensada para equipos internos: reúne en un solo entorno el **ciclo de vida del proyecto** (fases y flujo de trabajo), el **repositorio documental** (planos y anexos en formatos técnicos habituales, con carpetas, metadatos y trazabilidad), la **comunicación** (chat con canal general, conversaciones directas, grupos y hilo vinculado a cada obra), y la **operación** (tablero de tareas tipo Kanban, con posibilidad de filtrar por proyecto).

Cada **proyecto** se abre en un **workspace** con pestañas: datos generales, flujo y fase actual, **archivos**, entregas de planos, revisiones, **especificaciones y pliegos** (incl. integración con plantillas GA-FO cuando están disponibles), **presupuesto** y metadatos asociados, **eventos** (historial/auditoría), **materiales**, etc. **Gerencia** crea obras, arrastra fases en tablero o transiciona con reglas de dominio, y administra el **alta de usuarios** y asignación del **módulo Arquitectura**, condición para acceder al negocio de proyectos. El resto de **roles** (Control, Presupuesto, Arquitectura) operan en el límite de su permiso sobre cada proyecto. La autenticación es por **JWT**; la API está en **FastAPI** con **PostgreSQL** (persistencia) y **Redis** (caché, sincronización de chat y avisos). El cliente es **React** con **Vite**, enrutado bajo una shell autenticada con menú lateral, y expone además **tutoriales guiados** (recorridos in situ) y una guía de referencia escrita.

Este repositorio es un **monorepo**: `backend` (API, servicios, repositorios, migraciones **Alembic**, seed de demo) y `frontend` (TypeScript, Tailwind, **Zustand** para sesión/estado, formularios con **react-hook-form** y **Zod**). Puede ejecutarse con **Docker Compose** (recomendado) o con backend y frontend levantados por separado. La descripción de **módulos funcionales, flujos y pantallas** vive en [`docs/`](docs/README.md); detalles de arquitectura, variables y pruebas en [`docs/TECHNICAL.md`](docs/TECHNICAL.md). Lo que sigue en este README concentra **cómo levantar el entorno**, **usuarios de prueba** y estructura de carpetas.

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

| Usuario | Nombre | Contraseña | Rol | Uso |
|---------|--------|------------|-----|-----|
| `master@dupla.demo` | María López | `master123` | GERENCIA | Administración de usuarios; visión global |
| `tester@dupla.demo` | Carlos Ruiz | `testpass123` | CONTROL | Coordinación de proyectos, chat, tablero |
| `worker@dupla.demo` | Ana Martín | `workerpass123` | PRESUPUESTO | Operación de proyecto, chat, tablero |

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
- `backend/app/domain` — enums y reglas compartidas (workflow, tipos de archivo, etc.)
- `frontend/src` — UI, stores Zustand, esquemas Zod
- `docs/` — documentación de producto ([`docs/README.md`](docs/README.md)) y por módulo ([`docs/modules/`](docs/modules/))
