"""
Infer Dupla source discipline and numeric chapter prefix from takeoffs / budget metadata.
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.schemas import ProjectContext, QuantityTakeoff, QuantityTrace


def infer_source_discipline(
    takeoff: QuantityTakeoff,
    context: ProjectContext | None = None,
) -> str:
    """
    Map pipeline context + takeoff fields to one of:
    arquitectonica | estructural | electrica | sanitaria
    """
    meta = context.metadata if context is not None else {}
    did = str(meta.get("discipline_id") or "").strip().lower()
    aliases = {
        "arquitectura": "arquitectonica",
        "arq": "arquitectonica",
        "arquitectonica": "arquitectonica",
        "estructura": "estructural",
        "estructural": "estructural",
        "electric": "electrica",
        "electrical": "electrica",
        "electrica": "electrica",
        "plumbing": "sanitaria",
        "sanitario": "sanitaria",
        "sanitaria": "sanitaria",
    }
    if did:
        return aliases.get(did, did if did in set(aliases.values()) else "arquitectonica")

    inp = str(takeoff.inputs.get("discipline") or "").strip().lower()
    if inp in ("electrical", "electric", "electrica"):
        return "electrica"
    if inp in ("plumbing", "sanitary", "sanitaria"):
        return "sanitaria"

    it = takeoff.item_type.lower()
    if it == "pres_reference_line":
        pd = str(takeoff.inputs.get("pres_discipline", "") or "").upper()
        if any(x in pd for x in ("HORMIGON", "HORMIG", "ACERO", "REFUERZO", "LOSA", "VIGA", "COLUM")):
            return "estructural"
        if any(x in pd for x in ("ELECTRIC", "ELECTR")):
            return "electrica"
        if any(x in pd for x in ("SANIT", "AGUA", "DESAG", "PLUMB")):
            return "sanitaria"
        return "arquitectonica"

    if it.startswith(("beam_", "column_", "slab_", "footing_", "structural_")) or it in (
        "structural_area",
    ):
        return "estructural"

    if it == "fixture_count":
        d = str(takeoff.inputs.get("discipline") or "").lower()
        if d in ("electrical", "electric"):
            return "electrica"
        if d in ("plumbing", "sanitary"):
            return "sanitaria"
        return "arquitectonica"

    if it == "wet_area_fixture_count":
        return "sanitaria"

    return "arquitectonica"


_TOP_CHAPTER_RE = re.compile(r"^(\d{2})(?:\.|$)")


def top_chapter_prefix_from_line(line: dict[str, Any]) -> str | None:
    """First two-digit Dupla chapter from composed line metadata, if present."""
    meta = line.get("metadata") if isinstance(line.get("metadata"), dict) else {}
    codes = meta.get("chapter_codes") or []
    if isinstance(codes, str):
        codes = [codes]
    for raw in codes:
        c = str(raw).strip()
        m = _TOP_CHAPTER_RE.match(c)
        if m:
            return m.group(1)
    return None


def line_dict_from_budget_line(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    raise TypeError(f"Unsupported line type: {type(obj)!r}")


def takeoff_dict_from_context(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    raise TypeError(f"Unsupported takeoff type: {type(obj)!r}")


def coerce_takeoff(data: dict[str, Any], *, fallback_key: str = "") -> QuantityTakeoff:
    """Reconstruye ``QuantityTakeoff`` desde el dict serializado del pipeline."""
    tr_data = data.get("trace") or {}
    if isinstance(tr_data, QuantityTrace):
        tr = tr_data
    else:
        tr = QuantityTrace(
            source_entity_ids=list(tr_data.get("source_entity_ids") or []),
            source_entity_sources=list(tr_data.get("source_entity_sources") or []),
            metadata=dict(tr_data.get("metadata") or {}),
        )
    return QuantityTakeoff(
        item_key=str(data.get("item_key") or fallback_key),
        item_type=str(data.get("item_type") or ""),
        level_id=data.get("level_id"),
        unit=str(data.get("unit") or ""),
        quantity=float(data.get("quantity") or 0.0),
        formula=str(data.get("formula") or ""),
        inputs=dict(data.get("inputs") or {}),
        assumptions=list(data.get("assumptions") or []),
        source_refs=list(data.get("source_refs") or []),
        trace=tr,
    )
