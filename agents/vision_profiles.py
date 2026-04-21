"""
Perfiles de visión por disciplina: añaden un bloque de enfoque al system prompt base.

El esquema JSON detallado vive solo en `vision_agent._SIMPLE_SCHEMA_HINT` para no
duplicar ni desalinear el adaptador Python (`_simple_to_level_inventory`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from budget.discipline_mapping import (
    ELECTRICAL,
    FINISHES_ARCH,
    GENERAL,
    SANITARY,
    STRUCTURAL,
    normalize_discipline_key,
)


@dataclass(frozen=True)
class VisionPromptProfile:
    """Perfil canónico; `focus_addon` se concatena al prompt base de visión."""

    key: str
    focus_addon: str


_PROFILES: dict[str, VisionPromptProfile] = {
    GENERAL: VisionPromptProfile(
        key=GENERAL,
        focus_addon="",
    ),
    STRUCTURAL: VisionPromptProfile(
        key=STRUCTURAL,
        focus_addon=(
            "Prioriza columnas, vigas, losas, zapatas, plateas, muros de corte o cortafuego y "
            "cualquier refuerzo o sección anotada (V-, C-, L-, Z-). Las terminaciones arquitectónicas "
            "solo si ayudan a ubicar o dimensionar elementos estructurales."
        ),
    ),
    ELECTRICAL: VisionPromptProfile(
        key=ELECTRICAL,
        focus_addon=(
            "Prioriza tableros, interruptores, tomacorrientes, luminarias, datos/TV/teléfono, "
            "detectores, luminarias de emergencia y salidas especiales visibles. Cuenta cada símbolo "
            "en el arreglo `electrical` del JSON usando los tipos detallados del esquema."
        ),
    ),
    SANITARY: VisionPromptProfile(
        key=SANITARY,
        focus_addon=(
            "Prioriza puntos de agua fría/caliente, desagües, ventilaciones, registros, trampas de "
            "piso, válvulas, medidor, cisterna, bomba y artefactos. Usa `plumbing`, `wet_areas` y "
            "`fixtures` según corresponda."
        ),
    ),
    FINISHES_ARCH: VisionPromptProfile(
        key=FINISHES_ARCH,
        focus_addon=(
            "Prioriza muros (material, espesores, pañetes, cerámica), puertas, ventanas, pisos, cielos, "
            "cocinas y baños como layout de acabados (no dimensionado MEP salvo que sea visible en el plano)."
        ),
    ),
}


def get_vision_profile(profile_key: str | None) -> VisionPromptProfile:
    if not profile_key:
        return _PROFILES[GENERAL]
    k = normalize_discipline_key(profile_key)
    return _PROFILES.get(k, _PROFILES[GENERAL])
