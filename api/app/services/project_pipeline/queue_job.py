"""RQ entrypoint: run full project pipeline for a `run_id`."""
from __future__ import annotations

import logging
import app.bootstrap_path  # noqa: F401

from app.config import get_settings
from app.services.project_pipeline.orchestrator import execute_project_run

logger = logging.getLogger("dupla.api.queue_project")


def process_project_run(run_id: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s",
    )
    get_settings()
    try:
        execute_project_run(run_id)
    except Exception:  # noqa: BLE001
        logger.exception("Project run %s crashed", run_id)
        raise
