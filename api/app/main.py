from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI

import app.bootstrap_path  # noqa: F401

load_dotenv()

from app.config import get_settings
from app.routers import project_runs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dupla.api")

settings = get_settings()
app = FastAPI(title="Dupla API", version="0.1.0", description="Project pipeline (GEBSA IV reference) + RQ workers")
app.include_router(project_runs.router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
