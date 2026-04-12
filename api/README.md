# Dupla API

Small FastAPI service that accepts a **DWG** upload, enqueues **Autodesk Platform Services (APS) extraction + CAD normalization** asynchronously, and exposes job status and **normalized CAD JSON** via HTTP. A dedicated endpoint builds a **budget** from stored CAD facts using the bundled catalog **`api/data/TGIU.bc3`** (override with `BC3_CATALOG_PATH`).

## Layout

- `app/` — HTTP layer (FastAPI, job metadata, RQ enqueue).
- `lib/` — Dupla domain packages (`core`, `aps_integration`, `agents`, …) copied from the main repo for a self-contained deploy.
- `worker/` — RQ worker process (`python -m worker`).
- `data/TGIU.bc3` — bundled BC3 catalog for the budget endpoint.
- `data/jobs/{uuid}/` — Per-job `inputs/`, `outputs/`, and `meta.json` (`jobs/` ignored by git).

## Requirements

- Python 3.11+
- Redis (for RQ), local or Docker
- `.env` with APS credentials (same variables as `lib/aps_integration/aps_auth.py`): `CLIENT_ID`, `CLIENT_SECRET`, and `APS_BUCKET_NAME` in `lib/aps_integration/oss_manager.py` / env

## Local setup

```bash
cd api
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill APS_* and any other keys
```

Start Redis (example with Homebrew): `redis-server`

Run API:

```bash
export JOB_DATA_DIR="$PWD/data"
export REDIS_URL="redis://127.0.0.1:6379/0"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run worker (separate terminal, same `cwd` and env):

```bash
export PYTHONPATH="$PWD:$PWD/lib"
export JOB_DATA_DIR="$PWD/data"
export REDIS_URL="redis://127.0.0.1:6379/0"
python -m worker
```

## HTTP

- `GET /health` — liveness.
- `POST /api/v1/projects` — `multipart/form-data` field **`dwg`** (`.dwg` file). Returns **202** with `job_id` and `status_url`.
- `GET /api/v1/projects/{job_id}/results` — job status; when `succeeded`, includes **`cad_facts`** (normalized JSON) and output filenames under `outputs`.
- `POST /api/v1/projects/{job_id}/budget` — no body. Requires job `succeeded`. Loads **`api/data/TGIU.bc3`** (or **`BC3_CATALOG_PATH`**). Returns the composed budget JSON (chapters, lines, takeoffs, etc.).

### curl

```bash
# Upload
curl -sS -X POST "http://127.0.0.1:8000/api/v1/projects" \
  -F "dwg=@/path/to/file.dwg"

# Poll results (replace JOB_ID)
curl -sS "http://127.0.0.1:8000/api/v1/projects/JOB_ID/results"

# Budget (after job succeeded; uses api/data/TGIU.bc3)
curl -sS -X POST "http://127.0.0.1:8000/api/v1/projects/JOB_ID/budget"
```

## Docker Compose

From `api/`:

```bash
cp .env.example .env   # add secrets
docker compose up --build
```

The image includes **`data/TGIU.bc3`**. Compose mounts only **`./data/jobs`** so the catalog file in the image is not shadowed.

Services: **redis**, **api** (port 8000), **worker**. Job files persist under `./data/jobs`.

## Tests

```bash
cd api
pip install -e ".[dev]"
pytest tests/ -v
```
