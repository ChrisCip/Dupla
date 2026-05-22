#!/usr/bin/env python3
"""Optional IFC cross-check over scheduled DWG pair schedule."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-check DWG primary incidents against IFC clash results.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--pair-schedule", type=Path, default=None)
    parser.add_argument("--primary-incidents", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--ifcconvert-bin", type=str, default="IfcConvert")
    parser.add_argument("--ifcclash-bin", type=str, default="ifcclash")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    pair_schedule_path = (args.pair_schedule or (run_dir / "pair_schedule.json")).resolve()
    primary_path = (args.primary_incidents or (run_dir / "primary_incidents.json")).resolve()
    output_path = (args.output or (run_dir / "ifc_clash_crosscheck.json")).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not pair_schedule_path.is_file() or not primary_path.is_file():
        output_path.write_text(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "missing_inputs",
                    "pair_schedule": str(pair_schedule_path),
                    "primary_incidents": str(primary_path),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return 0

    pair_payload = json.loads(pair_schedule_path.read_text(encoding="utf-8"))
    primary_payload = json.loads(primary_path.read_text(encoding="utf-8"))
    scheduled = [item for item in pair_payload.get("pairs") or [] if bool(item.get("scheduled"))]

    ifcconvert = shutil.which(args.ifcconvert_bin)
    ifcclash = shutil.which(args.ifcclash_bin)
    if ifcclash is None:
        output_path.write_text(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "ifcclash_not_available",
                    "scheduled_pairs": len(scheduled),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return 0

    clash_sets = {"clash_sets": []}
    ifc_pairs: list[dict[str, Any]] = []
    work_dir = run_dir / "ifc_crosscheck"
    work_dir.mkdir(parents=True, exist_ok=True)

    for idx, pair in enumerate(scheduled):
        file_a = str(pair.get("file_a") or "")
        file_b = str(pair.get("file_b") or "")
        src_a = _resolve_source(file_a, run_dir)
        src_b = _resolve_source(file_b, run_dir)
        if src_a is None or src_b is None:
            continue
        ifc_a = _to_ifc(src_a, work_dir / f"pair_{idx:03d}_a.ifc", ifcconvert)
        ifc_b = _to_ifc(src_b, work_dir / f"pair_{idx:03d}_b.ifc", ifcconvert)
        if ifc_a is None or ifc_b is None:
            continue
        set_name = f"pair_{idx:03d}"
        clash_sets["clash_sets"].append(
            {
                "name": set_name,
                "a": [{"file": str(ifc_a)}],
                "b": [{"file": str(ifc_b)}],
            }
        )
        ifc_pairs.append({"name": set_name, "file_a": file_a, "file_b": file_b, "ifc_a": str(ifc_a), "ifc_b": str(ifc_b)})

    if not clash_sets["clash_sets"]:
        output_path.write_text(
            json.dumps({"status": "skipped", "reason": "no_ifc_pairs_built", "scheduled_pairs": len(scheduled)}, indent=2),
            encoding="utf-8",
        )
        return 0

    clash_sets_path = work_dir / "clash_sets.json"
    clash_sets_path.write_text(json.dumps(clash_sets, indent=2), encoding="utf-8")
    result_path = work_dir / "ifcclash_results.json"
    cmd = [ifcclash, str(clash_sets_path), "--output", str(result_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not result_path.is_file():
        output_path.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "reason": "ifcclash_execution_failed",
                    "stdout_tail": (proc.stdout or "")[-1000:],
                    "stderr_tail": (proc.stderr or "")[-1000:],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return 0

    ifc_result = json.loads(result_path.read_text(encoding="utf-8"))
    matched_pairs = {item.get("name") for item in ifc_result.get("clash_sets") or []}
    incidents = primary_payload.get("incidents") or []
    promoted = 0
    for incident in incidents:
        incident_name = str(incident.get("incident_id") or "")
        # Conservative mapping: if any pair was confirmed by IFC, keep incident confidence at least medium/high.
        if matched_pairs and incident_name:
            representative = incident.get("representative_conflict") or {}
            representative["confidence"] = "high"
            incident["representative_conflict"] = representative
            promoted += 1

    output_path.write_text(
        json.dumps(
            {
                "status": "completed",
                "scheduled_pairs": len(scheduled),
                "ifc_pairs": ifc_pairs,
                "ifc_clash_result_path": str(result_path),
                "matched_sets": sorted(matched_pairs),
                "incidents_promoted_to_high_confidence": promoted,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


def _resolve_source(rel_or_abs: str, run_dir: Path) -> Path | None:
    if not rel_or_abs:
        return None
    direct = Path(rel_or_abs)
    if direct.is_file():
        return direct.resolve()
    alt = (run_dir.parent / rel_or_abs).resolve()
    if alt.is_file():
        return alt
    return None


def _to_ifc(source: Path, target: Path, ifcconvert_bin: str | None) -> Path | None:
    if source.suffix.lower() == ".ifc":
        return source
    if ifcconvert_bin is None:
        return None
    cmd = [ifcconvert_bin, str(source), str(target)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not target.is_file():
        return None
    return target


if __name__ == "__main__":
    raise SystemExit(main())
