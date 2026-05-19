#!/usr/bin/env python3
"""Ingest architect validation CSV into clash learning memory."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from coordination.learning.feedback_schema import ClashFeedback
from coordination.learning.feedback_store import append_feedback
from coordination.learning.memory_digest import build_patterns_catalog, build_project_profile, slugify


DEFAULT_FEEDBACK_PATH = REPO_ROOT / "knowledge" / "clash_memory" / "feedback_log.jsonl"
DEFAULT_PATTERNS_CATALOG = REPO_ROOT / "knowledge" / "clash_memory" / "patterns_catalog.md"
DEFAULT_PROJECT_PROFILES_DIR = REPO_ROOT / "knowledge" / "clash_memory" / "project_profiles"
ALLOWED_LABELS = {"REAL_CLASH", "FALSE_POSITIVE", "MARGINAL"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest validation_template.csv into clash memory.")
    parser.add_argument("--input", type=Path, required=True, help="CSV exported from validation template.")
    parser.add_argument("--project", type=str, required=True, help="Project name.")
    parser.add_argument("--reviewer", type=str, required=True, help="Reviewer name.")
    parser.add_argument("--run", type=str, required=True, help="Run label.")
    parser.add_argument("--project-type", type=str, default=None, help="Optional project type.")
    parser.add_argument("--feedback-path", type=Path, default=DEFAULT_FEEDBACK_PATH)
    parser.add_argument("--patterns-catalog", type=Path, default=DEFAULT_PATTERNS_CATALOG)
    parser.add_argument("--project-profiles-dir", type=Path, default=DEFAULT_PROJECT_PROFILES_DIR)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"No existe el archivo CSV: {args.input}")

    ingested = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    with args.input.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            label = str(row.get("human_label") or "").strip().upper()
            incident_id = str(row.get("incident_id") or "").strip()
            if not incident_id or not label:
                continue
            if label not in ALLOWED_LABELS:
                raise ValueError(
                    f"Label invalido en incident_id={incident_id}: {label}. "
                    f"Valores permitidos: {sorted(ALLOWED_LABELS)}"
                )
            feedback = ClashFeedback(
                run_label=args.run,
                incident_id=incident_id,
                project_name=args.project,
                discipline_pair=_pick(row, "discipline_pair", "disciplinas"),
                level_id=_pick(row, "level_id", "nivel"),
                layer_pair=_pick(row, "layer_pair", "layers"),
                geometry_metrics={
                    "area_m2": _float_value(row.get("area_m2")),
                    "member_count": _int_value(row.get("member_count")),
                    "overlap_depth_mm": _float_value(row.get("overlap_depth_mm")),
                },
                human_label=label,
                human_reason=str(row.get("human_reason") or "").strip(),
                reviewer=str(row.get("reviewer") or args.reviewer).strip() or args.reviewer,
                timestamp=now_iso,
                project_type=args.project_type,
                notes=str(row.get("notes") or "").strip() or None,
            )
            append_feedback(feedback, args.feedback_path)
            ingested += 1

    build_patterns_catalog(args.feedback_path, args.patterns_catalog)
    profile_path = args.project_profiles_dir / f"{slugify(args.project)}.md"
    build_project_profile(args.feedback_path, args.project, profile_path)
    print(
        f"Ingestados {ingested} registros en {args.feedback_path}. "
        f"Catalogo: {args.patterns_catalog}. Perfil: {profile_path}."
    )
    return 0


def _pick(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _float_value(value: object) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _int_value(value: object) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

