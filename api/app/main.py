from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI

import app.bootstrap_path  # noqa: F401

load_dotenv()

from app.config import get_settings
from app.routers import budget, projects

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dupla.api")

settings = get_settings()
app = FastAPI(title="Dupla API", version="0.1.0")
app.include_router(projects.router, prefix=settings.api_prefix)
app.include_router(budget.router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
