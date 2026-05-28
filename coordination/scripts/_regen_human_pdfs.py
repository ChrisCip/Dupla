"""Quick helper to regenerate the human PDFs for the three demo runs.

Used during the visual polish work — keeps the same data, just re-renders the
PDF with the latest layout.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from coordination.reporting.human_report_pdf import render_coordination_human_report_pdf
from coordination.reporting.reporting import build_coordination_report_context


def regenerate(run_dir: Path, revision_md_name: str, project_name: str) -> Path:
    primary = json.loads((run_dir / "primary_incidents.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    coord_audit_path = run_dir / "coordinate_audit.json"
    coord_audit = json.loads(coord_audit_path.read_text(encoding="utf-8")) if coord_audit_path.is_file() else {}
    pair_path = run_dir / "pair_schedule.json"
    pair_schedule = json.loads(pair_path.read_text(encoding="utf-8")) if pair_path.is_file() else {}
    ctx = build_coordination_report_context(
        summary_payload=summary,
        primary_payload=primary,
        coordinate_audit_payload=coord_audit,
        pair_schedule_payload=pair_schedule,
    )
    revision_path = run_dir / revision_md_name
    revision_md = revision_path.read_text(encoding="utf-8") if revision_path.is_file() else ""
    out = run_dir / "coordination_report_human.pdf"
    render_coordination_human_report_pdf(
        output_path=out,
        project_name=primary.get("project_name", project_name),
        run_label=run_dir.name,
        generated_at=str(primary.get("generated_at", summary.get("generated_at", ""))),
        report_context=ctx,
        primary_payload=primary,
        all_elements=[],
        revision_md=revision_md,
    )
    return out


def main(runs: Iterable[tuple[str, str, str]]) -> None:
    for run_path, revision_name, project_name in runs:
        run_dir = Path(run_path)
        if not run_dir.is_dir():
            print(f"SKIP {run_dir} (missing)")
            continue
        out = regenerate(run_dir, revision_name, project_name)
        size = out.stat().st_size
        print(f"OK {out} ({size} bytes)")


if __name__ == "__main__":
    main(
        [
            (
                "analysis_output/tortuga_c40_package_run",
                "REVISION_CLASHES_ARQUITECTO_TORTUGA_C40.md",
                "TORTUGA C40",
            ),
            (
                "analysis_output/serena18_package_run",
                "REVISION_CLASHES_ARQUITECTO_SERENA_18.md",
                "SERENA 18",
            ),
            (
                "analysis_output/nasas09_verification_run",
                "REVISION_CLASHES_ARQUITECTO_NASAS_09.md",
                "NASAS 09",
            ),
        ]
    )
