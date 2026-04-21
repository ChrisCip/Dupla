"""
NASAS 09 — tres corridas de validación (PPR, PP, P) con salidas bajo:
  aps_integration/NASAS 09/outputs/corridas/corrida_<tag>/

1) corrida_PPR — planos (PDF) + pliego (xlsx→PDF texto) + revisión (PDF)
2) corrida_PP  — planos + pliego
3) corrida_P   — solo planos

Requisitos: .env con OPENAI_API_KEY y credenciales APS; BC3 en data/TGIU.bc3.

Uso:
  python scripts/run_nasas09_corridas.py --dry-run
  python scripts/run_nasas09_corridas.py --only PPR
  python scripts/run_nasas09_corridas.py --reuse-cad aps_integration/NASAS 09/outputs/corridas/_cad_merge
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from compare_budget import (  # noqa: E402
    analyze_budget_by_canonical_discipline,
    analyze_budget_pair,
    build_comparison_markdown,
    build_comparison_report,
)
from pipeline.nasas_pdf_utils import (  # noqa: E402
    collect_pdfs_recursive,
    merge_pdfs,
    pliego_xlsx_to_text_pdf,
    sanitize_filename,
)
from pipeline.nasas_quality_report import (  # noqa: E402
    call_openai_quality_narrative,
    export_bc3_from_budget_json,
    extract_reglamentos_excerpt,
    write_quality_pdf,
)

logger = logging.getLogger("dupla.nasas09")


def _nasas_root() -> Path:
    return (REPO_ROOT / "aps_integration" / "NASAS 09").resolve()


def _paths() -> dict[str, Path]:
    root = _nasas_root()
    arch = root / "NASAS arquitectura"
    return {
        "root": root,
        "planos_pdf_root": arch / "PLANOS RECIBIDOS",
        "pliego_dir": arch / "PLIEGO DE CONDICIONES",
        "revision_root": arch / "REVISION",
        "baseline_xlsx": root
        / "NASAS presupuesto"
        / "ACTUAL"
        / "Prelimary Budget NASAS 9-2, 17-02-2026.xlsx",
        "reglamentos": REPO_ROOT / "knowledge" / "reglamentos_mived",
        "outputs": root / "outputs" / "corridas",
    }


def _find_pliego_xlsx(p: dict[str, Path]) -> Path | None:
    d = p["pliego_dir"]
    if not d.is_dir():
        return None
    xs = sorted(d.rglob("*.xlsx"))
    xs = [x for x in xs if not x.name.startswith("~$")]
    return xs[0] if xs else None


def _build_merged_vision_pdf(
    tag: str,
    out_dir: Path,
    *,
    include_pliego: bool,
    include_revision: bool,
    paths: dict[str, Path],
) -> tuple[Path, dict[str, object]]:
    planos = collect_pdfs_recursive(paths["planos_pdf_root"])
    inputs_meta: dict[str, object] = {
        "planos_pdf_count": len(planos),
        "pliego_included": include_pliego,
        "revision_included": include_revision,
    }
    seq: list[Path] = list(planos)
    pliego_pdf: Path | None = None
    if include_pliego:
        xlsx = _find_pliego_xlsx(paths)
        if xlsx and xlsx.is_file():
            pliego_pdf = out_dir / "inputs" / "pliego_desde_xlsx.pdf"
            pliego_xlsx_to_text_pdf(xlsx, pliego_pdf)
            seq.append(pliego_pdf)
            inputs_meta["pliego_xlsx"] = str(xlsx)
        else:
            logger.warning("Pliego solicitado pero no hay .xlsx en PLIEGO DE CONDICIONES")
    if include_revision:
        rev = collect_pdfs_recursive(paths["revision_root"])
        seq.extend(rev)
        inputs_meta["revision_pdf_count"] = len(rev)
    merged = out_dir / "inputs" / f"vision_merge_{sanitize_filename(tag)}.pdf"
    if not seq:
        raise FileNotFoundError("No hay PDFs de planos para fusionar")
    merge_pdfs(seq, merged)
    inputs_meta["merged_pdf"] = str(merged)
    return merged, inputs_meta


def _run_cad_merge(out_dir: Path, *, dry_run: bool) -> Path:
    pattern = (
        "aps_integration/NASAS 09/NASAS arquitectura/PLANOS RECIBIDOS/**/*.dwg"
    )
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_multi_dwg_project_cad.py"),
        "--pattern",
        pattern,
        "--output-dir",
        str(out_dir),
        "--project-id",
        "nasas_09",
        "--project-name",
        "NASAS 09 — planos recibidos (merge DWG)",
        "--bc3",
        str(REPO_ROOT / "data" / "TGIU.bc3"),
    ]
    logger.info("CAD merge: %s", " ".join(cmd))
    if dry_run:
        return out_dir / "project_merged.normalized.json"
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    r = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env)
    if r.returncode != 0:
        raise RuntimeError("run_multi_dwg_project_cad falló")
    merged = out_dir / "project_merged.normalized.json"
    if not merged.is_file():
        raise FileNotFoundError(merged)
    return merged


def _run_vision(
    merged_json: Path,
    merged_pdf: Path,
    pipeline_dir: Path,
    excel_suffix: str,
    *,
    vision_profile: str,
    dry_run: bool,
) -> Path | None:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_merged_cad_pdf_vision.py"),
        "--pdf",
        str(merged_pdf),
        "--merged-json",
        str(merged_json),
        "--vision-output-dir",
        str(pipeline_dir),
        "--project-id",
        "nasas_09",
        "--project-name",
        "NASAS 09 — CAD + visión PDF",
        "--excel-suffix",
        excel_suffix,
        "--vision-profile",
        vision_profile,
    ]
    logger.info("Visión: %s", " ".join(cmd))
    if dry_run:
        return pipeline_dir / f"dupla_presupuesto_generado_cad_vision_{excel_suffix}.xlsx"
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    r = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env)
    if r.returncode != 0:
        raise RuntimeError("run_merged_cad_pdf_vision falló")
    # script imprime ruta xlsx en última línea; buscar por glob
    xs = list(pipeline_dir.glob(f"dupla_presupuesto_generado_cad_vision_{excel_suffix}*.xlsx"))
    return xs[0] if xs else None


def _postprocess_corrida(
    corrida_dir: Path,
    tag: str,
    generated_xlsx: Path | None,
    baseline: Path,
    paths: dict[str, Path],
    inputs_meta: dict[str, object],
    *,
    dry_run: bool,
) -> None:
    informes = corrida_dir / "informes"
    excel_d = corrida_dir / "excel"
    presto = corrida_dir / "presto"
    informes.mkdir(parents=True, exist_ok=True)
    excel_d.mkdir(parents=True, exist_ok=True)
    presto.mkdir(parents=True, exist_ok=True)

    pipeline_dir = corrida_dir / "pipeline"
    budget_json = pipeline_dir / "dupla_full_budget_output.json"
    if dry_run:
        logger.info("[dry-run] omitiendo comparación e informes")
        return
    if not generated_xlsx or not generated_xlsx.is_file():
        logger.error("No se encontró Excel generado en %s", pipeline_dir)
        return
    shutil.copy2(generated_xlsx, excel_d / generated_xlsx.name)

    if budget_json.is_file():
        bc3_out = presto / f"dupla_nasas09_{tag}.bc3"
        try:
            p = export_bc3_from_budget_json(budget_json, bc3_out)
            if p:
                logger.info("BC3: %s", p)
        except Exception:
            logger.exception("Export BC3")

    comp = analyze_budget_pair(
        generated_xlsx, baseline, real_format="nasas_preliminary"
    )
    comp_compact = {
        "coverage_pct": comp["coverage"],
        "qty_accuracy_pct": comp["qty_accuracy"],
        "price_accuracy_pct": comp["price_accuracy"],
        "real_total": comp["real_total"],
        "generated_total": comp["generated_total"],
        "matching_codes": len(comp["matching_codes"]),
        "real_codes": len(comp["real_by_code"]),
        "generated_partidas": len(comp["generated_partidas"]),
        "real_partidas": len(comp["real_partidas"]),
    }
    disc = analyze_budget_by_canonical_discipline(
        generated_xlsx, baseline, real_format="nasas_preliminary"
    )
    (informes / f"comparison_stats_{tag}.json").write_text(
        json.dumps({"pair_metrics": comp_compact, "discipline": disc}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (informes / f"discipline_breakdown_{tag}.json").write_text(
        json.dumps(disc, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    build_comparison_report(
        generated_xlsx,
        baseline,
        informes,
        real_format="nasas_preliminary",
    )
    md = build_comparison_markdown(
        generated_xlsx,
        baseline,
        title=f"NASAS 09 — {tag}",
        run_date=str(date.today()),
        run_tag=tag,
        notes=(
            "Referencia: Preliminary Budget (varias hojas). "
            "Los códigos NASAS (p. ej. 1.01) pueden no coincidir con códigos BC3 del generado; "
            "la cobertura por código puede ser baja aunque el desglose sea útil."
        ),
        real_format="nasas_preliminary",
    )
    (informes / f"comparacion_{tag}.md").write_text(md, encoding="utf-8")

    reg_ex = extract_reglamentos_excerpt(paths["reglamentos"])
    ai_payload = None
    try:
        ai_payload = call_openai_quality_narrative(
            corrida_name=tag,
            corrida_inputs=inputs_meta,
            comparison_stats={"pair": comp_compact, "discipline_headline": disc.get("headline")},
            discipline_json=disc,
            reglamentos_excerpt=reg_ex,
        )
        (informes / f"calidad_ia_{tag}.json").write_text(
            json.dumps(ai_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        logger.exception("Informe IA no generado (revisa OPENAI_API_KEY)")
    write_quality_pdf(
        informes / f"informe_final_{tag}.pdf",
        title=f"Informe final — NASAS 09 — {tag}",
        corrida_name=tag,
        comparison_md_path=informes / f"comparacion_{tag}.md",
        ai_payload=ai_payload,
        extra_sections=[
            ("Entradas de la corrida", json.dumps(inputs_meta, indent=2, ensure_ascii=False)),
        ],
    )


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")

    parser = argparse.ArgumentParser(description="Corridas NASAS 09 (PPR / PP / P)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--only",
        choices=("PPR", "PP", "P", "all"),
        default="all",
        help="Ejecutar una sola corrida o todas",
    )
    parser.add_argument(
        "--reuse-cad",
        type=str,
        default="",
        help="Carpeta con project_merged.normalized.json ya generado (salta APS en corridas siguientes)",
    )
    parser.add_argument(
        "--skip-vision",
        action="store_true",
        help="Solo preparar PDFs fusionados y metadatos (no ejecuta GPT ni APS)",
    )
    parser.add_argument(
        "--vision-profile",
        default="general",
        help="Perfil GPT visión (p. ej. structural si solo aplica estructura): ver run_merged_cad_pdf_vision.py",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    paths = _paths()
    if not paths["root"].is_dir():
        logger.error("No existe %s", paths["root"])
        return 1
    if not paths["baseline_xlsx"].is_file():
        logger.error("Falta presupuesto referencia: %s", paths["baseline_xlsx"])
        return 1

    paths["outputs"].mkdir(parents=True, exist_ok=True)
    cad_dir = (Path(args.reuse_cad).resolve() if args.reuse_cad else paths["outputs"] / "_cad_merge")

    corridas: list[tuple[str, str, bool, bool]] = [
        ("corrida_PPR", "PPR", True, True),
        ("corrida_PP", "PP", True, False),
        ("corrida_P", "P", False, False),
    ]
    if args.only != "all":
        m = {"PPR": ("corrida_PPR", "PPR", True, True), "PP": ("corrida_PP", "PP", True, False), "P": ("corrida_P", "P", False, False)}
        corridas = [m[args.only]]

    merged_json: Path
    if args.reuse_cad:
        merged_json = cad_dir / "project_merged.normalized.json"
        if not merged_json.is_file():
            logger.error("--reuse-cad requiere project_merged.normalized.json en %s", cad_dir)
            return 1
    elif not args.dry_run and not args.skip_vision:
        merged_json = _run_cad_merge(cad_dir, dry_run=False)
    else:
        merged_json = cad_dir / "project_merged.normalized.json"

    for folder, short, inc_pliego, inc_rev in corridas:
        cdir = paths["outputs"] / folder
        cdir.mkdir(parents=True, exist_ok=True)
        pipeline_dir = cdir / "pipeline"
        inputs_dir = cdir / "inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        try:
            merged_pdf, inputs_meta = _build_merged_vision_pdf(
                short,
                cdir,
                include_pliego=inc_pliego,
                include_revision=inc_rev,
                paths=paths,
            )
        except Exception as exc:
            logger.exception("Fusión PDF %s: %s", short, exc)
            continue
        meta_path = inputs_dir / f"inputs_{short}.json"
        meta_path.write_text(json.dumps(inputs_meta, indent=2, ensure_ascii=False), encoding="utf-8")

        if args.skip_vision:
            logger.info("Saltando visión (--skip-vision). PDF fusionado: %s", merged_pdf)
            continue

        suffix = sanitize_filename(f"nasas09_{short.lower()}")
        gen = _run_vision(
            merged_json,
            merged_pdf,
            pipeline_dir,
            suffix,
            vision_profile=args.vision_profile,
            dry_run=args.dry_run,
        )
        _postprocess_corrida(
            cdir,
            short,
            gen,
            paths["baseline_xlsx"],
            paths,
            inputs_meta,
            dry_run=args.dry_run,
        )

    logger.info("Listo. Salidas en %s", paths["outputs"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
