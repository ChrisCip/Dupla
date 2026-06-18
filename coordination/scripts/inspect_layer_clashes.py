#!/usr/bin/env python3
"""Inspect full layer overlap between two DWG files."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from coordination.core.models_25d import Discipline, Element25D
from coordination.extraction.from_dwg_accore import (
    ANNOTATION_TYPES,
    extract_elements_from_accore_payload,
    load_accore_payload_via_accore,
)
from coordination.extraction.from_dwg_com import NON_GEOMETRIC_LAYER_TOKENS

logger = logging.getLogger("dupla.inspect_layer_clashes")

PRODUCTION_MIN_DWG_AREA_MM2 = 40_000.0
PRODUCTION_MAX_DWG_ENTITIES = 350
MAX_RELAXED_ENTITIES = 999_999
DISCIPLINE_PAIR_LABEL = "Discipline.ARCH / Discipline.STRUC"


@dataclass
class LayerSummary:
    file_name: str
    discipline: Discipline
    layer: str
    entity_count: int
    dominant_type: str
    approx_bbox_area_mm2: float
    filtered_by_annotation: bool
    filtered_by_token: bool
    would_survive_min_area: bool


@dataclass
class LayerGeometry:
    layer: str
    union_geom: Any
    entity_count: int


def _cache_root_for_accore(cache_root: Path) -> Path:
    if cache_root.name.lower() == "accore":
        return cache_root
    return cache_root / "accore"


def _parse_discipline(value: str) -> Discipline:
    normalized = value.strip().upper()
    aliases = {
        "ARCH": Discipline.ARCH,
        "ARQ": Discipline.ARCH,
        "ARQUITECTURA": Discipline.ARCH,
        "STRUC": Discipline.STRUC,
        "EST": Discipline.STRUC,
        "ESTRUCTURA": Discipline.STRUC,
    }
    if normalized in aliases:
        return aliases[normalized]
    raise argparse.ArgumentTypeError(f"Disciplina no soportada: {value}")


def _safe_layer(value: Any) -> str:
    layer = str(value or "0").strip()
    return layer or "0"


def _bounds_area_mm2(entity: dict[str, Any], factor_mm: float) -> float:
    bounds = entity.get("Bounds")
    if not isinstance(bounds, dict):
        return 0.0
    min_pt = bounds.get("Min") or {}
    max_pt = bounds.get("Max") or {}
    try:
        min_x = float(min_pt.get("X") or 0.0) * factor_mm
        min_y = float(min_pt.get("Y") or 0.0) * factor_mm
        max_x = float(max_pt.get("X") or 0.0) * factor_mm
        max_y = float(max_pt.get("Y") or 0.0) * factor_mm
    except Exception:
        return 0.0
    if max_x <= min_x or max_y <= min_y:
        return 0.0
    return (max_x - min_x) * (max_y - min_y)


def _build_census(
    *,
    payload: dict[str, Any],
    file_name: str,
    discipline: Discipline,
) -> list[LayerSummary]:
    factor_mm = float(payload.get("UnitsToMmFactor") or 1.0)
    rows: dict[str, dict[str, Any]] = {}
    for entity in payload.get("Entities") or []:
        if not isinstance(entity, dict):
            continue
        layer = _safe_layer(entity.get("Layer"))
        entity_type = str(entity.get("Type") or "")
        is_annotation = entity_type in ANNOTATION_TYPES
        has_token = any(token in layer.lower() for token in NON_GEOMETRIC_LAYER_TOKENS)
        bbox_area = _bounds_area_mm2(entity, factor_mm)

        slot = rows.setdefault(
            layer,
            {
                "entity_count": 0,
                "type_counts": Counter(),
                "approx_bbox_area_mm2": 0.0,
                "annotation_count": 0,
                "token_count": 0,
                "survives_count": 0,
            },
        )
        slot["entity_count"] += 1
        slot["type_counts"][entity_type] += 1
        slot["approx_bbox_area_mm2"] += bbox_area
        if is_annotation:
            slot["annotation_count"] += 1
        if has_token:
            slot["token_count"] += 1
        if (not is_annotation) and (not has_token) and bbox_area >= PRODUCTION_MIN_DWG_AREA_MM2:
            slot["survives_count"] += 1

    summaries: list[LayerSummary] = []
    for layer, stats in sorted(rows.items(), key=lambda item: item[0].lower()):
        dominant_type = ""
        if stats["type_counts"]:
            dominant_type = sorted(stats["type_counts"].items(), key=lambda item: (-item[1], item[0]))[0][0]
        summaries.append(
            LayerSummary(
                file_name=file_name,
                discipline=discipline,
                layer=layer,
                entity_count=int(stats["entity_count"]),
                dominant_type=dominant_type,
                approx_bbox_area_mm2=float(stats["approx_bbox_area_mm2"]),
                filtered_by_annotation=bool(stats["annotation_count"] >= stats["entity_count"]),
                filtered_by_token=bool(stats["token_count"] >= stats["entity_count"]),
                would_survive_min_area=bool(stats["survives_count"] > 0),
            )
        )
    return summaries


def _extract_layer_geometries(elements: list[Element25D]) -> dict[str, LayerGeometry]:
    by_layer: dict[str, list[Any]] = defaultdict(list)
    for element in elements:
        layer = _safe_layer(element.metadata.get("layer"))
        coords = element.footprint_coords_mm
        if len(coords) < 3:
            continue
        polygon = Polygon(coords + [coords[0]])
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if polygon.is_empty or polygon.area <= 0.0:
            continue
        by_layer[layer].append(polygon)

    output: dict[str, LayerGeometry] = {}
    for layer, polygons in by_layer.items():
        if not polygons:
            continue
        merged = unary_union(polygons)
        if merged.is_empty:
            continue
        output[layer] = LayerGeometry(layer=layer, union_geom=merged, entity_count=len(polygons))
    return output


def _compute_overlap_pairs(
    left: dict[str, LayerGeometry],
    right: dict[str, LayerGeometry],
) -> list[dict[str, Any]]:
    right_items = list(right.values())
    if not left or not right_items:
        return []
    right_geoms = [item.union_geom for item in right_items]
    tree = STRtree(right_geoms)

    rows: list[dict[str, Any]] = []
    for left_item in left.values():
        left_geom = left_item.union_geom
        for candidate_index in tree.query(left_geom).tolist():
            right_item = right_items[int(candidate_index)]
            candidate = right_geoms[int(candidate_index)]
            inter = left_geom.intersection(candidate)
            if inter.is_empty:
                continue
            area_mm2 = float(inter.area)
            if area_mm2 <= 0.0:
                continue
            centroid = inter.centroid
            bounds = inter.bounds
            rows.append(
                {
                    "layer_arq": left_item.layer,
                    "layer_est": right_item.layer,
                    "clash_area_m2": area_mm2 / 1_000_000.0,
                    "centroid_x_mm": float(centroid.x),
                    "centroid_y_mm": float(centroid.y),
                    "clash_min_x_mm": float(bounds[0]),
                    "clash_min_y_mm": float(bounds[1]),
                    "clash_max_x_mm": float(bounds[2]),
                    "clash_max_y_mm": float(bounds[3]),
                    "n_entities_arq": left_item.entity_count,
                    "n_entities_est": right_item.entity_count,
                }
            )
    rows.sort(key=lambda item: (-item["clash_area_m2"], item["layer_arq"], item["layer_est"]))
    return rows


def _load_payload(path: Path, cache_root: Path, timeout_seconds: int) -> dict[str, Any]:
    payload_result = load_accore_payload_via_accore(
        path,
        cache_root=cache_root,
        accoreconsole_path=None,
        extractor_dll=None,
        timeout_seconds=timeout_seconds,
    )
    if not payload_result.payload:
        raise RuntimeError(f"No se pudo extraer payload accore para {path}")
    return payload_result.payload


def _extract_elements(
    *,
    payload: dict[str, Any],
    path: Path,
    discipline: Discipline,
    min_area_mm2: float,
    max_entities: int,
) -> list[Element25D]:
    return extract_elements_from_accore_payload(
        payload,
        path=path,
        discipline=discipline,
        level_id="unknown",
        translation_mm=(0.0, 0.0),
        min_area_mm2=min_area_mm2,
        max_entities=max_entities,
        z_thickness_mm=250.0,
        z_ref_mm=None,
    )


def _write_census_csv(path: Path, rows: list[LayerSummary]) -> None:
    fields = [
        "file",
        "discipline",
        "layer",
        "entity_count",
        "dominant_type",
        "approx_bbox_area_mm2",
        "filtered_by_annotation",
        "filtered_by_token",
        "would_survive_min_area",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "file": row.file_name,
                    "discipline": row.discipline.value,
                    "layer": row.layer,
                    "entity_count": row.entity_count,
                    "dominant_type": row.dominant_type,
                    "approx_bbox_area_mm2": round(row.approx_bbox_area_mm2, 3),
                    "filtered_by_annotation": str(row.filtered_by_annotation).lower(),
                    "filtered_by_token": str(row.filtered_by_token).lower(),
                    "would_survive_min_area": str(row.would_survive_min_area).lower(),
                }
            )


def _write_clashes_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        fields = [
            "layer_arq",
            "layer_est",
            "clash_area_m2",
            "centroid_x_mm",
            "centroid_y_mm",
            "clash_min_x_mm",
            "clash_min_y_mm",
            "clash_max_x_mm",
            "clash_max_y_mm",
            "n_entities_arq",
            "n_entities_est",
            "lost_in_production",
        ]
    else:
        fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_clashes_md(
    path: Path,
    *,
    arq_file: Path,
    est_file: Path,
    overlaps: list[dict[str, Any]],
) -> None:
    lost = [item for item in overlaps if bool(item.get("lost_in_production"))]
    lines = [
        "# Layer Clash Inspection",
        "",
        f"- ARQ: `{arq_file}`",
        f"- EST: `{est_file}`",
        f"- pares con solape: `{len(overlaps)}`",
        f"- detectado pero perdido en produccion: `{len(lost)}`",
        "",
        "## Top 50 por area",
        "",
        "| layer_arq | layer_est | area_m2 | centroid_x_mm | centroid_y_mm | lost_in_production |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in overlaps[:50]:
        lines.append(
            f"| {row['layer_arq']} | {row['layer_est']} | {row['clash_area_m2']:.6f} | "
            f"{row['centroid_x_mm']:.1f} | {row['centroid_y_mm']:.1f} | {row['lost_in_production']} |"
        )
    lines.append("")
    lines.append("## Detectado pero perdido en produccion")
    lines.append("")
    for row in lost[:100]:
        lines.append(
            f"- `{row['layer_arq']} / {row['layer_est']}` area={row['clash_area_m2']:.6f} m2 "
            f"centro=({row['centroid_x_mm']:.1f}, {row['centroid_y_mm']:.1f}) mm"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_feedback_candidates(
    *,
    overlaps: list[dict[str, Any]],
    run_label: str,
    project_name: str,
    project_type: str,
    level_id: str,
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    candidates: list[dict[str, Any]] = []
    for idx, row in enumerate(overlaps, start=1):
        candidates.append(
            {
                "run_label": run_label,
                "incident_id": f"layer_pair_{idx:04d}",
                "project_name": project_name,
                "discipline_pair": DISCIPLINE_PAIR_LABEL,
                "level_id": level_id,
                "layer_pair": f"{row['layer_arq']} / {row['layer_est']}",
                "geometry_metrics": {
                    "area_m2": float(row["clash_area_m2"]),
                    "member_count": int(row["n_entities_arq"]) + int(row["n_entities_est"]),
                    "overlap_depth_mm": 0.0,
                },
                "human_label": None,
                "human_reason": None,
                "reviewer": None,
                "timestamp": now,
                "project_type": project_type,
                "notes": (
                    "generated by inspect_layer_clashes; "
                    f"lost_in_production={bool(row.get('lost_in_production'))}; "
                    f"centroid_mm=({row['centroid_x_mm']:.1f},{row['centroid_y_mm']:.1f})"
                ),
            }
        )
    return candidates


def _write_feedback_candidates(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _ingest_feedback_candidates(
    *,
    rows: list[dict[str, Any]],
    feedback_log: Path,
    allow_unlabeled: bool,
) -> int:
    labeled = [row for row in rows if row.get("human_label")]
    selected = labeled
    if not selected and allow_unlabeled:
        selected = rows
    if not selected and sys.stdin.isatty():
        answer = input("No hay candidatos con human_label. Ingerir sin etiqueta? [y/N]: ").strip().lower()
        if answer in {"y", "yes", "s", "si"}:
            selected = rows
    if not selected:
        logger.warning("Ingest omitido: no hay candidatos etiquetados para anexar.")
        return 0

    feedback_log.parent.mkdir(parents=True, exist_ok=True)
    with feedback_log.open("a", encoding="utf-8") as handle:
        for row in selected:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(selected)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect all layer overlaps between two DWG files.")
    parser.add_argument("--arq", type=Path, required=True, help="DWG arquitectura")
    parser.add_argument("--est", type=Path, required=True, help="DWG estructura")
    parser.add_argument("--arq-discipline", type=_parse_discipline, default=Discipline.ARCH)
    parser.add_argument("--est-discipline", type=_parse_discipline, default=Discipline.STRUC)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, default=REPO_ROOT / "analysis_output" / "accore_cache")
    parser.add_argument("--run-label", type=str, required=True)
    parser.add_argument("--project-name", type=str, default="UNKNOWN")
    parser.add_argument("--project-type", type=str, default="generic")
    parser.add_argument("--level-id", type=str, default="unknown")
    parser.add_argument("--accore-timeout-seconds", type=int, default=240)
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--allow-unlabeled-ingest", action="store_true")
    parser.add_argument(
        "--feedback-log",
        type=Path,
        default=REPO_ROOT / "knowledge" / "clash_memory" / "feedback_log.jsonl",
    )
    return parser.parse_args()


def main() -> int:
    args = _args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    arq_path = args.arq.resolve()
    est_path = args.est.resolve()
    if not arq_path.is_file():
        logger.error("No existe ARQ: %s", arq_path)
        return 1
    if not est_path.is_file():
        logger.error("No existe EST: %s", est_path)
        return 1

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    accore_cache_root = _cache_root_for_accore(args.cache_root.resolve())

    logger.info("Cargando payload ARQ...")
    arq_payload = _load_payload(arq_path, accore_cache_root, args.accore_timeout_seconds)
    logger.info("Cargando payload EST...")
    est_payload = _load_payload(est_path, accore_cache_root, args.accore_timeout_seconds)

    logger.info("Fase 1/3: census de layers")
    census_rows = _build_census(payload=arq_payload, file_name=arq_path.name, discipline=args.arq_discipline)
    census_rows.extend(_build_census(payload=est_payload, file_name=est_path.name, discipline=args.est_discipline))

    logger.info("Fase 2/3: deteccion de solapes layer-vs-layer")
    relaxed_arq = _extract_elements(
        payload=arq_payload,
        path=arq_path,
        discipline=args.arq_discipline,
        min_area_mm2=0.0,
        max_entities=MAX_RELAXED_ENTITIES,
    )
    relaxed_est = _extract_elements(
        payload=est_payload,
        path=est_path,
        discipline=args.est_discipline,
        min_area_mm2=0.0,
        max_entities=MAX_RELAXED_ENTITIES,
    )
    prod_arq = _extract_elements(
        payload=arq_payload,
        path=arq_path,
        discipline=args.arq_discipline,
        min_area_mm2=PRODUCTION_MIN_DWG_AREA_MM2,
        max_entities=PRODUCTION_MAX_DWG_ENTITIES,
    )
    prod_est = _extract_elements(
        payload=est_payload,
        path=est_path,
        discipline=args.est_discipline,
        min_area_mm2=PRODUCTION_MIN_DWG_AREA_MM2,
        max_entities=PRODUCTION_MAX_DWG_ENTITIES,
    )

    relaxed_overlaps = _compute_overlap_pairs(_extract_layer_geometries(relaxed_arq), _extract_layer_geometries(relaxed_est))
    prod_overlaps = _compute_overlap_pairs(_extract_layer_geometries(prod_arq), _extract_layer_geometries(prod_est))
    prod_pair_keys = {(row["layer_arq"], row["layer_est"]) for row in prod_overlaps}
    for row in relaxed_overlaps:
        row["lost_in_production"] = (row["layer_arq"], row["layer_est"]) not in prod_pair_keys

    logger.info("Fase 3/3: escritura de outputs")
    layer_census_csv = output_dir / "layer_census.csv"
    layer_clashes_csv = output_dir / "layer_clashes.csv"
    layer_clashes_md = output_dir / "layer_clashes.md"
    feedback_candidates_jsonl = output_dir / "feedback_candidates.jsonl"

    _write_census_csv(layer_census_csv, census_rows)
    _write_clashes_csv(layer_clashes_csv, relaxed_overlaps)
    _write_clashes_md(layer_clashes_md, arq_file=arq_path, est_file=est_path, overlaps=relaxed_overlaps)
    feedback_candidates = _build_feedback_candidates(
        overlaps=relaxed_overlaps,
        run_label=args.run_label,
        project_name=args.project_name,
        project_type=args.project_type,
        level_id=args.level_id,
    )
    _write_feedback_candidates(feedback_candidates_jsonl, feedback_candidates)

    if args.ingest:
        ingested = _ingest_feedback_candidates(
            rows=feedback_candidates,
            feedback_log=args.feedback_log.resolve(),
            allow_unlabeled=args.allow_unlabeled_ingest,
        )
        logger.info("Feedback ingestado: %d filas", ingested)

    logger.info("Listo. Outputs en %s", output_dir)
    logger.info("Rows: census=%d overlaps=%d", len(census_rows), len(relaxed_overlaps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
