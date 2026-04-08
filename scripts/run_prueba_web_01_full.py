"""
Pipeline BLCAD + PDF del mismo proyecto (sin PRES ni comparaciones):
  1) BLCAD14001–14015 → APS → merge (y presupuesto CAD-only opcional, sin PRES)
  2) Merge + PDF → GPT visión → Excel: dupla_presupuesto_generado_cad_vision_<project_id>.xlsx

PRES.xlsx no interviene (es de otro proyecto / planos 8- ACAD).

Salida: output/prueba_web_01/run_<fecha_hora>/

Uso:
    python scripts/run_prueba_web_01_full.py
    python scripts/run_prueba_web_01_full.py --pdf "Batch_Publish_20260406 (Conflicted Copy).pdf"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _excel_slug(project_id: str) -> str:
    s = project_id.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_") or "proyecto"
    return s[:80]


def _write_run_readme(
    run_root: Path,
    *,
    pdf: Path,
    vision_dir: Path,
    cad_xlsx: Path,
    gen_xlsx: Path,
) -> None:
    lines = [
        "proyecto=prueba_web_01",
        f"fecha={datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"pdf={pdf}",
        f"carpeta_corrida={run_root}",
        f"cad_merged_xlsx={cad_xlsx} (solo CAD, sin PRES)",
        f"pdf_vision_dir={vision_dir}",
        f"presupuesto_cad_vision_xlsx={gen_xlsx}",
        "nota=No se usa PRES.xlsx; BC3 + embeddings únicamente.",
        "",
    ]
    (run_root / "README_CORRIDA.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="BLCAD + PDF + GPT (sin PRES)")
    parser.add_argument(
        "--pdf",
        type=str,
        default=str(REPO_ROOT / "Batch_Publish_20260406 (Conflicted Copy).pdf"),
    )
    parser.add_argument(
        "--project-id",
        default="prueba_web_01",
        help="Define el sufijo del Excel: dupla_presupuesto_generado_cad_vision_<id>",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.is_file():
        print(f"No existe el PDF: {pdf_path}", file=sys.stderr)
        return 1

    slug = _excel_slug(args.project_id)
    run_tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_root = (REPO_ROOT / "output" / "prueba_web_01" / f"run_{run_tag}").resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    vision_dir = run_root / "salida_pdf_gpt"

    py = sys.executable
    cad_script = REPO_ROOT / "scripts" / "run_multi_dwg_project_cad.py"
    vis_script = REPO_ROOT / "scripts" / "run_merged_cad_pdf_vision.py"

    cmd1 = [
        py,
        str(cad_script),
        "--output-dir",
        str(run_root),
        "--blcad-01-15-only",
        "--pattern",
        "BLCAD*.dwg",
        "--project-id",
        args.project_id,
        "--project-name",
        f"{args.project_id} — batch BLCAD14001–14015",
    ]
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}

    print("=== 1) APS + merge CAD (sin PRES) ===", flush=True)
    r1 = subprocess.run(cmd1, cwd=str(REPO_ROOT), env=env)
    if r1.returncode != 0:
        return r1.returncode

    merged = run_root / "project_merged.normalized.json"
    if not merged.is_file():
        print(f"No se creó {merged}", file=sys.stderr)
        return 1

    cmd2 = [
        py,
        str(vis_script),
        "--pdf",
        str(pdf_path),
        "--merged-json",
        str(merged),
        "--vision-output-dir",
        str(vision_dir.resolve()),
        "--project-id",
        args.project_id,
        "--project-name",
        f"{args.project_id} — CAD fusionado + PDF (GPT visión)",
    ]
    print("=== 2) PDF + GPT visión → dupla_presupuesto_generado_cad_vision_%s ===" % slug, flush=True)
    r2 = subprocess.run(cmd2, cwd=str(REPO_ROOT), env=env)
    if r2.returncode != 0:
        return r2.returncode

    gen_xlsx = (vision_dir / f"dupla_presupuesto_generado_cad_vision_{slug}.xlsx").resolve()
    cad_xlsx = (run_root / "dupla_presupuesto_proyecto_merged.xlsx").resolve()

    _write_run_readme(
        run_root,
        pdf=pdf_path,
        vision_dir=vision_dir,
        cad_xlsx=cad_xlsx,
        gen_xlsx=gen_xlsx,
    )

    summary = {
        "run_root": str(run_root),
        "merged_json": str(merged),
        "vision_dir": str(vision_dir),
        "presupuesto_cad_vision_xlsx": str(gen_xlsx) if gen_xlsx.is_file() else None,
        "presupuesto_cad_only_xlsx": str(cad_xlsx) if cad_xlsx.is_file() else None,
        "pres_usado": False,
    }
    (run_root / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(str(gen_xlsx), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
