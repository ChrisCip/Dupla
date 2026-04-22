# Dupla API (encapsulated)

Self-contained package under `api/` (no imports from the monorepo parent). Runs the **GEBSA IV–style** multi-discipline project pipeline: download PDF/DWG from URLs, APS, vision, budget, Excel + BC3 per discipline, shared BC3 embeddings.

## Layout

- `app/` — FastAPI, `POST /api/v1/project-runs`, `GET /api/v1/project-runs/{run_id}`
- `lib/` — Vendored domain: `disciplines/`, `core/`, `agents/`, `knowledge/`, `pipeline/`, `rules_engine/`, `processors/`, `budget/`, `aps_integration/`
- `data/` — `*.bc3`, optional `PRES.xlsx`
- `worker/` — RQ worker: `python -m worker` from `api/` (paths: `.` and `lib` on `PYTHONPATH` / `pip install -e .`)

## Run locally

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# .env: OPENAI_API_KEY, CLIENT_ID, CLIENT_SECRET, APS/S3 as needed; REDIS_URL
redis-server  # or docker compose
uvicorn app.main:app --reload --port 8000
python -m worker
```

## Job queue

- Queue name: `RQ_QUEUE_NAME` (default `dupla_jobs`)
- Enqueued function: `app.services.project_pipeline.queue_job.process_project_run` with `run_id`

## Caching

- Renders: `data/cache/rendered/<sha256(pdf)>/pages/` (optional, `use_render_cache` in config)

## Docker

Build with context = this directory (`api/`). Image copies `app`, `lib`, `worker`, `data`.
