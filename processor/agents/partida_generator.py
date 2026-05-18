"""
GPT-4o partida generator: creates project-specific budget line descriptions
from quantity takeoffs.

BC3 and PRES are used as few-shot formatting references only — not as a lookup
catalog. Every partida description is specific to this project.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from core.schemas import QuantityTakeoff, QuantityTrace
from knowledge.training_data import TrainingPair

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger("dupla.partida_generator")

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ---------------------------------------------------------------------------
# Chapter catalog — 24 chapters across 4 disciplines
# Maps chapter_code -> (chapter_name, discipline)
# ---------------------------------------------------------------------------

CHAPTER_CATALOG: dict[str, tuple[str, str]] = {
    "01": ("MOVIMIENTO DE TIERRAS Y FUNDACIONES", "estructural"),
    "02": ("HORMIGON ARMADO - COLUMNAS Y VIGAS", "estructural"),
    "03": ("HORMIGON ARMADO - LOSAS Y ENTREPISO", "estructural"),
    "04": ("ACERO DE REFUERZO", "estructural"),
    "05": ("ENCOFRADOS", "estructural"),
    "06": ("MUROS Y DIVISIONES", "arquitectura"),
    "07": ("PANETE Y REVESTIMIENTO DE MUROS", "arquitectura"),
    "08": ("PISOS Y CERAMICA", "arquitectura"),
    "09": ("CIELOS Y TECHOS", "arquitectura"),
    "10": ("PUERTAS Y MARCOS", "arquitectura"),
    "11": ("VENTANAS Y FACHADA", "arquitectura"),
    "12": ("PINTURA INTERIOR Y EXTERIOR", "arquitectura"),
    "13": ("IMPERMEABILIZACION", "arquitectura"),
    "14": ("ESCALERAS Y BARANDAS", "arquitectura"),
    "15": ("GABINETES Y COCINAS", "arquitectura"),
    "16": ("OBRAS EXTERIORES Y PAISAJISMO", "arquitectura"),
    "17": ("INSTALACIONES SANITARIAS - AGUA FRIA", "sanitario"),
    "18": ("INSTALACIONES SANITARIAS - AGUAS NEGRAS", "sanitario"),
    "19": ("PIEZAS SANITARIAS Y ACCESORIOS", "sanitario"),
    "20": ("CISTERNA Y SISTEMA DE BOMBEO", "sanitario"),
    "21": ("INSTALACIONES ELECTRICAS - DISTRIBUCION", "electrico"),
    "22": ("TABLEROS Y PROTECCIONES", "electrico"),
    "23": ("LUMINARIAS Y TOMACORRIENTES", "electrico"),
    "24": ("GASTOS GENERALES E INDIRECTOS", "arquitectura"),
}

# item_type -> default chapter_code
_ITEM_TYPE_TO_CHAPTER: dict[str, str] = {
    # Estructural — fundaciones
    "footing_concrete_volume": "01",
    "footing_volume": "01",
    "footing_area": "01",
    "footing_perimeter": "01",
    # Estructural — columnas/vigas
    "column_concrete_volume": "02",
    "column_volume": "02",
    "beam_concrete_volume": "02",
    "beam_volume": "02",
    "structural_concrete_volume": "02",
    "structural_volume": "02",
    "structural_count": "02",
    "structural_area": "02",
    "structural_length": "02",
    # Estructural — losas
    "slab_concrete_volume": "03",
    "slab_volume": "03",
    "slab_area": "03",
    # Acero de refuerzo
    "footing_reinforcement_kg": "04",
    "beam_reinforcement_kg": "04",
    "column_reinforcement_kg": "04",
    "slab_reinforcement_kg": "04",
    "reinforcement_kg": "04",
    # Encofrado
    "footing_formwork_area_hint": "05",
    "beam_formwork_area_hint": "05",
    "column_formwork_area_hint": "05",
    "slab_formwork_area_hint": "05",
    "formwork_area": "05",
    # Arquitectura — muros
    "wall_net_area": "06",
    "wall_gross_area": "06",
    "wall_volume": "06",
    "wall_length": "06",
    # Arquitectura — panete/acabados muros
    "wall_finish_plaster": "07",
    "wall_finish_tile": "07",
    "wall_finish_stucco": "07",
    # Arquitectura — pisos
    "floor_area": "08",
    "floor_finish": "08",
    "floor_tile_area": "08",
    "floor_epoxy_area": "08",
    # Arquitectura — cielos
    "ceiling_area": "09",
    "ceiling_finish": "09",
    # Arquitectura — puertas
    "door_count": "10",
    "door_leaf_wood_count": "10",
    "door_frame_count": "10",
    # Arquitectura — ventanas
    "window_count": "11",
    "window_frame_count": "11",
    "window_glazing_area": "11",
    "window_area": "11",
    # Arquitectura — pintura
    "wall_finish_paint": "12",
    "ceiling_finish_paint": "12",
    "paint_area": "12",
    # Arquitectura — impermeabilización
    "floor_waterproofing": "13",
    "wall_waterproofing": "13",
    "waterproofing_area": "13",
    # Arquitectura — escaleras
    "stair_count": "14",
    "stair_area": "14",
    "stair_railing_length": "14",
    # Arquitectura — gabinetes
    "kitchen_count": "15",
    "kitchen_area": "15",
    "cabinet_count": "15",
    # Sanitario — piezas sanitarias
    "wet_area_fixture_count": "19",
    "fixture_count_plumbing": "19",
    # Eléctrico
    "fixture_count_electrical": "23",
}

# Prefix fallback table (checked in order when item_type not in _ITEM_TYPE_TO_CHAPTER)
_PREFIX_TABLE: list[tuple[str, str]] = [
    ("footing_", "01"),
    ("beam_", "02"),
    ("column_", "02"),
    ("slab_", "03"),
    ("structural_", "02"),
    ("reinforcement_", "04"),
    ("formwork_", "05"),
    ("wall_finish_paint", "12"),
    ("wall_finish_", "07"),
    ("wall_", "06"),
    ("floor_waterproof", "13"),
    ("floor_", "08"),
    ("ceiling_finish_paint", "12"),
    ("ceiling_", "09"),
    ("door_", "10"),
    ("window_", "11"),
    ("paint_", "12"),
    ("waterproof_", "13"),
    ("stair_", "14"),
    ("kitchen_", "15"),
    ("cabinet_", "15"),
    ("wet_area_", "19"),
]

BATCH_SIZE = 45  # takeoffs per GPT-4o call
_MODEL = "gpt-4o"
_TEMPERATURE = 0.2

_SYSTEM_PROMPT = """\
Eres un presupuestista dominicano senior especializado en proyectos residenciales
y comerciales en República Dominicana (zona Punta Cana).

Tu tarea: dado un lote de mediciones (takeoffs) de un proyecto de construcción,
genera una partida presupuestaria específica y detallada para CADA medición.

REGLAS ABSOLUTAS:
1. Describe el trabajo REAL del proyecto, no categorías genéricas.
   MAL: "Hormigon armado"
   BIEN: "Hormigon armado f'c=280kg/cm2 en vigas V1 (0.25x0.45m) nivel 2"
2. La descripcion debe incluir especificaciones técnicas cuando el takeoff las
   proporciona (dimensiones, resistencia del concreto, tipo de bloque, acabado, etc.).
3. La unidad DEBE coincidir exactamente con la unidad del takeoff de entrada.
4. El chapter_code y chapter_name deben tomarse del capitulo asignado al lote.
5. El partida_code se forma como: {chapter_code}.{orden_dentro_capitulo:03d}
   Ejemplo: primer item del cap 06 = "06.001", segundo = "06.002"
6. Devuelve SOLO un JSON array, sin texto adicional, sin bloques de codigo.
7. El campo source_takeoff_key debe ser el item_key exacto del takeoff de entrada.
8. Genera EXACTAMENTE una partida por takeoff recibido, usando el mismo orden.\
"""


def _infer_discipline(takeoff: QuantityTakeoff) -> str:
    """Return one of: arquitectura | estructural | sanitario | electrico."""
    stamped = str(takeoff.trace.metadata.get("source_discipline") or "").strip()
    _alias: dict[str, str] = {
        "arquitectonica": "arquitectura",
        "arquitectura": "arquitectura",
        "estructural": "estructural",
        "estructura": "estructural",
        "electrica": "electrico",
        "electrico": "electrico",
        "sanitaria": "sanitario",
        "sanitario": "sanitario",
    }
    if stamped in _alias:
        return _alias[stamped]

    it = takeoff.item_type.lower()
    if it.startswith(("beam_", "column_", "slab_", "footing_", "structural_", "reinforcement_", "formwork_")):
        return "estructural"
    if it == "wet_area_fixture_count" or "plumbing" in str(takeoff.inputs.get("discipline") or "").lower():
        return "sanitario"
    if it == "fixture_count":
        disc = str(takeoff.inputs.get("discipline") or "").lower()
        if disc in ("plumbing", "sanitaria", "sanitario"):
            return "sanitario"
        return "electrico"
    return "arquitectura"


def _assign_chapter(takeoff: QuantityTakeoff) -> str:
    """Return chapter_code from the 24-chapter catalog."""
    it = takeoff.item_type.lower()

    # Special branching for fixture_count based on inputs.discipline
    if it == "fixture_count":
        disc = str(takeoff.inputs.get("discipline") or "").lower()
        if disc in ("plumbing", "sanitaria", "sanitario"):
            return "19"
        return "23"

    if it in _ITEM_TYPE_TO_CHAPTER:
        return _ITEM_TYPE_TO_CHAPTER[it]

    for prefix, ch in _PREFIX_TABLE:
        if it.startswith(prefix):
            return ch

    return "24"  # catch-all: gastos generales


def _build_few_shot_block(
    training_pairs: list[TrainingPair],
    discipline: str,
    max_examples: int = 6,
) -> str:
    """Pick real PRES examples matching the discipline and format as few-shot text."""
    _disc_kw: dict[str, set[str]] = {
        "estructural": {"hormig", "viga", "colum", "losa", "zapata", "acero", "encof", "fundam"},
        "arquitectura": {"muro", "panete", "piso", "puerta", "pintura", "ventana", "bloque", "cielo", "pared"},
        "sanitario": {"sanitar", "tuberia", "inodor", "lavam", "ducha", "drenaj", "agua", "plomer"},
        "electrico": {"electr", "tomacorr", "interrup", "luminaria", "panel", "switch", "circuito"},
    }
    keywords = _disc_kw.get(discipline, set())

    def _matches(pair: TrainingPair) -> bool:
        desc = pair.output_description.lower()
        return any(kw in desc for kw in keywords)

    filtered = [p for p in training_pairs if _matches(p)][:max_examples]
    if not filtered:
        filtered = training_pairs[:max_examples]

    if not filtered:
        return ""

    lines = ["EJEMPLOS DE PARTIDAS REALES (solo para formato y nivel de detalle):"]
    for p in filtered:
        lines.append(
            f'- "{p.output_description}" | Ud: {p.output_unit} | Precio ref: RD${p.output_price:.0f}'
        )
    return "\n".join(lines)


def _extract_json_list(text: str) -> list[dict[str, Any]]:
    """Extract a JSON array from GPT-4o text output (copied from classifier_agent)."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "items" in parsed:
            return list(parsed["items"])
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            cleaned = re.sub(r",\s*([}\]])", r"\1", text[start : end + 1])
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

    return []


class PartidaGenerator:
    """
    Generates project-specific budget partidas from quantity takeoffs using GPT-4o.

    Groups takeoffs by chapter, batches them, calls GPT-4o once per batch, and
    returns a flat list of partida dicts that the adapter converts to BudgetCandidates.
    """

    def __init__(self) -> None:
        if not HAS_OPENAI:
            raise ImportError("openai package is required for PartidaGenerator")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self._client = OpenAI(api_key=api_key)

    def generate(
        self,
        takeoffs: list[QuantityTakeoff],
        training_pairs: list[TrainingPair] | None = None,
        bc3_catalog: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Main entry point.

        Groups takeoffs by chapter_code, batches at BATCH_SIZE, calls GPT-4o
        per batch, and returns a flat list of generated partida dicts.

        pres_reference_line takeoffs are skipped (they already have descriptions).
        """
        non_pres = [t for t in takeoffs if t.item_type != "pres_reference_line"]
        if not non_pres:
            return []

        # Group by chapter_code
        groups: dict[str, list[QuantityTakeoff]] = {}
        for t in non_pres:
            ch = _assign_chapter(t)
            groups.setdefault(ch, []).append(t)

        results: list[dict[str, Any]] = []
        chapter_offsets: dict[str, int] = {}

        for chapter_code in sorted(groups.keys()):
            chapter_takeoffs = groups[chapter_code]
            chapter_name, discipline = CHAPTER_CATALOG.get(
                chapter_code, ("PARTIDAS GENERALES", "arquitectura")
            )
            few_shot = _build_few_shot_block(training_pairs or [], discipline)

            for batch_start in range(0, len(chapter_takeoffs), BATCH_SIZE):
                batch = chapter_takeoffs[batch_start : batch_start + BATCH_SIZE]
                offset = chapter_offsets.get(chapter_code, 0)

                partidas = self._generate_batch(
                    batch,
                    chapter_code=chapter_code,
                    chapter_name=chapter_name,
                    discipline=discipline,
                    few_shot_block=few_shot,
                    partida_offset=offset,
                )
                chapter_offsets[chapter_code] = offset + len(partidas)
                results.extend(partidas)

        logger.info(
            "PartidaGenerator: %d takeoffs -> %d partidas generated",
            len(non_pres),
            len(results),
        )
        return results

    def _generate_batch(
        self,
        takeoffs: list[QuantityTakeoff],
        *,
        chapter_code: str,
        chapter_name: str,
        discipline: str,
        few_shot_block: str,
        partida_offset: int,
    ) -> list[dict[str, Any]]:
        """Single GPT-4o call for one batch within a chapter."""
        takeoff_payload: list[dict[str, Any]] = []
        for t in takeoffs:
            item: dict[str, Any] = {
                "key": t.item_key,
                "type": t.item_type,
                "unit": t.unit,
                "qty": round(float(t.quantity), 3),
            }
            desc = str(t.inputs.get("takeoff_description") or "").strip()
            if desc:
                item["desc"] = desc[:800]
            level = str(t.level_id or "").strip()
            if level:
                item["level"] = level
            takeoff_payload.append(item)

        catalog_block = "\n".join(
            f"  {code}: {name} (disciplina: {disc})"
            for code, (name, disc) in CHAPTER_CATALOG.items()
        )

        start_num = partida_offset + 1
        user_prompt = (
            f"CAPITULO ASIGNADO: {chapter_code} - {chapter_name} (disciplina: {discipline})\n\n"
            f"CATALOGO DE CAPITULOS DISPONIBLES:\n{catalog_block}\n\n"
        )
        if few_shot_block:
            user_prompt += f"{few_shot_block}\n\n"

        user_prompt += (
            f"NUMERACION: los partida_code para este lote empiezan en "
            f"{chapter_code}.{start_num:03d}\n\n"
            f"TAKEOFFS A CONVERTIR EN PARTIDAS ({len(takeoffs)} items):\n"
            + json.dumps(takeoff_payload, ensure_ascii=False, indent=2)
            + "\n\nDevuelve SOLO el JSON array de partidas. "
            "Formato de cada elemento:\n"
            '{"chapter_code":"XX","chapter_name":"...","discipline":"...",'
            '"partida_code":"XX.NNN","partida_description":"...","unit":"...",'
            '"quantity":0.0,"source_takeoff_key":"..."}'
        )

        try:
            resp = self._client.chat.completions.create(
                model=_MODEL,
                max_tokens=4000,
                temperature=_TEMPERATURE,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = resp.choices[0].message.content or ""
        except Exception:
            logger.warning(
                "PartidaGenerator batch failed (chapter=%s, %d takeoffs)",
                chapter_code,
                len(takeoffs),
                exc_info=True,
            )
            return []

        partidas = _extract_json_list(raw)
        if not partidas:
            logger.warning(
                "PartidaGenerator: empty JSON from GPT-4o for chapter %s", chapter_code
            )
        return partidas
