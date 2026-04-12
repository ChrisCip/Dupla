from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import app.bootstrap_path  # noqa: F401

from core.pipeline import build_budget_from_sources
from core.schemas import ProjectContext
from knowledge.bc3_embeddings import load_or_build_embeddings
from knowledge.training_data import extract_training_pairs
from processors.bc3_parser import parse_bc3

from app.services.job_store import JobRecord, JobStore

logger = logging.getLogger("dupla.api.budget_service")


class BudgetBuildError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _lib_data_pres_default() -> Path:
    return Path(__file__).resolve().parents[2] / "lib" / "data" / "PRES.xlsx"


def _load_cad_facts(store: JobStore, job_id: str, record: JobRecord) -> dict[str, Any]:
    if record.status != "succeeded" or not record.outputs:
        raise BudgetBuildError(
            "job_not_ready",
            "Job must have status succeeded with outputs before building a budget.",
        )
    norm_name = record.outputs.get("normalized_json")
    if not norm_name:
        raise BudgetBuildError("no_normalized_json", "Job outputs missing normalized_json.")
    norm_path = store.outputs_dir(job_id) / norm_name
    if not norm_path.is_file():
        raise BudgetBuildError(
            "normalized_missing",
            f"Normalized JSON not found at {norm_path}",
        )

    try:
        return json.loads(norm_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BudgetBuildError("invalid_normalized_json", f"Invalid JSON: {exc}") from exc


def _resolve_bc3_catalog_path(bc3_catalog_path: Path) -> Path:
    if bc3_catalog_path.is_file():
        return bc3_catalog_path
    raise BudgetBuildError(
        "bc3_missing",
        f"BC3 catalog not found at {bc3_catalog_path}. Restore api/data/TGIU.bc3 or set BC3_CATALOG_PATH.",
    )


def _resolve_pres_xlsx_path(pres_xlsx_path: Path | None) -> str | None:
    if pres_xlsx_path is not None and pres_xlsx_path.is_file():
        return str(pres_xlsx_path)
    default_xlsx = _lib_data_pres_default()
    if default_xlsx.is_file():
        return str(default_xlsx)
    return None


def _training_pairs_from_xlsx(xlsx_path: str | None) -> list[Any]:
    if not xlsx_path:
        return []
    try:
        pairs = extract_training_pairs(xlsx_path)
        logger.info("Training pairs loaded: %d from %s", len(pairs), xlsx_path)
        return pairs
    except Exception:
        logger.warning("Failed to load training pairs from %s", xlsx_path, exc_info=True)
        return []


def compute_budget_for_job(
    job_id: str,
    *,
    job_data_dir: Path,
    bc3_catalog_path: Path,
    pres_xlsx_path: Path | None,
) -> dict[str, Any]:
    store = JobStore(job_data_dir)
    record = store.get(job_id)
    if record is None:
        raise BudgetBuildError("not_found", "Job not found")

    cad_facts = _load_cad_facts(store, job_id, record)

    bc3_path = _resolve_bc3_catalog_path(bc3_catalog_path)
    bc3_catalog = parse_bc3(str(bc3_path))

    embedding_index = None
    if bc3_catalog.get("items"):
        try:
            embedding_index = load_or_build_embeddings(bc3_catalog)
        except Exception:
            logger.warning("BC3 embeddings failed; continuing without index", exc_info=True)
            embedding_index = None

    xlsx_path = _resolve_pres_xlsx_path(pres_xlsx_path)
    training_pairs = _training_pairs_from_xlsx(xlsx_path)

    project_name = None
    if isinstance(cad_facts.get("project"), str):
        project_name = cad_facts["project"]

    metadata: dict[str, Any] = {}
    if xlsx_path:
        metadata["xlsx_path"] = xlsx_path

    context = ProjectContext(
        project_id=job_id,
        project_name=project_name,
        bc3_path=str(bc3_path),
        metadata=metadata,
    )

    return build_budget_from_sources(
        context,
        cad_facts,
        None,
        bc3_catalog,
        embedding_index=embedding_index,
        training_pairs=training_pairs,
    )
