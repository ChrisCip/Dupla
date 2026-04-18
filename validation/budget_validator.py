"""
Validaciones V1–V5 sobre líneas de presupuesto ya compuestas + catálogo BC3.

Diseñado para ejecutarse después del compositor (o en exportación Excel).
No inventa datos: solo señala incoherencias frente a reglas y al catálogo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from analysis.detail_inventory import DetailReport

from .discipline_inference import (
    coerce_takeoff,
    infer_source_discipline,
    line_dict_from_budget_line,
    takeoff_dict_from_context,
    top_chapter_prefix_from_line,
)

_RULES_PATH = Path(__file__).resolve().parent / "discipline_rules.json"


def load_discipline_rules(path: Path | None = None) -> dict[str, Any]:
    p = path or _RULES_PATH
    return json.loads(p.read_text(encoding="utf-8"))


@dataclass
class ValidationIssue:
    code: str
    severity: str  # "error" | "warning"
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message, "context": self.context}


@dataclass
class BudgetValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "issues": [i.to_dict() for i in self.issues],
            "stats": dict(self.stats),
        }


def validate_discipline_assignment(
    *,
    partida: dict[str, Any],
    chapter_prefix: str | None,
    source_discipline: str,
    rules: dict[str, Any],
) -> list[ValidationIssue]:
    """
    V1 — capítulo numérico Dupla (prefijo 01–09) debe caer en el mapa de la disciplina.
    Si no hay prefijo (p.ej. capítulos 100% BC3 A.*), no aplica y no genera issue.
    """
    issues: list[ValidationIssue] = []
    if not chapter_prefix:
        return issues
    mapping: dict[str, list[str]] = rules.get("discipline_to_chapters") or {}
    allowed = set(mapping.get(source_discipline) or [])
    if not allowed:
        issues.append(
            ValidationIssue(
                code="V1_UNKNOWN_DISCIPLINE",
                severity="warning",
                message=f"Disciplina de origen no mapeada: {source_discipline!r}",
                context={"takeoff_key": partida.get("takeoff_key"), "chapter_prefix": chapter_prefix},
            )
        )
        return issues
    if chapter_prefix not in allowed:
        issues.append(
            ValidationIssue(
                code="V1_DISCIPLINE_CHAPTER_MISMATCH",
                severity="error",
                message=(
                    f"Partida con disciplina {source_discipline!r} aparece bajo capítulo {chapter_prefix!r}, "
                    f"no permitido por reglas (permitidos: {sorted(allowed)})"
                ),
                context={
                    "takeoff_key": partida.get("takeoff_key"),
                    "summary": partida.get("summary"),
                    "chapter_prefix": chapter_prefix,
                },
            )
        )
    return issues


def detect_cross_discipline_duplicates(
    budget_by_discipline: dict[str, list[dict[str, Any]]],
    *,
    fingerprint_keys: tuple[str, ...] = ("inventory_entity_id", "wall_id", "derived_from"),
) -> list[ValidationIssue]:
    """
    V2 — detecta la misma huella de elemento presupuestada en más de una disciplina.
    """
    issues: list[ValidationIssue] = []
    fp_map: dict[str, list[str]] = {}
    for disc, rows in budget_by_discipline.items():
        for row in rows:
            meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            fp = None
            for k in fingerprint_keys:
                v = meta.get(k)
                if v:
                    fp = str(v).strip()
                    break
            if not fp:
                key = str(row.get("takeoff_key") or "")
                fp = key.split(":", 1)[0] if key else ""
            if not fp:
                continue
            fp_map.setdefault(fp, []).append(disc)

    for fp, discs in fp_map.items():
        uniq = sorted(set(discs))
        if len(uniq) > 1:
            issues.append(
                ValidationIssue(
                    code="V2_CROSS_DISCIPLINE_DUPLICATE",
                    severity="warning",
                    message="Misma huella de elemento contada en varias disciplinas",
                    context={"fingerprint": fp, "disciplines": uniq},
                )
            )
    return issues


def validate_quantities(
    partidas: list[dict[str, Any]],
    detail_report: DetailReport | None,
    *,
    takeoff_by_key: dict[str, dict[str, Any]] | None = None,
) -> list[ValidationIssue]:
    """
    V3 — cruza cantidades con DetailReport cuando está disponible.

    - missing + cantidad > 0 → error (no inventar)
    - implicit: se podría marcar en metadata quantity_estimated (opcional); aquí solo warning si hay señal
    """
    issues: list[ValidationIssue] = []
    if detail_report is None:
        return issues

    missing_ids = {m.element_id for m in detail_report.missing_elements if m.element_id}
    implicit_ids = {i.element_id for i in detail_report.implicit_elements if i.element_id}

    for p in partidas:
        qty = float(p.get("quantity") or 0.0)
        key = str(p.get("takeoff_key") or "")
        meta = p.get("metadata") if isinstance(p.get("metadata"), dict) else {}
        inv_id = str(meta.get("inventory_entity_id") or meta.get("element_id") or "").strip()
        if not inv_id and takeoff_by_key and key in takeoff_by_key:
            tmeta = takeoff_by_key[key].get("inputs") or {}
            if isinstance(tmeta, dict):
                inv_id = str(tmeta.get("inventory_entity_id") or tmeta.get("element_id") or "").strip()

        if inv_id and inv_id in missing_ids and qty > 0:
            issues.append(
                ValidationIssue(
                    code="V3_QUANTITY_FOR_MISSING_ELEMENT",
                    severity="error",
                    message="Cantidad > 0 pero el elemento figura como FALTANTE en DetailReport",
                    context={"takeoff_key": key, "element_id": inv_id, "quantity": qty},
                )
            )
        if inv_id and inv_id in implicit_ids and qty > 0:
            if not meta.get("quantity_estimated"):
                issues.append(
                    ValidationIssue(
                        code="V3_IMPLICIT_QUANTITY_UNFLAGGED",
                        severity="warning",
                        message="Cantidad sobre elemento IMPLÍCITO sin flag quantity_estimated en metadata",
                        context={"takeoff_key": key, "element_id": inv_id, "quantity": qty},
                    )
                )
    return issues


def validate_pricing(partidas: list[dict[str, Any]], bc3_catalog: dict[str, Any] | None) -> list[ValidationIssue]:
    """
    V4 — precio debe existir en catálogo BC3 para el código de partida usado.

    Si no hay catálogo, solo advierte líneas con precio pero sin candidate_code.
    """
    issues: list[ValidationIssue] = []
    if not bc3_catalog:
        for p in partidas:
            up = p.get("unit_price")
            if up is not None and float(up or 0) > 0 and not str(p.get("candidate_code") or p.get("code") or ""):
                issues.append(
                    ValidationIssue(
                        code="V4_PRICE_WITHOUT_CODE",
                        severity="warning",
                        message="Precio unitario sin código BC3 de referencia",
                        context={"takeoff_key": p.get("takeoff_key")},
                    )
                )
        return issues

    concepts = bc3_catalog.get("concepts_by_code") or {}

    for p in partidas:
        code = str(p.get("candidate_code") or p.get("code") or "").strip()
        if not code or code.upper().startswith("DUP"):
            if p.get("unit_price") is not None and float(p.get("unit_price") or 0) > 0:
                issues.append(
                    ValidationIssue(
                        code="V4_SYNTHETIC_LINE_WITH_PRICE",
                        severity="warning",
                        message="Línea sin código BC3 catalogado pero con precio",
                        context={"takeoff_key": p.get("takeoff_key"), "code": code},
                    )
                )
            continue
        row = concepts.get(code) or {}
        price = float(row.get("price") or 0.0)
        up = p.get("unit_price")
        up_f = float(up) if up is not None else None
        if price <= 0:
            issues.append(
                ValidationIssue(
                    code="V4_SIN_PRECIO_BC3",
                    severity="warning",
                    message="Código BC3 sin precio en catálogo — requiere cotización manual",
                    context={"takeoff_key": p.get("takeoff_key"), "bc3_code": code},
                )
            )
            if up_f is not None and up_f > 0:
                issues.append(
                    ValidationIssue(
                        code="V4_PRICE_WITHOUT_CATALOG_BACKING",
                        severity="error",
                        message="Precio > 0 en línea pero el catálogo BC3 no lista precio para ese código",
                        context={"takeoff_key": p.get("takeoff_key"), "bc3_code": code, "line": up_f},
                    )
                )
        elif up_f is not None and abs(up_f - price) > 0.02:
            issues.append(
                ValidationIssue(
                    code="V4_PRICE_MISMATCH_CATALOG",
                    severity="warning",
                    message="Precio unitario distinto del precio listado en concepts BC3 (puede ser ConstruCosto u otra fuente)",
                    context={"takeoff_key": p.get("takeoff_key"), "bc3_code": code, "line": up_f, "catalog": price},
                )
            )
    return issues


def validate_chapter_completeness(
    lines: list[dict[str, Any]],
    discipline: str,
    rules: dict[str, Any],
) -> list[ValidationIssue]:
    """V5 — pistas de completitud por disciplina (keywords en resúmenes)."""
    issues: list[ValidationIssue] = []
    hints = (rules.get("completeness_hints") or {}).get(discipline) or {}
    if not hints.get("warning_if_no_line_matches"):
        return issues
    kws = [k.lower() for k in hints.get("summary_keywords_any") or []]
    if not kws:
        return issues
    texts = " ".join(str(line.get("summary") or "").lower() for line in lines)
    if not any(k in texts for k in kws):
        issues.append(
            ValidationIssue(
                code="V5_COMPLETENESS_HINT",
                severity="warning",
                message=f"Ninguna partida coincide con palabras clave esperadas para {discipline}",
                context={"discipline": discipline, "keywords": kws},
            )
        )
    return issues


def run_budget_validation(
    lines: Iterable[Any],
    takeoffs: Iterable[Any],
    *,
    bc3_catalog: dict[str, Any] | None = None,
    rules: dict[str, Any] | None = None,
    detail_reports_by_discipline: dict[str, DetailReport] | None = None,
    context: Any | None = None,
) -> BudgetValidationReport:
    """
    Ejecuta V1–V5 y devuelve un reporte agregado.

    ``context`` puede ser ``ProjectContext`` para inferir disciplina con
    ``discipline_id`` por corrida.
    """
    rules = rules or load_discipline_rules()
    line_dicts = [line_dict_from_budget_line(x) for x in lines]
    takeoff_list = [takeoff_dict_from_context(t) for t in takeoffs]
    takeoff_by_key = {str(t.get("item_key")): t for t in takeoff_list if t.get("item_key")}

    from core.schemas import ProjectContext

    ctx_obj = context if isinstance(context, ProjectContext) else None

    issues: list[ValidationIssue] = []
    by_disc: dict[str, list[dict[str, Any]]] = {}

    for ld in line_dicts:
        key = str(ld.get("takeoff_key") or "")
        to = takeoff_by_key.get(key, {})
        to_obj = coerce_takeoff(to, fallback_key=key)
        disc = infer_source_discipline(to_obj, ctx_obj)
        by_disc.setdefault(disc, []).append(ld)
        if "metadata" not in ld or not isinstance(ld["metadata"], dict):
            ld["metadata"] = {}
        ld["metadata"]["source_discipline"] = disc

        ch = top_chapter_prefix_from_line(ld)
        issues.extend(
            validate_discipline_assignment(
                partida=ld,
                chapter_prefix=ch,
                source_discipline=disc,
                rules=rules,
            )
        )

    issues.extend(detect_cross_discipline_duplicates(by_disc))

    if detail_reports_by_discipline:
        for disc, rep in detail_reports_by_discipline.items():
            partidas_for_disc = by_disc.get(disc, [])
            issues.extend(validate_quantities(partidas_for_disc, rep, takeoff_by_key=takeoff_by_key))

    issues.extend(validate_pricing(line_dicts, bc3_catalog))

    for disc in sorted(by_disc.keys()):
        issues.extend(validate_chapter_completeness(by_disc[disc], disc, rules))

    stats = {
        "lines": len(line_dicts),
        "errors": sum(1 for i in issues if i.severity == "error"),
        "warnings": sum(1 for i in issues if i.severity == "warning"),
    }
    return BudgetValidationReport(issues=issues, stats=stats)
