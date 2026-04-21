"""
Vision agent for normalized building inventory extraction.

Two-step approach:
1. GPT-4o Vision returns a simple flat count of visible elements.
2. Python adapter converts that simple inventory to the full LevelInventory schema.

This avoids asking GPT-4o to fill a complex 15-field schema, which causes it to
return mostly null/empty data. The simpler prompt produces useful counts.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .vision_profiles import get_vision_profile
from core.schemas import LevelInventory, level_inventory_from_dict

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger("dupla.vision")

try:
    from openai import OpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def get_client() -> "OpenAI":
    if not HAS_OPENAI:
        raise ImportError("openai is not installed. Run: pip install -r requirements.txt")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured in the project .env file.")
    return OpenAI(api_key=api_key)


def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as handle:
        return base64.b64encode(handle.read()).decode("utf-8")


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    import re

    fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    if start >= 0:
        depth = 0
        for index in range(start, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : index + 1])
                    except json.JSONDecodeError:
                        break

    return {"raw_text": text, "parse_error": True}


# ---------------------------------------------------------------------------
# Step 1: Simple prompt — GPT-4o counts visible elements
# ---------------------------------------------------------------------------

_MAX_OFFICE_METHODOLOGY_CHARS = 12000


_SIMPLE_SYSTEM_PROMPT = """Eres un ingeniero presupuestista senior dominicano con 20+ años de experiencia en cuantificación de obras.
Analizas planos de construcción (plantas, cortes, elevaciones, detalles) para extraer TODOS los elementos constructivos con sus dimensiones exactas para presupuesto.

Si el usuario incluye un bloque "METODOLOGÍA DE OFICINA", aplícalo como criterio de prioridad para
interpretar notaciones y desgloses, sin contradecir el formato JSON ni inventar cantidades no visibles.

REGLAS OBLIGATORIAS:
1. BUSCA ACTIVAMENTE en toda la imagen: cuadros de resumen, leyendas, notaciones, cotas, secciones anotadas, detalles constructivos.
2. NO devuelvas null si el dato es visible o deducible. Si ves "V-1 0.30x0.60" eso son section_width_m=0.30 y section_height_m=0.60.
3. Si ves "B-6" o "bloque 6" = espesor 0.15m (6 pulgadas). "B-8" = 0.20m. "B-4" = 0.10m.
4. Notaciones tipo "e=0.20" o "esp. 0.15" = espesor en metros.
5. Si ves cotas entre líneas de nivel (NPT+0.00, NPT+2.80) = altura de entrepiso.
6. CADA tipo diferente de elemento va en una entrada separada. No agrupes bloques de 6 con bloques de 8.
7. Extrae ABSOLUTAMENTE TODO lo visible: estructura, albañilería, acabados, instalaciones eléctricas, sanitarias, carpintería.
8. Para baños: cuenta CADA pieza sanitaria (inodoro, lavamanos, ducha, bañera, bidet, gabinete).
9. Para cocinas: identifica gabinetes, fregaderos, conexiones de gas si son visibles.
10. Para instalaciones eléctricas: tomacorrientes, interruptores, luminarias, paneles, salidas especiales.
11. Para instalaciones sanitarias: tuberías visibles, registros, trampas, válvulas, puntos de agua.
12. Identifica el TIPO DE PLANO: arquitectónico, estructural, eléctrico, sanitario, corte, elevación, detalle.

Return ONLY valid JSON — no markdown, no explanation, no text."""

_SIMPLE_SCHEMA_HINT = """{
  "plan_type": "architectural|structural|electrical|plumbing|section|elevation|detail|site|combined",
  "floor_area_m2": <number or null>,
  "ceiling_height_m": <number or null>,
  "floor_to_floor_height_m": <number or null>,
  "walls": [
    {"id": "descriptive label (e.g. muro_ext_bloque8, muro_int_bloque6, muro_concreto)",
     "material": "block_6in|block_8in|block_4in|concrete|drywall|wood|other",
     "location": "interior|exterior",
     "estimated_length_m": <number>,
     "estimated_area_m2": <number or null>,
     "height_m": <number or null>,
     "thickness_m": <number>,
     "finish_interior": "plaster|ceramic_tile|paint|none|null",
     "finish_exterior": "plaster|ceramic_tile|paint|exposed|none|null",
     "structural": true/false,
     "count_segments": <integer>}
  ],
  "doors": [
    {"id": "descriptive (e.g. puerta_principal, puerta_interior_madera)",
     "type": "main_entry|interior|service|bathroom|closet|garage|sliding|folding|other",
     "material": "wood|metal|aluminum|pvc|glass|other",
     "count": <integer>,
     "width_m": <number or null>,
     "height_m": <number or null>,
     "includes_frame": true/false,
     "includes_hardware": true/false}
  ],
  "windows": [
    {"id": "descriptive (e.g. ventana_corrediza_aluminio)",
     "type": "sliding|fixed|casement|jalousie|louver|awning|other",
     "material": "aluminum|wood|pvc|steel|other",
     "glazing": "clear|tinted|frosted|double|other",
     "count": <integer>,
     "width_m": <number or null>,
     "height_m": <number or null>}
  ],
  "wet_areas": [
    {"id": "descriptive (e.g. bano_principal, bano_servicio, lavanderia)",
     "kind": "full_bathroom|half_bathroom|service_bathroom|laundry|utility",
     "count": <integer>,
     "area_m2": <number or null>,
     "has_shower": true/false,
     "has_bathtub": true/false,
     "has_toilet": true/false,
     "has_sink": true/false,
     "has_bidet": true/false,
     "has_cabinet": true/false,
     "floor_finish": "ceramic|porcelain|other|null",
     "wall_finish": "ceramic|porcelain|paint|other|null",
     "waterproofing_required": true/false}
  ],
  "kitchens": [
    {"id": "descriptive",
     "count": <integer>,
     "area_m2": <number or null>,
     "has_upper_cabinets": true/false,
     "has_lower_cabinets": true/false,
     "has_countertop": true/false,
     "countertop_material": "granite|marble|quartz|other|null",
     "has_sink": true/false,
     "has_gas_connection": true/false,
     "floor_finish": "ceramic|porcelain|other|null",
     "wall_finish": "ceramic|porcelain|paint|other|null"}
  ],
  "stairs": [
    {"id": "descriptive",
     "count": <integer>,
     "flights": <integer or null>,
     "steps_per_flight": <integer or null>,
     "width_m": <number or null>,
     "material": "concrete|steel|wood|other",
     "has_railing": true/false,
     "railing_material": "metal|wood|glass|other|null"}
  ],
  "structural_elements": [
    {"id": "notation if visible (e.g. V-1, C-1, L-1, Z-1) or descriptive",
     "type": "column|beam|slab|footing|shear_wall|lintel|tie_beam",
     "count": <integer>,
     "section_width_m": <number or null>,
     "section_height_m": <number or null>,
     "length_m": <number or null>,
     "area_m2": <number or null>,
     "span_m": <number or null>,
     "material": "concrete|steel|masonry|other",
     "concrete_grade": "fc_210|fc_250|fc_280|null",
     "has_reinforcement": true}
  ],
  "floor_finishes": [
    {"id": "descriptive (e.g. piso_porcelanato_sala, piso_ceramica_bano)",
     "type": "ceramic|porcelain|marble|granite|vinyl|concrete_polished|terrazo|other",
     "area_m2": <number or null>,
     "location": "description of where"}
  ],
  "ceiling_finishes": [
    {"id": "descriptive",
     "type": "plaster|drywall|exposed|suspended|wood|other",
     "area_m2": <number or null>,
     "location": "description"}
  ],
  "electrical": [
    {"id": "descriptive",
     "type": "outlet_110v|outlet_220v|switch_single|switch_double|switch_triple|switch_dimmer|luminaire_ceiling|luminaire_wall|luminaire_recessed|panel_breaker|intercom|doorbell|data_outlet|tv_outlet|phone_outlet|smoke_detector|emergency_light|fan_connection|ac_connection|other",
     "count": <integer>,
     "location": "description or null"}
  ],
  "plumbing": [
    {"id": "descriptive",
     "type": "water_supply_point|drain_point|vent_pipe|cleanout|floor_drain|water_heater_connection|washing_machine_connection|hose_bib|valve|water_meter|cistern|pump|other",
     "count": <integer>,
     "pipe_diameter_in": <number or null>,
     "material": "pvc|cpvc|copper|galvanized|other|null",
     "location": "description or null"}
  ],
  "fixtures": [
    {"id": "descriptive",
     "type": "toilet|sink|shower_base|bathtub|bidet|urinal|laundry_sink|kitchen_sink|water_heater|pump|other",
     "count": <integer>,
     "brand_or_quality": "standard|premium|economy|null"}
  ],
  "exterior_works": [
    {"id": "descriptive",
     "type": "sidewalk|driveway|garden_wall|fence|gate|parking_area|ramp|retaining_wall|drainage_channel|other",
     "quantity": <number or null>,
     "unit": "m2|m|unit",
     "material": "description or null"}
  ],
  "annotations_and_notes": [
    {"text": "exact text visible", "interpretation": "what it means for quantification"}
  ]
}"""


def _compose_vision_system_prompt(vision_profile_key: str | None) -> tuple[str, str]:
    """
    Prompt de sistema = base (metodología + reglas RD) + foco opcional por disciplina.
    El JSON pedido al modelo sigue siendo siempre `_SIMPLE_SCHEMA_HINT` para alinear el adaptador.
    """
    profile = get_vision_profile(vision_profile_key)
    base = _SIMPLE_SYSTEM_PROMPT.strip()
    addon = (profile.focus_addon or "").strip()
    if not addon:
        return base, profile.key
    return (
        f"{base}\n\nENFOQUE POR DISCIPLINA ({profile.key}):\n{addon}",
        profile.key,
    )


def _detect_view_type(image_path: Path) -> str:
    name = image_path.name.lower()
    if "elev" in name or "fach" in name or "alzado" in name:
        return "elevation"
    if "sitio" in name or "emplaza" in name or "site" in name:
        return "site"
    if "planta" in name or "floor" in name or "page" in name:
        return "plan"
    return "unknown"


def format_cad_facts_for_prompt(cad_summary: dict[str, Any]) -> str:
    if not cad_summary:
        return "No CAD facts were provided."

    cad_facts = cad_summary.get("cad_facts", {})
    inventory_hints = cad_summary.get("inventory_hints", {})
    lines: list[str] = []

    layer_names = inventory_hints.get("layer_names", [])
    if layer_names:
        lines.append("Layer names:")
        lines.extend(f"- {layer_name}" for layer_name in layer_names[:40])

    dimensions = inventory_hints.get("scale_dimensions", [])
    if dimensions:
        lines.append("Scale and dimension hints:")
        for item in dimensions[:12]:
            lines.append(
                f"- layer={item.get('layer')} measurement={item.get('measurement')} text={item.get('text')}"
            )

    block_frequency = inventory_hints.get("block_frequency", [])
    if block_frequency:
        lines.append("Block frequency hints:")
        for item in block_frequency[:12]:
            lines.append(f"- {item.get('block_name')}: {item.get('count')}")

    hatches = cad_facts.get("hatches", [])
    if hatches:
        lines.append("Hatch hints:")
        for hatch in hatches[:10]:
            lines.append(
                f"- layer={hatch.get('layer')} area={hatch.get('area')} pattern={hatch.get('pattern_name')}"
            )

    texts = cad_facts.get("texts", [])
    if texts:
        lines.append("Text markers:")
        for text in texts[:12]:
            lines.append(f"- layer={text.get('layer')} content={text.get('content')}")

    return "\n".join(lines)


def _build_simple_user_prompt(
    image_path: Path,
    level_name: str,
    cad_summary: dict[str, Any],
    *,
    office_methodology: str | None = None,
) -> str:
    view_type = _detect_view_type(image_path)
    cad_hints = format_cad_facts_for_prompt(cad_summary)
    methodology_block = ""
    if office_methodology and office_methodology.strip():
        trimmed = office_methodology.strip()
        if len(trimmed) > _MAX_OFFICE_METHODOLOGY_CHARS:
            logger.warning(
                "Office methodology truncated: %d → %d chars",
                len(trimmed),
                _MAX_OFFICE_METHODOLOGY_CHARS,
            )
            trimmed = trimmed[:_MAX_OFFICE_METHODOLOGY_CHARS] + "\n\n[... texto truncado por límite ...]"
        methodology_block = f"""METODOLOGÍA DE OFICINA (criterio del presupuestista — prioridad al interpretar notas y desgloses):
{trimmed}

---

"""

    return f"""ANALIZA este plano ({view_type}) del nivel: {level_name}

{methodology_block}DATOS DEL CAD (úsalos para verificar y complementar lo que ves):
{cad_hints}

INSTRUCCIONES DE EXTRACCIÓN EXHAUSTIVA:

1. ESTRUCTURA: Busca cuadros de columnas/vigas/zapatas/losas. Lee CADA notación 
   (V-1, C-1, Z-1, L-1) con su sección (ancho x alto). Si ves "0.30x0.60" cerca 
   de una viga, esa es la sección. Cuenta CADA elemento individualmente.

2. MUROS: Diferencia CADA tipo: bloque 6" (B-6, 0.15m), bloque 8" (B-8, 0.20m), 
   concreto armado (muro cortante), drywall. Mide longitudes de las cotas o estima 
   por escala. Indica interior/exterior.

3. ACABADOS DE MUROS: Si ves notas de "pañete", "empañete", "fraguache", "repello" = 
   plaster. Si ves "cerámica" o "azulejo" = ceramic_tile. Indica ambas caras si aplica.

4. PUERTAS: CADA tipo por separado (principal, interiores, baño, servicio, closet). 
   Lee dimensiones de las cotas (ancho x alto). Material si visible.

5. VENTANAS: CADA tipo (corrediza, fija, celosía, proyectante). Dimensiones de cotas.

6. BAÑOS: Para CADA baño cuenta: inodoro, lavamanos, ducha/tina, gabinete, espejo, 
   accesorios. Nota acabados (cerámica piso, cerámica pared, pintura).

7. COCINA: Gabinetes superiores e inferiores, tope, fregadero, conexión gas.

8. PISOS: Tipo de acabado por zona (porcelanato sala, cerámica baño, etc.). Área si 
   hay cotas.

9. CIELOS: Tipo (yeso, suspendido, expuesto) por zona.

10. ELÉCTRICO: Cuenta CADA punto: tomacorrientes 110V, 220V, interruptores (sencillo, 
    doble, triple), luminarias (techo, pared, empotradas), salidas de datos, TV, 
    teléfono, panel de breakers, timbres, detectores de humo, abanicos, A/C.

11. SANITARIO/PLOMERÍA: Puntos de agua, desagües, ventilaciones, registros, válvulas, 
    conexión calentador, conexión lavadora, llaves de paso, medidor, cisterna, bomba.

12. ESCALERAS: Tipo, material, ancho, número de peldaños, barandas.

13. EXTERIORES: Aceras, rampas, muros de contención, cercas, portones, estacionamiento.

14. ANOTACIONES: Lee TODAS las notas y textos relevantes del plano. Interpreta su 
    significado para cuantificación.

Devuelve este JSON EXACTO (sin texto adicional):
{_SIMPLE_SCHEMA_HINT}"""


# ---------------------------------------------------------------------------
# Step 2: Python adapter — simple dict → LevelInventory-compatible dict
# ---------------------------------------------------------------------------

def _simple_to_level_inventory(
    simple: dict[str, Any],
    level_name: str,
    level_id: str,
    image_name: str,
) -> dict[str, Any]:
    """Convert GPT-4o simple inventory output to a LevelInventory-compatible dict."""

    _BLOCK_THICKNESS: dict[str, float] = {
        "block_6in": 0.15, "block_8in": 0.20, "block_4in": 0.10,
    }

    walls: list[dict[str, Any]] = []
    for i, w in enumerate(simple.get("walls") or [], 1):
        raw_material = w.get("material") or "other"
        thickness = w.get("thickness_m")
        if thickness is None:
            thickness = _BLOCK_THICKNESS.get(raw_material)

        material_hint = raw_material
        if raw_material.startswith("block_"):
            material_hint = "masonry"

        wall_system = None
        if raw_material.startswith("block_"):
            wall_system = "masonry_wall"
        elif raw_material == "concrete":
            wall_system = "concrete_wall"
        elif raw_material == "drywall":
            wall_system = "drywall_partition"

        wall_id = w.get("id") or f"vis-wall-{i:02d}"
        walls.append(
            {
                "id": wall_id,
                "source": "vision",
                "source_layers": [],
                "source_refs": [f"vision:{image_name}:wall_{i}"],
                "assumptions": ["Dimensions extracted from plan analysis."],
                "inputs": {
                    "raw": w,
                    "finish_interior": w.get("finish_interior"),
                    "finish_exterior": w.get("finish_exterior"),
                    "original_material_code": raw_material,
                },
                "conflict_notes": [],
                "length_m": w.get("estimated_length_m"),
                "height_m": w.get("height_m"),
                "thickness_m": thickness,
                "area_m2": w.get("estimated_area_m2"),
                "material_hint": material_hint,
                "wall_system": wall_system,
                "interior_exterior_hint": (
                    w.get("location") if w.get("location") in {"interior", "exterior"} else None
                ),
                "structural": w.get("structural") or False,
                "finish_required": True,
                "confidence": 0.70,
                "evidence": [
                    f"Wall identified: material={raw_material}, location={w.get('location')}, "
                    f"thickness={thickness}m, length={w.get('estimated_length_m')}m."
                ],
            }
        )

    doors: list[dict[str, Any]] = []
    for i, d in enumerate(simple.get("doors") or [], 1):
        count = d.get("count")
        doors.append(
            {
                "id": f"vis-door-{i:02d}",
                "source": "vision",
                "source_layers": [],
                "source_refs": [f"vision:{image_name}:door_{i}"],
                "assumptions": [],
                "inputs": {"raw": d},
                "conflict_notes": [],
                "count": int(count) if count is not None else 1,
                "width_m": d.get("width_m"),
                "height_m": d.get("height_m"),
                "type_hint": d.get("type"),
                "confidence": 0.70,
                "evidence": [
                    f"Counted from plan image: type={d.get('type')}, count={d.get('count')}."
                ],
            }
        )

    windows: list[dict[str, Any]] = []
    for i, w in enumerate(simple.get("windows") or [], 1):
        count = w.get("count")
        windows.append(
            {
                "id": f"vis-window-{i:02d}",
                "source": "vision",
                "source_layers": [],
                "source_refs": [f"vision:{image_name}:window_{i}"],
                "assumptions": [],
                "inputs": {"raw": w},
                "conflict_notes": [],
                "count": int(count) if count is not None else 1,
                "width_m": w.get("width_m"),
                "height_m": w.get("height_m"),
                "type_hint": w.get("type"),
                "confidence": 0.70,
                "evidence": [
                    f"Counted from plan image: type={w.get('type')}, count={w.get('count')}."
                ],
            }
        )

    wet_areas: list[dict[str, Any]] = []
    for i, a in enumerate(simple.get("wet_areas") or [], 1):
        count = a.get("count")
        wet_areas.append(
            {
                "id": f"vis-wetarea-{i:02d}",
                "source": "vision",
                "source_refs": [f"vision:{image_name}:wetarea_{i}"],
                "assumptions": [],
                "inputs": {"raw": a},
                "conflict_notes": [],
                "kind": a.get("kind") or "bathroom",
                "count": int(count) if count is not None else 1,
                "estimated_area_m2": a.get("area_m2"),
                "confidence": 0.65,
                "evidence": [
                    f"Identified from plan image: kind={a.get('kind')}, count={a.get('count')}."
                ],
            }
        )

    kitchens: list[dict[str, Any]] = []
    for i, k in enumerate(simple.get("kitchens") or [], 1):
        count = k.get("count")
        kitchens.append(
            {
                "id": f"vis-kitchen-{i:02d}",
                "source": "vision",
                "source_refs": [f"vision:{image_name}:kitchen_{i}"],
                "assumptions": [],
                "inputs": {"raw": k},
                "conflict_notes": [],
                "count": int(count) if count is not None else 1,
                "estimated_area_m2": k.get("area_m2"),
                "confidence": 0.65,
                "evidence": ["Kitchen identified from plan image."],
            }
        )

    stairs: list[dict[str, Any]] = []
    for i, s in enumerate(simple.get("stairs") or [], 1):
        count = s.get("count")
        stairs.append(
            {
                "id": f"vis-stair-{i:02d}",
                "source": "vision",
                "source_refs": [f"vision:{image_name}:stair_{i}"],
                "assumptions": [],
                "inputs": {"raw": s},
                "conflict_notes": [],
                "count": int(count) if count is not None else 1,
                "flights": s.get("flights"),
                "width_m": s.get("width_m"),
                "confidence": 0.70,
                "evidence": ["Stair identified from plan image."],
            }
        )

    structural_elements: list[dict[str, Any]] = []
    for i, e in enumerate(simple.get("structural_elements") or [], 1):
        etype = e.get("type") or "other"
        raw_count = e.get("count")
        material = e.get("material") or ("concrete" if etype in {"column", "beam", "slab", "footing", "shear_wall", "lintel", "tie_beam"} else None)
        notation = e.get("id") or ""
        elem_id = notation if notation and not notation.startswith("vis-") else f"vis-{etype}-{i:02d}"

        concrete_grade = e.get("concrete_grade")
        concrete_grade_hint = None
        if concrete_grade and concrete_grade != "null":
            concrete_grade_hint = concrete_grade.replace("fc_", "fc'=").replace("_", " ")

        structural_elements.append(
            {
                "id": elem_id,
                "source": "vision",
                "source_refs": [f"vision:{image_name}:{etype}_{i}"],
                "assumptions": [],
                "inputs": {
                    "raw": e,
                    "notation": notation,
                    "concrete_grade_raw": concrete_grade,
                },
                "conflict_notes": [],
                "element_type": etype if etype not in {"shear_wall", "lintel", "tie_beam"} else "other",
                "count": int(raw_count) if raw_count is not None else 1,
                "area_m2": e.get("area_m2"),
                "length_m": e.get("length_m"),
                "span_m": e.get("span_m"),
                "section_width_m": e.get("section_width_m"),
                "section_height_m": e.get("section_height_m"),
                "material_hint": material,
                "reinforcement_hint": "reinforced" if material == "concrete" or e.get("has_reinforcement") else None,
                "concrete_grade_hint": concrete_grade_hint,
                "confidence": 0.65,
                "evidence": [
                    f"Structural element from plan: notation={notation}, type={etype}, "
                    f"section={e.get('section_width_m')}x{e.get('section_height_m')}m, "
                    f"material={material}, count={raw_count}."
                ],
            }
        )

    fixtures: list[dict[str, Any]] = []
    for i, f_item in enumerate(simple.get("fixtures") or [], 1):
        count = f_item.get("count")
        fixtures.append(
            {
                "id": f"vis-fixture-{i:02d}",
                "source": "vision",
                "source_refs": [f"vision:{image_name}:fixture_{i}"],
                "assumptions": [],
                "inputs": {"raw": f_item},
                "conflict_notes": [],
                "fixture_type": f_item.get("type") or "other",
                "count": int(count) if count is not None else 1,
                "unit": "unit",
                "confidence": 0.65,
                "evidence": [f"Counted from plan image: type={f_item.get('type')}."],
            }
        )

    extra_fixtures: list[dict[str, Any]] = []

    for i, e in enumerate(simple.get("electrical") or [], 1):
        count = e.get("count")
        extra_fixtures.append(
            {
                "id": f"vis-elec-{i:02d}",
                "source": "vision",
                "source_refs": [f"vision:{image_name}:elec_{i}"],
                "assumptions": [],
                "inputs": {"raw": e, "discipline": "electrical"},
                "conflict_notes": [],
                "fixture_type": e.get("type") or "electrical_other",
                "count": int(count) if count is not None else 1,
                "unit": "unit",
                "location_hint": e.get("location"),
                "confidence": 0.65,
                "evidence": [f"Electrical element from plan: type={e.get('type')}, count={count}."],
            }
        )

    for i, p in enumerate(simple.get("plumbing") or [], 1):
        count = p.get("count")
        extra_fixtures.append(
            {
                "id": f"vis-plumb-{i:02d}",
                "source": "vision",
                "source_refs": [f"vision:{image_name}:plumb_{i}"],
                "assumptions": [],
                "inputs": {
                    "raw": p,
                    "discipline": "plumbing",
                    "pipe_diameter_in": p.get("pipe_diameter_in"),
                    "pipe_material": p.get("material"),
                },
                "conflict_notes": [],
                "fixture_type": p.get("type") or "plumbing_other",
                "count": int(count) if count is not None else 1,
                "unit": "unit",
                "location_hint": p.get("location"),
                "confidence": 0.60,
                "evidence": [f"Plumbing element from plan: type={p.get('type')}, count={count}."],
            }
        )

    for i, ext in enumerate(simple.get("exterior_works") or [], 1):
        qty = ext.get("quantity")
        extra_fixtures.append(
            {
                "id": f"vis-ext-{i:02d}",
                "source": "vision",
                "source_refs": [f"vision:{image_name}:ext_{i}"],
                "assumptions": [],
                "inputs": {
                    "raw": ext,
                    "discipline": "exterior",
                    "ext_unit": ext.get("unit"),
                    "ext_material": ext.get("material"),
                },
                "conflict_notes": [],
                "fixture_type": ext.get("type") or "exterior_other",
                "count": int(qty) if qty is not None else 1,
                "unit": ext.get("unit") or "unit",
                "location_hint": ext.get("id"),
                "confidence": 0.55,
                "evidence": [f"Exterior work from plan: type={ext.get('type')}."],
            }
        )

    all_fixtures = fixtures + extra_fixtures

    plan_type = simple.get("plan_type", "unknown")
    annotations = simple.get("annotations_and_notes") or []
    floor_finishes = simple.get("floor_finishes") or []
    ceiling_finishes = simple.get("ceiling_finishes") or []

    notes = [
        f"Plan type detected: {plan_type}.",
        "Exhaustive vision extraction — Python-adapted to LevelInventory schema.",
    ]
    for ann in annotations[:10]:
        text = ann.get("text", "")
        interp = ann.get("interpretation", "")
        if text:
            notes.append(f"Annotation: '{text}' → {interp}")

    system_notes: list[str] = []
    if floor_finishes:
        for ff in floor_finishes:
            system_notes.append(
                f"Floor finish: {ff.get('type', 'unknown')} at {ff.get('location', 'unknown')}"
                f" ({ff.get('area_m2', '?')} m2)"
            )
    if ceiling_finishes:
        for cf in ceiling_finishes:
            system_notes.append(
                f"Ceiling finish: {cf.get('type', 'unknown')} at {cf.get('location', 'unknown')}"
                f" ({cf.get('area_m2', '?')} m2)"
            )

    return {
        "level_id": level_id,
        "level_name": level_name,
        "source": "vision",
        "source_image": image_name,
        "source_view": plan_type,
        "floor_area_m2": simple.get("floor_area_m2"),
        "ceiling_area_m2": simple.get("floor_area_m2"),
        "walls": walls,
        "doors": doors,
        "windows": windows,
        "wet_areas": wet_areas,
        "kitchens": kitchens,
        "stairs": stairs,
        "structural_elements": structural_elements,
        "fixtures": all_fixtures,
        "openings": [],
        "conflict_notes": [],
        "source_refs": [f"vision:{image_name}"],
        "assumptions": ["Quantities extracted from exhaustive visual plan analysis."],
        "inputs": {
            "image": image_name,
            "plan_type": plan_type,
            "floor_finishes": floor_finishes,
            "ceiling_finishes": ceiling_finishes,
            "annotations": annotations,
        },
        "system_notes": system_notes,
        "notes": notes,
    }


def _build_cross_checks(level_inventory: LevelInventory, cad_summary: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    block_frequency = {
        item["block_name"].lower(): item["count"]
        for item in cad_summary.get("inventory_hints", {}).get("block_frequency", [])
        if item.get("block_name")
    }

    if level_inventory.doors:
        door_count = sum(max(door.count, 0) for door in level_inventory.doors)
        block_hint = sum(
            count for name, count in block_frequency.items() if "door" in name or "puert" in name
        )
        checks.append(
            {
                "check": "door_inventory_vs_block_hints",
                "vision_count": door_count,
                "cad_block_hint": block_hint,
                "status": "info",
            }
        )

    if level_inventory.windows:
        window_count = sum(max(window.count, 0) for window in level_inventory.windows)
        block_hint = sum(
            count
            for name, count in block_frequency.items()
            if "window" in name or "vent" in name
        )
        checks.append(
            {
                "check": "window_inventory_vs_block_hints",
                "vision_count": window_count,
                "cad_block_hint": block_hint,
                "status": "info",
            }
        )

    return checks


def analyze_plan(
    image_path: Path,
    cad_summary: dict[str, Any],
    level_name: str,
    *,
    office_methodology: str | None = None,
    vision_profile_key: str | None = None,
) -> dict[str, Any]:
    client = get_client()
    image_path = Path(image_path).resolve()
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_b64 = encode_image(image_path)
    extension = image_path.suffix.lower().replace(".", "")
    mime = f"image/{extension}" if extension in {"png", "jpg", "jpeg", "webp"} else "image/png"

    system_prompt, profile_key = _compose_vision_system_prompt(vision_profile_key)

    # Step 1: Ask GPT-4o to return a simple flat inventory
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _build_simple_user_prompt(
                            image_path,
                            level_name,
                            cad_summary,
                            office_methodology=office_methodology,
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=4096,
        temperature=0.1,
    )

    raw_text = response.choices[0].message.content or ""
    simple_payload = _extract_json(raw_text)

    if simple_payload.get("parse_error"):
        return {
            "parse_error": True,
            "raw_text": raw_text,
            "_metadata": {
                "file": image_path.name,
                "timestamp": datetime.now().isoformat(),
                "vision_profile": profile_key,
            },
        }

    # Step 2: Python adapter converts simple dict → full LevelInventory dict
    level_id = level_name.lower().replace(" ", "_")
    adapted = _simple_to_level_inventory(simple_payload, level_name, level_id, image_path.name)

    level_inventory = level_inventory_from_dict(adapted, default_source="vision")
    result = level_inventory.to_dict()
    result["cad_cross_checks"] = _build_cross_checks(level_inventory, cad_summary)
    result["_raw_response"] = raw_text
    result["_simple_payload"] = simple_payload
    result["_metadata"] = {
        "file": image_path.name,
        "timestamp": datetime.now().isoformat(),
        "office_methodology_chars": len(office_methodology or ""),
        "vision_profile": profile_key,
    }
    return result


def run_full_vision_analysis(
    pages_dir: str,
    cad_summary: dict[str, Any],
    *,
    office_methodology: str | None = None,
    vision_profile_key: str | None = None,
) -> list[dict[str, Any]]:
    pages_path = Path(pages_dir)
    images = sorted(
        path for path in pages_path.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )

    results: list[dict[str, Any]] = []
    for image_path in images:
        level_name = image_path.stem
        try:
            results.append(
                analyze_plan(
                    image_path,
                    cad_summary,
                    level_name,
                    office_methodology=office_methodology,
                    vision_profile_key=vision_profile_key,
                )
            )
        except Exception as exc:  # pragma: no cover - depends on external API/runtime
            logger.warning("Vision failed for %s: %s", image_path.name, exc, exc_info=True)
            results.append({"error": str(exc), "file": image_path.name})

    return results


if __name__ == "__main__":
    json_path = Path("resumen_procesado.json") if Path("resumen_procesado.json").exists() else Path("../resumen_procesado.json")
    image_path = Path("vision_test_image.png")

    cad_summary: dict[str, Any] = {}
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as handle:
            cad_summary = json.load(handle)

    if image_path.exists():
        result = analyze_plan(image_path, cad_summary, level_name=image_path.stem, office_methodology=None)
        output_path = Path("vision_inventory_result.json")
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False)
        print(f"Vision inventory written to {output_path}")
    else:
        print("Place a test image at ./vision_test_image.png to run the module directly.")
