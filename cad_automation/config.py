"""Configuracion compartida para el paquete ``cad_automation``."""

import re
from pathlib import Path
from typing import Optional

from .models import DisciplineCode, UnitSystem


DISCIPLINE_PREFIX_MAP: dict[str, DisciplineCode] = {
    "A": DisciplineCode.A,
    "S": DisciplineCode.S,
    "M": DisciplineCode.M,
    "E": DisciplineCode.E,
    "P": DisciplineCode.P,
    "C": DisciplineCode.C,
    "F": DisciplineCode.F,
    "G": DisciplineCode.G,
    "L": DisciplineCode.L,
    "T": DisciplineCode.T,
    "I": DisciplineCode.I,
    "Q": DisciplineCode.Q,
}

DISCIPLINE_ALIAS_MAP: dict[str, DisciplineCode] = {
    "AR": DisciplineCode.A,
    "ARQ": DisciplineCode.A,
    "ST": DisciplineCode.S,
    "EST": DisciplineCode.S,
    "ME": DisciplineCode.M,
    "MEC": DisciplineCode.M,
    "EL": DisciplineCode.E,
    "ELE": DisciplineCode.E,
    "PL": DisciplineCode.P,
    "PLO": DisciplineCode.P,
    "CI": DisciplineCode.C,
    "CIV": DisciplineCode.C,
    "FA": DisciplineCode.F,
    "FS": DisciplineCode.F,
    "FP": DisciplineCode.F,
    "SE": DisciplineCode.E,
    "TE": DisciplineCode.T,
    "HVAC": DisciplineCode.M,
    "SS": DisciplineCode.P,
    "SD": DisciplineCode.P,
}

COMMON_LAYERS: set[str] = {
    "0",
    "DEFPOINTS",
    "ASHADE",
}

COMMON_LAYER_PATTERNS: list[str] = [
    r"^G[-_]",
    r"^0$",
    r"^DEFPOINTS$",
    r"^BORDER",
    r"^TITLE",
    r"^VIEWPORT",
    r"^XREF",
    r"^ASHADE$",
]

UNIT_TO_MM: dict[UnitSystem, float] = {
    UnitSystem.UNITLESS: 1.0,
    UnitSystem.INCHES: 25.4,
    UnitSystem.FEET: 304.8,
    UnitSystem.MILES: 1_609_344.0,
    UnitSystem.MILLIMETERS: 1.0,
    UnitSystem.CENTIMETERS: 10.0,
    UnitSystem.METERS: 1000.0,
    UnitSystem.KILOMETERS: 1_000_000.0,
    UnitSystem.MICROINCHES: 0.0000254,
    UnitSystem.MILS: 0.0254,
    UnitSystem.YARDS: 914.4,
    UnitSystem.DECIMETERS: 100.0,
    UnitSystem.DECAMETERS: 10_000.0,
    UnitSystem.HECTOMETERS: 100_000.0,
}

INSUNITS_MAP: dict[int, UnitSystem] = {unit.value: unit for unit in UnitSystem}
TARGET_UNIT: UnitSystem = UnitSystem.MILLIMETERS

SUPPORTED_EXTENSIONS: set[str] = {".dxf", ".dwg"}
DEFAULT_OUTPUT_DIR = "cad_output"
OUTPUT_SUBDIRS: dict[str, str] = {
    "disciplines": "por_disciplina",
    "normalized": "normalizados",
    "split": "planos_separados",
    "reports": "reportes",
}

REPORT_SEPARATOR = "=" * 80
REPORT_SUBSEPARATOR = "-" * 60


def classify_layer(layer_name: str) -> DisciplineCode:
    """Clasifica una capa segun su prefijo o alias."""
    name_upper = str(layer_name).upper().strip()
    if not name_upper:
        return DisciplineCode.UNKNOWN

    if is_common_layer(name_upper):
        return DisciplineCode.G

    match = re.match(r"^([A-Z]+)[-_]", name_upper)
    if match:
        prefix = match.group(1)
        if prefix and prefix[0] in DISCIPLINE_PREFIX_MAP:
            return DISCIPLINE_PREFIX_MAP[prefix[0]]
        if prefix in DISCIPLINE_ALIAS_MAP:
            return DISCIPLINE_ALIAS_MAP[prefix]

    for alias, discipline in DISCIPLINE_ALIAS_MAP.items():
        if name_upper.startswith(alias):
            return discipline

    return DisciplineCode.UNKNOWN


def is_common_layer(layer_name: str) -> bool:
    """Indica si la capa debe incluirse como comun en todos los exports."""
    name_upper = str(layer_name).upper().strip()
    if name_upper in COMMON_LAYERS:
        return True
    return any(re.match(pattern, name_upper) for pattern in COMMON_LAYER_PATTERNS)


def get_conversion_factor(
    from_unit: UnitSystem,
    to_unit: Optional[UnitSystem] = None,
) -> float:
    """Calcula el factor multiplicador entre dos sistemas de unidades."""
    to_unit = TARGET_UNIT if to_unit is None else to_unit
    if from_unit == to_unit:
        return 1.0

    from_to_mm = UNIT_TO_MM.get(from_unit, 1.0)
    to_to_mm = UNIT_TO_MM.get(to_unit, 1.0)
    return from_to_mm / to_to_mm


def get_output_dir(source_path: Path, subdir_key: str = "disciplines") -> Path:
    """Resuelve el directorio de salida consistente para los artefactos CAD."""
    base_dir = source_path if source_path.is_dir() else source_path.parent
    output_root = base_dir / DEFAULT_OUTPUT_DIR
    subdir = OUTPUT_SUBDIRS.get(subdir_key, "")
    return output_root / subdir if subdir else output_root
