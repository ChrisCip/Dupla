"""
Structural discipline quantifier (Sprint S3 Blocks 6-7).

Computes concrete volume, formwork area, and rebar weight for columns,
beams, slabs, and footings from explicit inputs on each ``StructuralElement``.
Falls back to the monolithic ``quantify_inventory`` so anything we don't
recognise still produces a takeoff.

Rebar is delegated to ``disciplines.estructura.rebar`` (NO volumetric
estimation ratios) when the element carries explicit reinforcement notation;
otherwise a discipline-specific ratio is applied with the assumption logged
on the takeoff.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from agents.quantifier_agent import quantify_inventory as _quantify_all
from core.schemas import LevelInventory, QuantityTakeoff, QuantityTrace, StructuralElement

from .rebar import (
    REBAR_CATALOG,
    calculate_main_bar_weight,
    calculate_stirrup_weight,
    parse_reinforcement,
)

logger = logging.getLogger("dupla.disciplines.estructura")

# Re-export the catalog under the ASTM name used by some external callers.
ASTM_A615_CATALOG = REBAR_CATALOG

_STRUCTURAL_ITEM_TYPES = frozenset({
    "structural_count", "structural_length", "structural_area", "structural_volume",
    "beam_concrete_volume", "beam_volume", "beam_area", "beam_length", "beam_count",
    "beam_formwork_area_hint", "beam_formwork_area", "beam_reinforcement_kg",
    "column_concrete_volume", "column_volume", "column_area", "column_length", "column_count",
    "column_formwork_area_hint", "column_formwork_area", "column_reinforcement_kg",
    "slab_concrete_volume", "slab_area", "slab_count",
    "slab_formwork_area_hint", "slab_formwork_area", "slab_reinforcement_kg",
    "footing_concrete_volume", "footing_volume", "footing_area",
    "footing_formwork_area_hint", "footing_formwork_area", "footing_reinforcement_kg",
    "footing_lean_concrete_volume", "footing_excavation_volume",
    "stair_count",
})

# Discipline-default rebar ratios when explicit notation is missing.
# kg of steel per m³ of concrete. Documented as ASSUMPTIONS on each takeoff.
_REBAR_RATIO_KG_PER_M3: dict[str, float] = {
    "column": 100.0,
    "beam":   100.0,
    "slab":   120.0,
    "footing": 80.0,
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _f(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _parse_section_string(section: str) -> tuple[float | None, float | None]:
    """Parse '0.30x0.40' / '30x40' / '0.30×0.40' -> (width_m, height_m)."""
    if not section:
        return None, None
    s = str(section).lower().replace("×", "x").replace(" ", "")
    if "x" not in s:
        return None, None
    a, _, b = s.partition("x")
    try:
        wa, hb = float(a), float(b)
    except ValueError:
        return None, None
    if wa > 5 and hb > 5:   # both >5 → cm form
        return wa / 100.0, hb / 100.0
    return wa, hb


def _section_dims(elem: StructuralElement) -> tuple[float | None, float | None]:
    inputs = elem.inputs or {}
    w = _f(getattr(elem, "section_width_m", None)) or _f(inputs.get("section_width_m"))
    h = _f(getattr(elem, "section_height_m", None)) or _f(inputs.get("section_height_m"))
    if w is None or h is None:
        sw, sh = _parse_section_string(inputs.get("section") or inputs.get("section_text") or "")
        w = w or sw
        h = h or sh
    return w, h


def _length(elem: StructuralElement) -> float | None:
    inputs = elem.inputs or {}
    return (
        _f(getattr(elem, "length_m", None))
        or _f(inputs.get("length_m"))
        or _f(inputs.get("span_m"))
        or _f(inputs.get("height_m"))
    )


def _count(elem: StructuralElement) -> int:
    # Prefer explicit inputs.count (vision/CAD source) over the schema default,
    # which is 1 and would silently swallow an "8 zapatas iguales" input.
    inputs = elem.inputs or {}
    for candidate in (inputs.get("count"), getattr(elem, "count", None)):
        if candidate is None:
            continue
        try:
            n = int(float(candidate))
        except (TypeError, ValueError):
            continue
        if n >= 1:
            return n
    return 1


def _subtype(elem: StructuralElement) -> str:
    inputs = elem.inputs or {}
    return str(inputs.get("element_subtype") or inputs.get("subtype") or "").lower()


def _trace(steps: list[str], metadata: dict[str, Any] | None = None) -> QuantityTrace:
    return QuantityTrace(evidence=list(steps), metadata=dict(metadata or {}))


def _element_description(elem: StructuralElement, key_suffix: str) -> str:
    et_label = {"column": "Columna", "beam": "Viga", "slab": "Losa", "footing": "Zapata"}.get(
        elem.element_type, str(elem.element_type or "Elemento")
    )
    inp = elem.inputs or {}
    label = str(inp.get("structural_label") or elem.id or "").strip()
    w, h = _section_dims(elem)
    bits = [et_label]
    if label and label != elem.id and not label.startswith("json-"):
        bits.append(label)
    if w is not None and h is not None:
        bits.append(f"seccion {w:.2f}x{h:.2f} m")
    suffix_label = {
        "concrete": "hormigon",
        "rebar": "acero",
        "formwork": "encofrado",
        "lean": "hormigon de limpieza",
        "excavation": "excavacion",
    }
    last = key_suffix.split("_")[-1]
    if last in suffix_label:
        bits.append(suffix_label[last])
    return " — ".join(bits)


def _takeoff(
    *,
    elem: StructuralElement,
    level_id: str,
    key_suffix: str,
    item_type: str,
    unit: str,
    quantity: float,
    formula: str,
    inputs: dict[str, Any],
    assumptions: list[str],
    trace_steps: list[str],
) -> QuantityTakeoff:
    return QuantityTakeoff(
        item_key=f"{elem.id}:{key_suffix}",
        item_type=item_type,
        level_id=level_id,
        unit=unit,
        quantity=round(quantity, 4),
        formula=formula,
        inputs={
            **inputs,
            "takeoff_description": _element_description(elem, key_suffix),
            "context_tags": [elem.element_type, key_suffix.split("_")[-1]],
        },
        assumptions=list(assumptions),
        source_refs=list(elem.source_refs or []),
        trace=_trace(trace_steps, {"element_id": elem.id, "element_type": elem.element_type}),
    )


# ---------------------------------------------------------------------------
# Rebar weight (uses rebar.py when notation present, ratio otherwise)
# ---------------------------------------------------------------------------

def _calc_rebar_kg(
    elem: StructuralElement,
    *,
    length_m: float,
    section_width_m: float | None,
    section_height_m: float | None,
    concrete_volume_m3: float | None,
) -> tuple[float, str, list[str]]:
    """Return ``(total_kg, formula, assumptions)``."""
    inputs = elem.inputs or {}
    main_notation = inputs.get("reinforcement_main_bars") or inputs.get("main_bars")
    stirrup_notation = inputs.get("reinforcement_stirrups") or inputs.get("stirrups")

    if main_notation:
        parsed = parse_reinforcement(main_notation, stirrup_notation)
        main = calculate_main_bar_weight(parsed.main_bars, length_m)
        stirrup_kg = 0.0
        stirrup_note = ""
        if parsed.stirrups and section_width_m and section_height_m:
            stirrup_res = calculate_stirrup_weight(
                parsed.stirrups, length_m, section_width_m, section_height_m,
            )
            stirrup_kg = float(stirrup_res.get("total_kg", 0.0))
            stirrup_note = f" + estribos({stirrup_notation})={stirrup_kg:.2f}kg"
        total = float(main["total_kg"]) + stirrup_kg
        formula = (
            f"rebar('{main_notation}', L={length_m}m) = "
            f"{main['total_kg']:.2f}kg{stirrup_note}"
        )
        assumptions = list(main.get("assumptions", []))
        assumptions.insert(0, "Steel weight from explicit plan notation via rebar.py (no estimation).")
        return total, formula, assumptions

    ratio = _REBAR_RATIO_KG_PER_M3.get(elem.element_type, 100.0)
    vol = concrete_volume_m3 or 0.0
    total = ratio * vol
    return total, f"{ratio} kg/m3 × {vol:.3f} m3 (ratio estimate, no plan notation)", [
        f"No explicit reinforcement notation; applied default ratio {ratio} kg/m3 for {elem.element_type}.",
        "quantity_source=ratio_estimate",
    ]


# ---------------------------------------------------------------------------
# Per-element calculators
# ---------------------------------------------------------------------------

def _quantify_column(elem: StructuralElement, level_id: str) -> list[QuantityTakeoff]:
    w, h = _section_dims(elem)
    length = _length(elem)
    n = _count(elem)
    out: list[QuantityTakeoff] = []
    if not (w and h and length):
        return out

    vol = w * h * length * n
    out.append(_takeoff(
        elem=elem, level_id=level_id, key_suffix="concrete_volume",
        item_type="column_concrete_volume", unit="m3", quantity=vol,
        formula=f"{w:.2f}×{h:.2f}×{length:.2f}×{n} = {vol:.3f} m3",
        inputs={"section_width_m": w, "section_height_m": h, "length_m": length, "count": n,
                "material_hint": elem.material_hint},
        assumptions=[], trace_steps=["Column volume = w × h × L × count."],
    ))

    perimeter = 2 * (w + h)
    formwork = perimeter * length * n
    out.append(_takeoff(
        elem=elem, level_id=level_id, key_suffix="formwork_area",
        item_type="column_formwork_area", unit="m2", quantity=formwork,
        formula=f"perim(2×({w:.2f}+{h:.2f}))×{length:.2f}×{n} = {formwork:.2f} m2",
        inputs={"section_width_m": w, "section_height_m": h, "length_m": length, "count": n},
        assumptions=[], trace_steps=["Column formwork = perimeter × length × count (4 caras)."],
    ))

    kg, formula, kg_assumptions = _calc_rebar_kg(
        elem, length_m=length, section_width_m=w, section_height_m=h, concrete_volume_m3=vol,
    )
    if kg > 0:
        kg_total = kg * n if "ratio" not in formula else kg
        out.append(_takeoff(
            elem=elem, level_id=level_id, key_suffix="reinforcement_kg",
            item_type="column_reinforcement_kg", unit="kg", quantity=kg_total,
            formula=formula + (f" × {n} count" if "ratio" not in formula and n > 1 else ""),
            inputs={"length_m": length, "count": n, "material_hint": "steel"},
            assumptions=kg_assumptions,
            trace_steps=["Steel via rebar.py." if "rebar(" in formula else "Steel via discipline ratio."],
        ))
    return out


def _quantify_beam(elem: StructuralElement, level_id: str) -> list[QuantityTakeoff]:
    w, h = _section_dims(elem)
    length = _length(elem)
    n = _count(elem)
    subtype = _subtype(elem)
    out: list[QuantityTakeoff] = []
    if not (w and h and length):
        return out

    vol = w * h * length * n
    out.append(_takeoff(
        elem=elem, level_id=level_id, key_suffix="concrete_volume",
        item_type="beam_concrete_volume", unit="m3", quantity=vol,
        formula=f"{w:.2f}×{h:.2f}×{length:.2f}×{n} = {vol:.3f} m3",
        inputs={"section_width_m": w, "section_height_m": h, "length_m": length, "count": n,
                "beam_type": subtype or None, "material_hint": elem.material_hint},
        assumptions=[], trace_steps=["Beam volume = w × h × L × count."],
    ))

    formwork = (2 * h + w) * length * n
    out.append(_takeoff(
        elem=elem, level_id=level_id, key_suffix="formwork_area",
        item_type="beam_formwork_area", unit="m2", quantity=formwork,
        formula=f"(2×{h:.2f}+{w:.2f})×{length:.2f}×{n} = {formwork:.2f} m2",
        inputs={"section_width_m": w, "section_height_m": h, "length_m": length, "count": n,
                "beam_type": subtype or None},
        assumptions=["Beam formwork: 3 caras (fondo + 2 laterales)."],
        trace_steps=["Beam formwork = (2×h + w) × L × count."],
    ))

    kg, formula, kg_assumptions = _calc_rebar_kg(
        elem, length_m=length, section_width_m=w, section_height_m=h, concrete_volume_m3=vol,
    )
    if kg > 0:
        kg_total = kg * n if "ratio" not in formula else kg
        out.append(_takeoff(
            elem=elem, level_id=level_id, key_suffix="reinforcement_kg",
            item_type="beam_reinforcement_kg", unit="kg", quantity=kg_total,
            formula=formula + (f" × {n} count" if "ratio" not in formula and n > 1 else ""),
            inputs={"length_m": length, "count": n, "material_hint": "steel", "beam_type": subtype or None},
            assumptions=kg_assumptions,
            trace_steps=["Steel via rebar.py." if "rebar(" in formula else "Steel via ratio."],
        ))
    return out


def _quantify_slab(elem: StructuralElement, level_id: str) -> list[QuantityTakeoff]:
    inputs = elem.inputs or {}
    area = _f(getattr(elem, "area_m2", None)) or _f(inputs.get("area_m2"))
    thickness = _f(inputs.get("thickness_m"))
    n = _count(elem)
    out: list[QuantityTakeoff] = []
    if not area or not thickness:
        return out

    vol = area * thickness * n
    out.append(_takeoff(
        elem=elem, level_id=level_id, key_suffix="concrete_volume",
        item_type="slab_concrete_volume", unit="m3", quantity=vol,
        formula=f"{area:.2f}×{thickness:.3f}×{n} = {vol:.3f} m3",
        inputs={"area_m2": area, "thickness_m": thickness, "count": n,
                "slab_type": inputs.get("slab_type")},
        assumptions=[], trace_steps=["Slab volume = area × thickness × count."],
    ))

    kg, formula, kg_assumptions = _calc_rebar_kg(
        elem, length_m=thickness, section_width_m=None, section_height_m=None,
        concrete_volume_m3=vol,
    )
    if kg > 0:
        out.append(_takeoff(
            elem=elem, level_id=level_id, key_suffix="reinforcement_kg",
            item_type="slab_reinforcement_kg", unit="kg", quantity=kg,
            formula=formula,
            inputs={"area_m2": area, "thickness_m": thickness, "material_hint": "steel"},
            assumptions=kg_assumptions,
            trace_steps=["Steel via rebar.py." if "rebar(" in formula else "Steel via 120 kg/m3 slab ratio."],
        ))
    return out


def _quantify_footing(elem: StructuralElement, level_id: str) -> list[QuantityTakeoff]:
    inputs = elem.inputs or {}
    L = _f(inputs.get("length_m")) or _f(getattr(elem, "length_m", None))
    W = _f(inputs.get("width_m")) or _f(inputs.get("section_width_m"))
    D = _f(inputs.get("depth_m")) or _f(inputs.get("peralte_m")) or _f(inputs.get("thickness_m"))
    n = _count(elem)
    out: list[QuantityTakeoff] = []
    if not (L and W and D):
        return out

    vol = L * W * D * n
    out.append(_takeoff(
        elem=elem, level_id=level_id, key_suffix="concrete_volume",
        item_type="footing_concrete_volume", unit="m3", quantity=vol,
        formula=f"{L:.2f}×{W:.2f}×{D:.2f}×{n} = {vol:.3f} m3",
        inputs={"length_m": L, "width_m": W, "depth_m": D, "count": n},
        assumptions=[], trace_steps=["Footing volume = L × W × D × count."],
    ))

    lean = L * W * 0.05 * n
    out.append(_takeoff(
        elem=elem, level_id=level_id, key_suffix="lean_concrete_volume",
        item_type="footing_lean_concrete_volume", unit="m3", quantity=lean,
        formula=f"{L:.2f}×{W:.2f}×0.05×{n} = {lean:.3f} m3",
        inputs={"length_m": L, "width_m": W, "count": n},
        assumptions=["Hormigon de limpieza: capa 5 cm (constructor standard)."],
        trace_steps=["Lean concrete = L × W × 0.05 × count."],
    ))

    perimeter = 2 * (L + W)
    formwork = perimeter * D * n
    out.append(_takeoff(
        elem=elem, level_id=level_id, key_suffix="formwork_area",
        item_type="footing_formwork_area", unit="m2", quantity=formwork,
        formula=f"2×({L:.2f}+{W:.2f})×{D:.2f}×{n} = {formwork:.2f} m2",
        inputs={"length_m": L, "width_m": W, "depth_m": D, "count": n},
        assumptions=["Footing formwork: perímetro × peralte (4 caras)."],
        trace_steps=["Footing formwork = perimeter × D × count."],
    ))

    kg, formula, kg_assumptions = _calc_rebar_kg(
        elem, length_m=L, section_width_m=W, section_height_m=D, concrete_volume_m3=vol,
    )
    if kg > 0:
        out.append(_takeoff(
            elem=elem, level_id=level_id, key_suffix="reinforcement_kg",
            item_type="footing_reinforcement_kg", unit="kg", quantity=kg,
            formula=formula,
            inputs={"length_m": L, "width_m": W, "depth_m": D, "material_hint": "steel"},
            assumptions=kg_assumptions,
            trace_steps=["Steel via rebar.py." if "rebar(" in formula else "Steel via 80 kg/m3 footing ratio."],
        ))
    return out


_DISPATCH = {
    "column":  _quantify_column,
    "beam":    _quantify_beam,
    "slab":    _quantify_slab,
    "footing": _quantify_footing,
}


def quantify(levels: Iterable[LevelInventory]) -> list[QuantityTakeoff]:
    """Structural quantification.

    For each ``StructuralElement`` with usable geometry, emit explicit
    concrete + formwork + rebar takeoffs computed from the inputs.
    Anything we don't recognise still goes through the monolithic quantifier
    and is filtered down to structural item types — never regress on what
    already works.
    """
    level_list = list(levels)
    out: list[QuantityTakeoff] = []
    handled_ids: set[str] = set()

    for level in level_list:
        for elem in (level.structural_elements or []):
            calc = _DISPATCH.get(elem.element_type)
            if not calc:
                continue
            new = calc(elem, level.level_id)
            if new:
                handled_ids.add(elem.id)
                out.extend(new)

    legacy = _quantify_all(level_list)
    for t in legacy:
        if t.item_type not in _STRUCTURAL_ITEM_TYPES:
            continue
        owner = t.item_key.split(":", 1)[0]
        if owner in handled_ids:
            continue
        out.append(t)

    return out
