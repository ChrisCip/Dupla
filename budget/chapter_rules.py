"""
Deterministic chapter mapping and summary generation for budget composition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from core.schemas import BudgetCandidate, QuantityTakeoff

STRONG_BC3_SCORE = 0.45
STRONG_BC3_MARGIN = 0.05


@dataclass(frozen=True)
class ChapterSegment:
    code: str
    title: str


def _coerce_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item]
    return [str(value)]


def _takeoff_tags(takeoff: QuantityTakeoff) -> set[str]:
    tags = {
        tag.lower()
        for tag in [
            *_coerce_tags(takeoff.inputs.get("context_tags")),
            *_coerce_tags(takeoff.trace.metadata.get("context_tags")),
        ]
        if tag
    }
    return tags


def _material_hint(takeoff: QuantityTakeoff) -> str | None:
    value = takeoff.inputs.get("material_hint")
    if value is None:
        value = takeoff.trace.metadata.get("material_hint")
    return str(value).lower() if value else None


def select_strong_candidate(
    takeoff: QuantityTakeoff,
    candidates: Iterable[BudgetCandidate],
    *,
    min_score: float = STRONG_BC3_SCORE,
    min_margin: float = STRONG_BC3_MARGIN,
) -> BudgetCandidate | None:
    ranked = sorted(
        (candidate for candidate in candidates if candidate.takeoff_key == takeoff.item_key),
        key=lambda candidate: candidate.score,
        reverse=True,
    )
    if not ranked:
        return None

    top = ranked[0]
    second_score = ranked[1].score if len(ranked) > 1 else 0.0
    unit_matches = top.unit.lower() == takeoff.unit.lower()
    if unit_matches and top.score >= min_score and (top.score - second_score) >= min_margin:
        return top
    return None


def chapter_path_for_takeoff(takeoff: QuantityTakeoff) -> list[ChapterSegment]:
    item_type = takeoff.item_type.lower()
    tags = _takeoff_tags(takeoff)

    if item_type == "wall_length":
        return [
            ChapterSegment("02", "ALBANILERIA"),
            ChapterSegment("02.01", "MUROS Y DIVISIONES"),
        ]

    if item_type == "structural_area":
        return [
            ChapterSegment("01", "ESTRUCTURA"),
            ChapterSegment("01.04", "SUPERFICIES ESTRUCTURALES"),
        ]

    if item_type == "pres_reference_line":
        disc = str(takeoff.inputs.get("pres_discipline", "") or "").upper()
        if "HORMIGON" in disc or "HORMIG" in disc:
            return [
                ChapterSegment("01", "ESTRUCTURA"),
                ChapterSegment("01.01", "HORMIGON ARMADO"),
            ]
        if "ACERO" in disc or "REFUERZO" in disc:
            return [
                ChapterSegment("01", "ESTRUCTURA"),
                ChapterSegment("01.03", "ACERO DE REFUERZO"),
            ]
        if "MURO" in disc or "DIVISION" in disc:
            return [
                ChapterSegment("02", "ALBANILERIA"),
                ChapterSegment("02.01", "MUROS Y DIVISIONES"),
            ]
        if "SUPERFICIE" in disc or "PANET" in disc or "PAÑET" in disc or "FRAGU" in disc:
            return [
                ChapterSegment("05", "TERMINACIONES"),
                ChapterSegment("05.01", "TERMINACION DE SUPERFICIES"),
            ]
        if "PISO" in disc or "PISOS" in disc:
            return [
                ChapterSegment("05", "TERMINACIONES"),
                ChapterSegment("05.02", "TERMINACION DE PISOS"),
            ]
        if "PUERTA" in disc:
            return [
                ChapterSegment("06", "CARPINTERIAS"),
                ChapterSegment("06.01", "PUERTAS"),
            ]
        if "PINTURA" in disc:
            return [
                ChapterSegment("05", "TERMINACIONES"),
                ChapterSegment("05.05", "PINTURA"),
            ]
        if "ELECTRIC" in disc or "ELECTR" in disc:
            return [
                ChapterSegment("08", "INSTALACIONES"),
                ChapterSegment("08.01", "ELECTRICAS"),
            ]
        if "SANIT" in disc or "PLOMER" in disc:
            return [
                ChapterSegment("08", "INSTALACIONES"),
                ChapterSegment("08.02", "SANITARIAS"),
            ]
        if "ESCAL" in disc:
            return [
                ChapterSegment("05", "TERMINACIONES"),
                ChapterSegment("05.06", "ESCALERAS"),
            ]
        short = disc[:40].strip() or "PARTIDAS PRES"
        return [
            ChapterSegment("07", "REFERENCIA PRESUPUESTO REAL"),
            ChapterSegment("07.01", short),
        ]

    if item_type.endswith("_waterproofing") or "waterproofing" in tags:
        return [
            ChapterSegment("04", "IMPERMEABILIZACION"),
            ChapterSegment("04.01", "TERMINACIONES HUMEDAS"),
        ]

    if item_type in {"stair_count"}:
        return [
            ChapterSegment("05", "TERMINACIONES"),
            ChapterSegment("05.06", "ESCALERAS"),
        ]

    if item_type in {"fixture_count"}:
        return [
            ChapterSegment("08", "INSTALACIONES"),
            ChapterSegment("08.01", "ELECTRICAS"),
        ]

    if item_type in {"kitchen_count", "kitchen_area"}:
        return [
            ChapterSegment("05", "TERMINACIONES"),
            ChapterSegment("05.04", "COCINAS Y AREAS HUMEDAS"),
        ]

    if item_type.startswith(("beam_", "column_", "slab_", "structural_")):
        if "formwork" in item_type:
            return [
                ChapterSegment("01", "ESTRUCTURA"),
                ChapterSegment("01.02", "ENCOFRADOS"),
            ]
        if "reinforcement" in item_type:
            return [
                ChapterSegment("01", "ESTRUCTURA"),
                ChapterSegment("01.03", "ACERO DE REFUERZO"),
            ]
        return [
            ChapterSegment("01", "ESTRUCTURA"),
            ChapterSegment("01.01", "HORMIGON ARMADO"),
        ]

    if item_type.startswith("wall_"):
        if any(token in item_type for token in ("finish", "paint", "plaster")) or "finish" in tags:
            return [
                ChapterSegment("05", "TERMINACIONES"),
                ChapterSegment("05.01", "TERMINACION DE SUPERFICIES"),
            ]
        return [
            ChapterSegment("02", "ALBANILERIA"),
            ChapterSegment("02.01", "MUROS Y DIVISIONES"),
        ]

    if item_type.startswith("floor_"):
        if "wet_area" in tags or "waterproofing" in tags:
            return [
                ChapterSegment("04", "IMPERMEABILIZACION"),
                ChapterSegment("04.01", "TERMINACIONES HUMEDAS"),
            ]
        return [
            ChapterSegment("05", "TERMINACIONES"),
            ChapterSegment("05.02", "TERMINACION DE PISOS"),
        ]

    if item_type.startswith("ceiling_"):
        return [
            ChapterSegment("05", "TERMINACIONES"),
            ChapterSegment("05.03", "TECHOS Y CIELOS"),
        ]

    if item_type.startswith("door_"):
        return [
            ChapterSegment("06", "CARPINTERIAS"),
            ChapterSegment("06.01", "PUERTAS"),
        ]

    if item_type.startswith("window_"):
        return [
            ChapterSegment("06", "CARPINTERIAS"),
            ChapterSegment("06.02", "VENTANAS"),
        ]

    if item_type.startswith("wet_area_"):
        if "waterproofing" in item_type or "waterproofing" in tags:
            return [
                ChapterSegment("04", "IMPERMEABILIZACION"),
                ChapterSegment("04.01", "TERMINACIONES HUMEDAS"),
            ]
        return [
            ChapterSegment("05", "TERMINACIONES"),
            ChapterSegment("05.04", "TERMINACIONES HUMEDAS"),
        ]

    return [
        ChapterSegment("99", "PARTIDAS GENERALES"),
        ChapterSegment("99.01", "ITEMS POR CLASIFICAR"),
    ]


def _structural_summary(takeoff: QuantityTakeoff) -> str:
    item_type = takeoff.item_type.lower()
    material_hint = _material_hint(takeoff)

    if item_type == "beam_concrete_volume":
        return "Hormigon armado en vigas"
    if item_type == "column_concrete_volume":
        return "Hormigon armado en columnas"
    if item_type == "slab_concrete_volume":
        return "Hormigon armado en losas"
    if item_type == "beam_formwork_area_hint":
        return "Encofrado de vigas"
    if item_type == "column_formwork_area_hint":
        return "Encofrado de columnas"
    if item_type == "slab_formwork_area_hint":
        return "Encofrado inferior de losas"
    if item_type == "beam_volume":
        return "Volumen estructural de vigas"
    if item_type == "column_volume":
        return "Volumen estructural de columnas"
    if item_type == "slab_volume":
        return "Volumen estructural de losas"
    if material_hint == "concrete":
        return "Elemento estructural de hormigon"
    return "Elemento estructural"


def _wall_summary(takeoff: QuantityTakeoff) -> str:
    item_type = takeoff.item_type.lower()
    tags = _takeoff_tags(takeoff)
    material_hint = _material_hint(takeoff)

    if item_type == "wall_waterproofing":
        return "Impermeabilizacion en muros de areas humedas"
    if item_type == "wall_finish_paint":
        if "interior" in tags:
            return "Pintura en muros interiores"
        if "exterior" in tags:
            return "Pintura en muros exteriores"
        return "Pintura en muros"
    if item_type == "wall_finish_plaster":
        if "interior" in tags:
            return "Revoque en muros interiores"
        return "Revoque en muros"
    if item_type == "wall_volume":
        if material_hint == "masonry":
            return "Muro de mamposteria"
        if material_hint == "concrete":
            return "Muro de hormigon"
        return "Muro o division"
    if item_type == "wall_net_area":
        return "Muro o division"
    if item_type == "wall_area":
        return "Superficie de muros"
    if item_type == "wall_length":
        return "Longitud de muros (ml)"
    return "Trabajo en muros"


def _floor_summary(takeoff: QuantityTakeoff) -> str:
    item_type = takeoff.item_type.lower()
    tags = _takeoff_tags(takeoff)

    if item_type == "floor_waterproofing" or "waterproofing" in tags:
        return "Impermeabilizacion en pisos de areas humedas"
    if item_type == "floor_finish":
        return "Terminacion de pisos"
    return "Trabajo en pisos"


def _ceiling_summary(takeoff: QuantityTakeoff) -> str:
    item_type = takeoff.item_type.lower()
    if item_type == "ceiling_finish_paint":
        return "Pintura en cielos y techos"
    if item_type == "ceiling_area":
        return "Acabado de cielos y techos"
    return "Trabajo en cielos y techos"


def _door_summary(takeoff: QuantityTakeoff) -> str:
    item_type = takeoff.item_type.lower()
    material_hint = _material_hint(takeoff)

    if item_type == "door_leaf_wood_count":
        return "Puerta de madera"
    if item_type == "door_leaf_metal_count":
        return "Puerta metalica"
    if item_type == "door_frame_count":
        return "Marco de puerta"
    if item_type == "door_hardware_set":
        return "Juego de herrajes para puerta"
    if material_hint == "wood":
        return "Puerta de madera"
    if material_hint == "steel":
        return "Puerta metalica"
    return "Puerta"


def _window_summary(takeoff: QuantityTakeoff) -> str:
    item_type = takeoff.item_type.lower()
    if item_type == "window_installation_count":
        return "Colocacion de ventanas"
    if item_type == "window_sealant_area":
        return "Sellado y tratamiento de ventanas"
    return "Ventanas"


def _wet_area_summary(takeoff: QuantityTakeoff) -> str:
    item_type = takeoff.item_type.lower()
    if "waterproofing" in item_type:
        return "Impermeabilizacion en areas humedas"
    if "finish" in item_type:
        return "Terminaciones en areas humedas"
    return "Area humeda"


def build_budget_summary(
    takeoff: QuantityTakeoff,
    candidate: BudgetCandidate | None = None,
) -> str:
    if candidate is not None:
        return candidate.summary.strip() or takeoff.item_type.replace("_", " ").strip()

    item_type = takeoff.item_type.lower()
    if item_type == "pres_reference_line":
        summary = str(takeoff.inputs.get("pres_summary", "") or "").strip()
        return summary or takeoff.item_key
    if item_type == "structural_area":
        return "Superficie estructural (referencia)"

    if item_type.startswith(("beam_", "column_", "slab_", "structural_")):
        return _structural_summary(takeoff)
    if item_type.startswith("wall_"):
        return _wall_summary(takeoff)
    if item_type.startswith("floor_"):
        return _floor_summary(takeoff)
    if item_type.startswith("ceiling_"):
        return _ceiling_summary(takeoff)
    if item_type.startswith("door_"):
        return _door_summary(takeoff)
    if item_type.startswith("window_"):
        return _window_summary(takeoff)
    if item_type.startswith("wet_area_"):
        return _wet_area_summary(takeoff)

    return takeoff.item_type.replace("_", " ").strip().capitalize()
