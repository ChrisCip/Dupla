"""Architectural Spanish copy for human clash coordination reports."""

from __future__ import annotations

import re
from typing import Any

_NA = "no disponible"

_DEBUG_MARKERS = (
    "source_ref",
    "bbox",
    "normalized",
    "unavailable",
    "missing",
    "fallback_manual",
    "provenance",
    "coordination_context",
    "representative_conflict",
    "incident.",
    "no generado",
    "tras revisar todas las fuentes",
)

CORRECTION_STATUS_ES: dict[str, str] = {
    "detected": "Detectado",
    "reviewed": "Revisado",
    "under_review": "Revisado",
    "correction_required": "Corrección requerida",
    "correction_uploaded": "Corrección cargada",
    "rerun_pending": "Pendiente re-análisis",
    "resolved": "Resuelto",
    "still_present": "Aún presente",
    "false_positive": "Falso positivo",
}

UPLOAD_STATUS_ES: dict[str, str] = {
    "pending": "Pendiente de carga",
    "not_uploaded": "Pendiente de carga",
    "uploaded": "Cargado en Dupla",
    "correction_uploaded": "Cargado en Dupla",
    "not_required": "No requerido",
}

REVIEWER_DECISION_ES: dict[str, str] = {
    "pending": "Pendiente",
    "real": "Real",
    "false_positive": "Falso positivo",
    "defer": "Pendiente",
}

CORRECTION_LIFECYCLE = (
    "Detectado → Revisado → Corrección cargada → Pendiente re-análisis → Resuelto / Aún presente"
)

DISCIPLINE_ENUM_ES: dict[str, str] = {
    "ARCH": "Arquitectura",
    "STRUC": "Estructura",
    "MEP_PLUMBING": "Fontanería",
    "MEP_HVAC": "Mecánico",
    "MEP_ELEC": "Eléctrico",
}

DWG_TO_CORRECT_PENDING = "DWG a corregir: pendiente de decisión del revisor"

CLASH_TYPE_ES: dict[str, str] = {
    "HARD": "Solapamiento constructivo",
    "SOFT": "Conflicto de tolerancia",
    "PENETRATION": "Penetración",
    "CLEARANCE": "Holgura insuficiente",
}


def humanize_discipline_label(raw: str) -> str:
    """Map discipline codes and internal enum strings to Spanish labels."""
    text = str(raw or "").strip()
    if not text or text == _NA:
        return "—"
    if text.startswith("Discipline."):
        token = text.split(".", 1)[-1].strip().upper()
        return DISCIPLINE_ENUM_ES.get(token, token.replace("_", " ").title())
    upper = text.upper()
    mapping = {
        "ARQUITECTURA": "Arquitectura",
        "ESTRUCTURA": "Estructura",
        "FONTANERIA": "Fontanería",
        "ELECTRICIDAD": "Eléctrico",
        "CLIMATIZACION": "Mecánico",
    }
    return mapping.get(upper, text.title())


def _is_internal_discipline_reference(text: str) -> bool:
    lowered = str(text or "").lower()
    return "discipline." in lowered or lowered.startswith("discipline ")


def _is_debug_text(text: str) -> bool:
    lowered = str(text or "").lower()
    if not lowered.strip():
        return True
    return any(marker in lowered for marker in _DEBUG_MARKERS)


def format_correction_status(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if not key:
        return CORRECTION_STATUS_ES["detected"]
    return CORRECTION_STATUS_ES.get(key, key.replace("_", " ").capitalize())


def format_upload_status(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if not key:
        return UPLOAD_STATUS_ES["pending"]
    return UPLOAD_STATUS_ES.get(key, key.replace("_", " ").capitalize())


def format_reviewer_decision(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if not key:
        return REVIEWER_DECISION_ES["pending"]
    return REVIEWER_DECISION_ES.get(key, str(raw).strip().capitalize())


def corrected_delivery_section_lines() -> list[str]:
    """Narrative for «Entrega de planos corregidos»."""
    return [
        "Dupla detecta clashes comparando un par de archivos DWG (DWG A vs DWG B) en la misma corrida de análisis.",
        "El arquitecto o coordinador revisa este informe, localiza cada punto en AutoCAD y corrige el DWG afectado.",
        "El DWG corregido debe subirse de nuevo en Dupla, en la sección de Clashes, vinculado al código y a la corrida correspondiente.",
        "No sobrescriba el DWG original del proyecto: Dupla conserva el archivo base y registra la corrección como una revisión aparte.",
        "Tras la carga, Dupla actualizará el estado del clash. Un re-análisis posterior confirmará si el conflicto quedó resuelto.",
        f"Ciclo de vida: {CORRECTION_LIFECYCLE}.",
    ]


def corrected_delivery_steps() -> list[str]:
    """Numbered operational steps for the delivery section."""
    return [
        "Revise cada código en las láminas DWG A vs DWG B y en la matriz de chequeo.",
        "En AutoCAD, abra el par original (DWG A y DWG B) y aplique el comando Z W indicado.",
        "Corrija en AutoCAD el DWG señalado en «DWG a corregir» (no reemplace el archivo original del repositorio).",
        "Guarde una revisión identificable (ej.: ARQ_P1_REV_S-A1.dwg) y súbala en Clashes → corrida → código de clash.",
        "Registre la decisión del revisor (Real / Falso positivo / Pendiente) y el avance en la bitácora.",
        "Espere el re-análisis de Dupla para confirmar Resuelto o Aún presente.",
    ]


def format_clash_type(raw: str) -> str:
    key = str(raw or "").strip().upper()
    if not key or key == _NA.upper():
        return "Interferencia geométrica"
    return CLASH_TYPE_ES.get(key, "Interferencia geométrica")


def format_dwg_to_correct(
    dwg_to_correct: str,
    *,
    plano_a: str,
    plano_b: str,
    disciplina_a: str,
    disciplina_b: str,
) -> str:
    target = str(dwg_to_correct or "").strip()
    if target and target != _NA and not _is_debug_text(target) and not _is_internal_discipline_reference(target):
        return _basename_or_label(target, plano_a, plano_b)
    return DWG_TO_CORRECT_PENDING


def _basename_or_label(path: str, plano_a: str, plano_b: str) -> str:
    name = path.replace("\\", "/").split("/")[-1]
    if name.lower() in {plano_a.lower(), plano_b.lower()}:
        return plano_a if name.lower() == plano_a.lower() else plano_b
    return name


def build_architectural_observation(
    *,
    layer_a: str,
    layer_b: str,
    nivel: str,
    disciplina_a: str,
    disciplina_b: str,
    plano_a: str,
    plano_b: str,
    area_m2: float | None = None,
    human_description: str = "",
) -> str:
    """Return reviewer-facing observation text in architectural language."""
    if human_description and not _is_debug_text(human_description):
        cleaned = " ".join(human_description.split())
        if cleaned and cleaned != _NA:
            return _ensure_period(cleaned)

    parts: list[str] = []
    la = layer_a if layer_a and layer_a != _NA else ""
    lb = layer_b if layer_b and layer_b != _NA else ""
    if la and lb:
        parts.append(f"Verificar solape entre capa {la} y capa {lb} en nivel {nivel}.")
    elif la or lb:
        layer = la or lb
        parts.append(f"Verificar interferencia en capa {layer} en nivel {nivel}.")
    else:
        parts.append(
            f"Verificar coordinación entre {disciplina_a} y {disciplina_b} "
            f"({plano_a} vs {plano_b}) en nivel {nivel}."
        )

    if area_m2 is not None and 0 < area_m2 < 0.05:
        parts.append(
            "Confirmar si el cruce corresponde a elemento constructivo real o a anotación gráfica."
        )
    return " ".join(parts)


def build_architectural_action(
    *,
    dwg_to_correct: str,
    plano_a: str,
    plano_b: str,
    recommended_action: str = "",
) -> str:
    if recommended_action and not _is_debug_text(recommended_action):
        return _ensure_period(" ".join(recommended_action.split()))

    target = format_dwg_to_correct(
        dwg_to_correct,
        plano_a=plano_a,
        plano_b=plano_b,
        disciplina_a="",
        disciplina_b="",
    )
    if target == DWG_TO_CORRECT_PENDING or target.startswith("Definir"):
        return (
            "Corregir el DWG correspondiente del par comparado y subir la revisión "
            "en la sección de Clashes."
        )
    return (
        f"Corregir el DWG {target} y subir la revisión en la sección de Clashes."
    )


def format_ubicacion_zw(
    *,
    center_text: str,
    zoom_command: str,
    zoom_fallback: str | None = None,
) -> str:
    """Location column: Z W command with optional center reference (newline-separated)."""
    return "\n".join(
        format_ubicacion_zw_lines(
            center_text=center_text,
            zoom_command=zoom_command,
            zoom_fallback=zoom_fallback,
        )
    )


def format_ubicacion_zw_lines(
    *,
    center_text: str,
    zoom_command: str,
    zoom_fallback: str | None = None,
) -> list[str]:
    """Return ubicación lines for ReportLab paragraph rendering."""
    zw = str(zoom_command or "").strip()
    if zw and zw.upper().startswith("Z W"):
        lines: list[str] = []
        if center_text and center_text != _NA:
            lines.append(center_text)
        lines.append(zw)
        return lines
    if zoom_fallback and not _is_debug_text(zoom_fallback):
        return [_sanitize_zoom_fallback(zoom_fallback)]
    if center_text and center_text != _NA:
        return [center_text, "Localizar manualmente en AutoCAD (Z E)."]
    return ["Localizar manualmente en AutoCAD usando nivel y capas indicadas."]


def _sanitize_zoom_fallback(text: str) -> str:
    cleaned = " ".join(text.split())
    cleaned = cleaned.replace("Limites de zoom no disponibles;", "Ubicación aproximada no disponible;")
    cleaned = cleaned.replace("limites de zoom no disponibles;", "ubicación aproximada no disponible;")
    return _ensure_period(cleaned)


def _ensure_period(text: str) -> str:
    text = text.strip()
    if text and text[-1] not in ".!?":
        return f"{text}."
    return text


def humanize_confidence(raw: str) -> str:
    mapping = {"high": "Alta", "medium": "Media", "low": "Baja"}
    key = str(raw or "").lower()
    return mapping.get(key, "—")


def filter_human_warnings(warnings: list[str] | None) -> list[str]:
    """Drop internal normalization warnings from architect-facing output."""
    if not warnings:
        return []
    out: list[str] = []
    for warning in warnings:
        if _is_debug_text(warning):
            continue
        if re.search(r"capas no disponibles|centro xy no disponible|limites no disponibles|comando z w no generado", warning, re.I):
            continue
        out.append(warning)
    return out
