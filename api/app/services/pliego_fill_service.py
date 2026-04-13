from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.services.job_store import JobRecord, JobStore

PLIEGO_TEMPLATE_RELATIVE = "data/pliego.xlsx"

# Hoja RESUMEN — etiquetas en columna A/D según plantilla GA-FO-01; valores típicos a la derecha del rótulo.
RESUMEN_CELLS: dict[str, str] = {
    "proyecto": "C2",
    "ubicacion_del_proyecto": "F2",
    "m2_construccion": "C3",
    "m2_de_solar": "F3",
    "arquitecto_encargado": "C4",
    "gerente_del_proyecto": "F4",
    "tipo_de_proyecto": "C5",
    "propietario": "F5",
    "fecha_inicio_proyecto": "C6",
    "fecha_finalizacion_proyecto": "F6",
    "fecha_inicio_recepcion_documentacion": "C7",
    "fecha_actualizacion": "F7",
}


class PliegoFillError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _load_normalized_payload(store: JobStore, job_id: str, record: JobRecord) -> dict[str, Any]:
    if record.status != "succeeded" or not record.outputs:
        raise PliegoFillError(
            "job_not_ready",
            "Job must have status succeeded with outputs before pliego fill hints.",
        )
    norm_name = record.outputs.get("normalized_json")
    if not norm_name:
        raise PliegoFillError("no_normalized_json", "Job outputs missing normalized_json.")
    norm_path = store.outputs_dir(job_id) / norm_name
    if not norm_path.is_file():
        raise PliegoFillError("normalized_missing", f"Normalized JSON not found at {norm_path}")
    try:
        return json.loads(norm_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PliegoFillError("invalid_normalized_json", f"Invalid JSON: {exc}") from exc


def _inner_cad_facts(payload: dict[str, Any]) -> dict[str, Any]:
    inner = payload.get("cad_facts")
    return inner if isinstance(inner, dict) else {}


def _sum_hatch_areas_m2(inner: dict[str, Any]) -> float | None:
    hatches = inner.get("hatches")
    if not isinstance(hatches, list):
        return None
    total = 0.0
    count = 0
    for h in hatches:
        if not isinstance(h, dict):
            continue
        a = h.get("area")
        if isinstance(a, (int, float)) and float(a) > 0:
            total += float(a)
            count += 1
    if count == 0:
        return None
    return round(total, 2)


def _text_samples_for_location(texts: list[Any], *, limit: int = 8) -> list[str]:
    out: list[str] = []
    for t in texts:
        if not isinstance(t, dict):
            continue
        content = str(t.get("content") or "").strip()
        if len(content) < 4:
            continue
        if _looks_like_address_or_title(content):
            out.append(content[:500])
        if len(out) >= limit:
            break
    if not out and texts:
        for t in texts[:limit]:
            if isinstance(t, dict) and t.get("content"):
                out.append(str(t["content"]).strip()[:500])
                break
    return out


_ADDR_HINT = re.compile(
    r"(calle|ave\.?|avenida|urb\.?|urbanizaci|carretera|km\.?\s*\d|p\.?\s*r\.?\s*|puerto\srico)",
    re.IGNORECASE,
)


def _looks_like_address_or_title(s: str) -> bool:
    if len(s) > 120:
        return False
    return bool(_ADDR_HINT.search(s)) or (len(s.split()) <= 12 and len(s) > 5)


def _level_labels(payload: dict[str, Any]) -> list[str]:
    hints = payload.get("inventory_hints")
    if not isinstance(hints, dict):
        return []
    markers = hints.get("level_markers")
    if not isinstance(markers, list):
        return []
    labels: list[str] = []
    for m in markers[:20]:
        if isinstance(m, dict) and m.get("content"):
            labels.append(str(m["content"]).strip())
    return labels


def build_pliego_fill_payload(job_id: str, job_data_dir: Path) -> dict[str, Any]:
    store = JobStore(job_data_dir)
    record = store.get(job_id)
    if record is None:
        raise PliegoFillError("not_found", "Job not found")

    normalized = _load_normalized_payload(store, job_id, record)
    inner = _inner_cad_facts(normalized)
    hints = normalized.get("inventory_hints") if isinstance(normalized.get("inventory_hints"), dict) else {}

    dwg_name = record.dwg_filename or ""
    stem = Path(dwg_name).stem if dwg_name else ""
    project_label = normalized.get("project")
    if isinstance(project_label, str) and project_label.endswith(".normalized.json"):
        project_label = stem or project_label
    proyecto_sugerido = stem or project_label or job_id

    hatch_sum_m2 = _sum_hatch_areas_m2(inner)
    texts = inner.get("texts") if isinstance(inner.get("texts"), list) else []
    ubicacion_hints = _text_samples_for_location(texts)
    niveles = _level_labels(normalized)

    layers = inner.get("layers")
    layer_names = sorted(layers.keys()) if isinstance(layers, dict) else []

    disclaimers = [
        "Los campos administrativos (fechas, responsables, permisos, instituciones) no se infieren del DWG; complételos en la plantilla.",
        "m² de construcción / solar son aproximaciones heurísticas desde geometría del CAD (p. ej. suma de áreas de sombreado); validar en obra.",
    ]

    resumen: dict[str, Any] = {}
    for key, cell in RESUMEN_CELLS.items():
        resumen[key] = {
            "excel_cell": f"RESUMEN!{cell}",
            "suggested_value": None,
            "source": "manual",
            "notes": None,
        }

    resumen["proyecto"]["suggested_value"] = proyecto_sugerido
    resumen["proyecto"]["source"] = "dwg_filename_or_normalized_project"

    if ubicacion_hints:
        resumen["ubicacion_del_proyecto"]["suggested_value"] = ubicacion_hints[0]
        resumen["ubicacion_del_proyecto"]["source"] = "cad_text_heuristic"
        resumen["ubicacion_del_proyecto"]["notes"] = "Revisar: texto tomado del plano si parece ubicación o título."
    else:
        resumen["ubicacion_del_proyecto"]["notes"] = "Sin texto candidato; rellenar a mano."

    if hatch_sum_m2 is not None:
        resumen["m2_construccion"]["suggested_value"] = hatch_sum_m2
        resumen["m2_construccion"]["source"] = "sum_hatch_area_m2"
        resumen["m2_construccion"]["notes"] = "Suma de propiedades Area en entidades Hatch del DWG (Model Derivative)."
    else:
        resumen["m2_construccion"]["notes"] = "Sin áreas de hatch numéricas; medir o cuantificar en presupuesto."

    resumen["m2_de_solar"]["notes"] = "No inferido del DWG por defecto; definir límite de solar en planta/catastro."

    derived = {
        "dwg_filename": dwg_name,
        "total_objects": normalized.get("total_objects"),
        "layer_count": len(layer_names),
        "layer_names_sample": layer_names[:40],
        "hatch_entity_count": len(inner.get("hatches") or []) if isinstance(inner.get("hatches"), list) else 0,
        "text_entity_count": len(texts),
        "dimension_count": len(inner.get("dimensions") or []) if isinstance(inner.get("dimensions"), list) else 0,
        "level_markers": niveles,
        "text_snippets_for_review": [t[:300] for t in ubicacion_hints[:5]],
        "block_frequency_top": hints.get("block_frequency")[:15] if isinstance(hints.get("block_frequency"), list) else [],
    }

    return {
        "job_id": job_id,
        "template_reference": PLIEGO_TEMPLATE_RELATIVE,
        "template_sheet_resumen": "RESUMEN",
        "resumen_fields": resumen,
        "derived_from_dwg": derived,
        "disclaimers": disclaimers,
    }
