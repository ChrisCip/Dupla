"""
BLCAD09: CAD fusionado (16 DWG) → clasificación GPT-4o por lámina del PDF combinado
→ sub-PDFs por disciplina → presupuesto Excel por disciplina (4) + presupuesto general (PDF completo).

Requiere: .env (OPENAI_API_KEY, APS), PyMuPDF, dependencias del repo.

Uso:
    python scripts/run_blcad09_discipline_pipeline.py
    python scripts/run_blcad09_discipline_pipeline.py --skip-cad-merge output/blcad09_runs/2026-01-01_120000/cad_merge
    python scripts/run_blcad09_discipline_pipeline.py --no-open-excel
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("dupla.blcad09_pipeline")

DISCIPLINE_KEYS = ("structural", "electrical", "sanitary", "finishes_architectural")
DEFAULT_PDF = REPO_ROOT / "BLCAD09" / "BLCADO900.pdf"


def _run_cmd(args: list[str]) -> str:
    logger.info("Ejecutando: %s", " ".join(args))
    proc = subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        logger.error("Subproceso falló (código %s)", proc.returncode)
        if proc.stderr:
            for line in proc.stderr.splitlines()[-80:]:
                logger.error("%s", line)
        if proc.stdout:
            for line in proc.stdout.splitlines()[-40:]:
                logger.error("stdout: %s", line)
        proc.check_returncode()
    if proc.stderr:
        for line in proc.stderr.splitlines()[-30:]:
            logger.debug("stderr: %s", line)
    out = (proc.stdout or "").strip()
    if out:
        for line in out.splitlines():
            logger.info("%s", line)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    return lines[-1].strip() if lines else ""


def _open_excels(paths: list[Path]) -> None:
    if sys.platform != "win32":
        logger.warning("Abrir Excel automático solo está implementado en Windows.")
        return
    import os

    for p in paths:
        if p.is_file():
            try:
                os.startfile(str(p))  # type: ignore[attr-defined]
                logger.info("Abierto: %s", p)
            except OSError as exc:
                logger.warning("No se pudo abrir %s: %s", p, exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="BLCAD09: split PDF por disciplina (GPT-4o) + presupuestos")
    parser.add_argument(
        "--pdf",
        type=str,
        default=str(DEFAULT_PDF),
        help="PDF combinado del proyecto (por defecto BLCAD09/BLCADO900.pdf)",
    )
    parser.add_argument(
        "--run-root",
        type=str,
        default="",
        help="Carpeta base de la corrida (por defecto output/blcad09_runs/<timestamp>/)",
    )
    parser.add_argument(
        "--skip-cad-merge",
        type=str,
        default="",
        help="Ruta a carpeta cad_merge existente con project_merged.normalized.json (salta APS)",
    )
    parser.add_argument(
        "--skip-classify",
        action="store_true",
        help="Reusar pdf_split/ existente (page_disciplines.json + split_*.pdf)",
    )
    parser.add_argument(
        "--classify-dpi",
        type=int,
        default=110,
        help="DPI para miniaturas de clasificación (más bajo = más barato)",
    )
    parser.add_argument(
        "--no-open-excel",
        action="store_true",
        help="No abrir los .xlsx al final",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.is_file():
        logger.error("No existe el PDF: %s", pdf_path)
        return 1

    if args.run_root:
        run_root = Path(args.run_root).resolve()
    else:
        run_root = (REPO_ROOT / "output" / "blcad09_runs" / datetime.now().strftime("%Y-%m-%d_%H%M%S")).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    cad_dir = run_root / "cad_merge"
    split_dir = run_root / "pdf_split"
    logger.info("Carpeta de corrida: %s", run_root)

    merged_json: Path
    if args.skip_cad_merge:
        cad_dir = Path(args.skip_cad_merge).resolve()
        merged_json = cad_dir / "project_merged.normalized.json"
        if not merged_json.is_file():
            logger.error("No hay merge en: %s", merged_json)
            return 1
        logger.info("Reuso CAD fusionado: %s", merged_json)
    else:
        cad_dir.mkdir(parents=True, exist_ok=True)
        _run_cmd(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "run_multi_dwg_project_cad.py"),
                "--pattern",
                "BLCAD09/BLCAD09*.dwg",
                "--blcad-09001-16-only",
                "--output-dir",
                str(cad_dir),
                "--project-id",
                "blcad09",
                "--project-name",
                "BLCAD09 — merge 16 planos",
            ]
        )
        merged_json = cad_dir / "project_merged.normalized.json"
        if not merged_json.is_file():
            logger.error("Falló la fusión CAD: no está %s", merged_json)
            return 1

    if args.skip_classify:
        split_dir.mkdir(parents=True, exist_ok=True)
        if not (split_dir / "page_disciplines.json").is_file():
            logger.error("--skip-classify requiere %s", split_dir / "page_disciplines.json")
            return 1
        logger.info("Saltando clasificación; usando split en %s", split_dir)
        from pipeline.pdf_discipline_split import write_split_pdfs_by_discipline
        import json

        data = json.loads((split_dir / "page_disciplines.json").read_text(encoding="utf-8"))
        from pipeline.pdf_discipline_split import PageDiscipline

        labels = [
            PageDiscipline(page_index=int(x["page"]) - 1, discipline=x["discipline"], title=x.get("title", ""))
            for x in data["pages"]
        ]
        splits = write_split_pdfs_by_discipline(pdf_path, labels, split_dir)
    else:
        from pipeline.pdf_discipline_split import classify_pdf_pages, write_split_pdfs_by_discipline

        split_dir.mkdir(parents=True, exist_ok=True)
        labels = classify_pdf_pages(pdf_path, split_dir, dpi=args.classify_dpi)
        splits = write_split_pdfs_by_discipline(pdf_path, labels, split_dir)

    excel_paths: list[Path] = []
    cad_xlsx = cad_dir / "dupla_presupuesto_proyecto_merged.xlsx"
    if cad_xlsx.is_file():
        excel_paths.append(cad_xlsx)

    try:
        import fitz
    except ImportError:
        fitz = None  # type: ignore[assignment]

    for disc in DISCIPLINE_KEYS:
        sub_pdf = splits.get(disc)
        if not sub_pdf or not sub_pdf.is_file():
            logger.info("Sin PDF para disciplina %s — se omite.", disc)
            continue
        n = 1
        if fitz is not None:
            try:
                doc = fitz.open(sub_pdf)
                n = len(doc)
                doc.close()
            except Exception:
                n = 1
        if n == 0:
            continue
        vision_sub = run_root / "vision" / disc
        vision_sub.mkdir(parents=True, exist_ok=True)
        last = _run_cmd(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "run_merged_cad_pdf_vision.py"),
                "--pdf",
                str(sub_pdf),
                "--merged-json",
                str(merged_json),
                "--vision-output-dir",
                str(vision_sub),
                "--project-id",
                "blcad09",
                "--project-name",
                f"BLCAD09 — visión {disc}",
                "--excel-suffix",
                f"blcad09_{disc}",
                "--vision-profile",
                disc,
            ]
        )
        if last:
            excel_paths.append(Path(last))

    gen_dir = run_root / "vision" / "general_full_pdf"
    gen_dir.mkdir(parents=True, exist_ok=True)
    last_gen = _run_cmd(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_merged_cad_pdf_vision.py"),
            "--pdf",
            str(pdf_path),
            "--merged-json",
            str(merged_json),
            "--vision-output-dir",
            str(gen_dir),
            "--project-id",
            "blcad09",
            "--project-name",
            "BLCAD09 — presupuesto general (PDF completo)",
            "--excel-suffix",
            "blcad09_general",
            "--vision-profile",
            "general",
        ]
    )
    if last_gen:
        excel_paths.append(Path(last_gen))

    summary = run_root / "EXCELS_GENERADOS.txt"
    summary.write_text(
        "\n".join(str(p) for p in excel_paths) + "\n",
        encoding="utf-8",
    )
    logger.info("Resumen escrito: %s", summary)
    print(summary)

    if not args.no_open_excel:
        _open_excels(excel_paths)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
