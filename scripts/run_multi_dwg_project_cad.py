"""
Varios DWG del mismo proyecto: APS por archivo, merge de JSON normalizado,
un solo presupuesto CAD-only (sin PDF ni GPT visión).

Uso:
    python scripts/run_multi_dwg_project_cad.py
    python scripts/run_multi_dwg_project_cad.py --pattern "BLCAD09/BLCAD*.dwg" --project-name "Proyecto 09"
    python scripts/run_multi_dwg_project_cad.py --pattern "BLCAD14/BLCAD*.dwg" --project-name "Proyecto 14"
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aps_integration.oss_manager import APS_BUCKET_NAME
from budget.export_excel import export_budget_workbook
from core.logging_config import setup_logging
from core.pipeline import build_budget_from_sources
from core.schemas import ProjectContext
from dupla_run_full_analysis_local import (
    AUTO_UNIQUE_OBJECT_NAME,
    BUCKET_NAME,
    stage_aps_extraction,
)
from knowledge.bc3_embeddings import load_or_build_embeddings
from knowledge.training_data import extract_training_pairs
from processors.bc3_parser import parse_bc3

logger = logging.getLogger("dupla.multi_dwg_cad")

_BLCAD_14001_15 = re.compile(r"^BLCAD140(0[1-9]|1[0-5])\.dwg$", re.IGNORECASE)
# BLCAD09001 … BLCAD09016 (prefijo "BLCAD090", no "BLCAD09" + 2 dígitos)
_BLCAD_09001_16 = re.compile(r"^BLCAD090(0[1-9]|1[0-6])\.dwg$", re.IGNORECASE)


def merge_process_autodesk_outputs(
    labeled: list[tuple[str, dict]],
) -> dict:
    """
    Fusiona salidas de process_autodesk_json (misma forma que *.normalized.json).

    Prefija capas con el nombre del DWG para evitar colisiones entre planos.
    """
    if not labeled:
        raise ValueError("No hay planos para fusionar.")

    merged_cf: dict = {
        "layers": {},
        "texts": [],
        "dimensions": [],
        "hatches": [],
        "blocks": [],
        "geometry_hints": [],
    }
    level_markers: list = []
    scale_dimensions: list = []
    block_names: Counter[str] = Counter()
    layer_names: set[str] = set()
    total_objects = 0
    sources: list[str] = []

    for stem, payload in labeled:
        sources.append(stem)
        total_objects += int(payload.get("total_objects") or 0)
        cf = payload.get("cad_facts") or {}
        layers = cf.get("layers") or {}
        for layer_name, summary in layers.items():
            key = f"{stem}|{layer_name}"
            merged_cf["layers"][key] = summary
            layer_names.add(key)

        merged_cf["texts"].extend(cf.get("texts") or [])
        merged_cf["dimensions"].extend(cf.get("dimensions") or [])
        merged_cf["hatches"].extend(cf.get("hatches") or [])
        merged_cf["blocks"].extend(cf.get("blocks") or [])
        merged_cf["geometry_hints"].extend(cf.get("geometry_hints") or [])

        hints = payload.get("inventory_hints") or {}
        level_markers.extend(hints.get("level_markers") or [])
        scale_dimensions.extend(hints.get("scale_dimensions") or [])
        for row in hints.get("block_frequency") or []:
            if isinstance(row, dict) and row.get("block_name"):
                block_names[row["block_name"]] += int(row.get("count") or 0)

    block_frequency = [{"block_name": n, "count": c} for n, c in block_names.most_common(40)]

    return {
        "project": "merged:" + "+".join(sources),
        "total_objects": total_objects,
        "cad_facts": merged_cf,
        "inventory_hints": {
            "level_markers": level_markers[:50],
            "scale_dimensions": scale_dimensions[:50],
            "block_frequency": block_frequency,
            "layer_names": sorted(layer_names),
        },
        "_merge_sources": sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-DWG → presupuesto CAD-only fusionado")
    parser.add_argument(
        "--pattern",
        default="BLCAD14/BLCAD*.dwg",
        help="Glob relativo al repo (por defecto planos en BLCAD14/)",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Carpeta de salida exacta (recomendado). Si se omite: output/prueba_web_01/<fecha_hora>/",
    )
    cad_subset = parser.add_mutually_exclusive_group()
    cad_subset.add_argument(
        "--blcad-01-15-only",
        action="store_true",
        help="Incluir solo BLCAD14001.dwg … BLCAD14015.dwg (tras el glob --pattern).",
    )
    cad_subset.add_argument(
        "--blcad-09001-16-only",
        action="store_true",
        help="Incluir solo BLCAD09001…09016 (prefijo BLCAD090; tras el glob --pattern).",
    )
    parser.add_argument(
        "--project-id",
        default="prueba_web_01",
        help="ID estable del proyecto",
    )
    parser.add_argument(
        "--project-name",
        default="Prueba web 01 — batch BLCAD + APS",
        help="Nombre legible del proyecto",
    )
    parser.add_argument(
        "--bc3",
        type=str,
        default=str(REPO_ROOT / "data" / "TGIU.bc3"),
        help="Ruta al BC3",
    )
    parser.add_argument(
        "--pres",
        type=str,
        default="",
        help="Opcional: PRES.xlsx de otro proyecto para few-shot BC3. Por defecto no se usa ningún PRES.",
    )
    args = parser.parse_args()

    dwg_paths = sorted(REPO_ROOT.glob(args.pattern))
    dwg_paths = [p for p in dwg_paths if p.is_file()]
    if args.blcad_01_15_only:
        dwg_paths = [p for p in dwg_paths if _BLCAD_14001_15.match(p.name)]
    elif args.blcad_09001_16_only:
        dwg_paths = [p for p in dwg_paths if _BLCAD_09001_16.match(p.name)]
    if not dwg_paths:
        print(f"No se encontraron DWG con el patrón {args.pattern!r} en {REPO_ROOT}", file=sys.stderr)
        return 1

    if args.output_dir:
        out_dir = Path(args.output_dir).resolve()
    else:
        run_folder = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        out_dir = (REPO_ROOT / "output" / "prueba_web_01" / run_folder).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    setup_logging(console_level=logging.INFO, log_file=out_dir / "run.log")
    logger.info("Planos: %d — %s", len(dwg_paths), ", ".join(p.name for p in dwg_paths))
    logger.info("Salida: %s", out_dir)

    bc3_path = Path(args.bc3).resolve()
    if not bc3_path.is_file():
        logger.error("BC3 no encontrado: %s", bc3_path)
        return 1

    training_pairs: list = []
    if args.pres:
        pres_path = Path(args.pres).resolve()
        if pres_path.is_file():
            try:
                training_pairs = extract_training_pairs(str(pres_path))
                logger.info("Pares desde PRES (--pres): %d (%s)", len(training_pairs), pres_path.name)
            except Exception:
                logger.warning("No se pudieron leer pares desde PRES", exc_info=True)
        else:
            logger.error("No existe el archivo --pres: %s", pres_path)
            return 1
    else:
        logger.info("Sin PRES: matching BC3 sin pares de entrenamiento desde Excel.")

    bc3_catalog = parse_bc3(str(bc3_path))

    embedding_index = None
    if bc3_catalog.get("items"):
        try:
            embedding_index = load_or_build_embeddings(bc3_catalog)
            logger.info("Embeddings BC3: %d items", len(embedding_index.metadata))
        except Exception:
            logger.warning("Embeddings no disponibles (se sigue sin ellos)", exc_info=True)

    bucket_name = BUCKET_NAME or APS_BUCKET_NAME
    labeled: list[tuple[str, dict]] = []

    for dwg_path in dwg_paths:
        logger.info("=== APS: %s ===", dwg_path.name)
        aps = stage_aps_extraction(dwg_path, out_dir, bucket_name)
        norm_path = Path(aps["normalized_json_path"])
        payload = json.loads(norm_path.read_text(encoding="utf-8"))
        labeled.append((dwg_path.stem, payload))

    merged = merge_process_autodesk_outputs(labeled)
    merged_path = out_dir / "project_merged.normalized.json"
    merged_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Fusionado guardado: %s (objetos totales declarados: %s)", merged_path, merged["total_objects"])

    raw_paths = [str(out_dir / f"{s}.autodesk_raw.json") for s, _ in labeled]

    context = ProjectContext(
        project_id=args.project_id,
        project_name=args.project_name,
        source_json_path=str(merged_path),
        plan_image_paths=[],
        bc3_path=str(bc3_path),
        metadata={
            "dwg_paths": [str(p.resolve()) for p in dwg_paths],
            "merged_normalized_json": str(merged_path),
            "autodesk_raw_json_paths": raw_paths,
            "merge_sources": merged.get("_merge_sources", []),
            "vision_pages_dir": "",
            "uploaded_object_name": "multi_dwg_merge",
            "auto_unique_object_name": AUTO_UNIQUE_OBJECT_NAME,
            "xlsx_path": str(Path(args.pres).resolve()) if args.pres else "",
            "pres_template_takeoffs": False,
            "pipeline_mode": "multi_dwg_cad_only",
        },
    )

    # build_budget_from_sources espera el mismo dict que process_autodesk_json (sin _merge_sources en uso downstream)
    cad_for_pipeline = {k: v for k, v in merged.items() if not str(k).startswith("_")}

    logger.info("Presupuesto CAD fusionado…")
    budget = build_budget_from_sources(
        context=context,
        cad_facts=cad_for_pipeline,
        vision_payloads=[],
        bc3_catalog=bc3_catalog,
        embedding_index=embedding_index,
        training_pairs=training_pairs,
    )

    out_json = out_dir / "dupla_full_budget_output.json"
    out_json.write_text(json.dumps(budget, indent=2, ensure_ascii=False), encoding="utf-8")

    xlsx_path = out_dir / "dupla_presupuesto_proyecto_merged.xlsx"
    export_budget_workbook(context, budget["rows"], xlsx_path)
    logger.info("Excel: %s", xlsx_path)

    manifest = out_dir / "README_CORRIDA.txt"
    manifest.write_text(
        "\n".join(
            [
                f"fecha={datetime.now().strftime('%Y-%m-%d')}",
                f"project_id={args.project_id}",
                f"planos={len(dwg_paths)}",
                *[f"  - {p}" for p in dwg_paths],
                f"merged_json={merged_path}",
                f"budget_json={out_json}",
                f"budget_xlsx={xlsx_path}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(xlsx_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
