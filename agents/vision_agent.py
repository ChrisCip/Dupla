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
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from core.schemas import LevelInventory, level_inventory_from_dict

load_dotenv(Path(__file__).parent.parent / ".env")

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

_SIMPLE_SYSTEM_PROMPT = """You are a building quantity surveyor analyzing architectural plan images.

Count and list ALL visible building elements concisely.
Return ONLY valid JSON — no markdown, no explanation, no text before or after.
Use null for values you cannot determine from the image.
Only report what is clearly visible; do not invent counts."""

_SIMPLE_SCHEMA_HINT = """{
  "floor_area_m2": <number or null>,
  "walls": [
    {"material": "masonry|concrete|drywall|wood|other",
     "location": "interior|exterior|unknown",
     "estimated_length_m": <number or null>,
     "estimated_area_m2": <number or null>,
     "height_m": <number or null>}
  ],
  "doors": [{"type": "interior|exterior|garage|main_entry|service|other", "count": <integer>, "width_m": <number or null>}],
  "windows": [{"type": "sliding|fixed|casement|jalousie|other", "count": <integer>, "width_m": <number or null>}],
  "wet_areas": [{"kind": "bathroom|laundry|service_bath", "count": <integer>, "area_m2": <number or null>}],
  "kitchens": [{"count": <integer>, "area_m2": <number or null>}],
  "stairs": [{"count": <integer>, "flights": <integer or null>, "width_m": <number or null>}],
  "structural_elements": [{"type": "column|beam|slab|footing|shear_wall", "count": <integer or null>, "area_m2": <number or null>}],
  "fixtures": [{"type": "sink|toilet|shower|bathtub|outlet|switch|luminaire|panel|pump|other", "count": <integer>}]
}"""


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
) -> str:
    view_type = _detect_view_type(image_path)
    cad_hints = format_cad_facts_for_prompt(cad_summary)
    return f"""Analyze this {view_type} image for level: {level_name}

CAD layer hints (use to cross-check your counts):
{cad_hints}

Count ALL visible building elements. Group same-type elements together.
Each wall group (interior masonry, exterior concrete, etc.) = one entry.
Each door type (interior, exterior, etc.) = one entry with total count.
Each window type = one entry with total count.

Return this exact JSON structure:
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

    walls: list[dict[str, Any]] = []
    for i, w in enumerate(simple.get("walls") or [], 1):
        walls.append(
            {
                "id": f"vis-wall-{i:02d}",
                "source": "vision",
                "source_layers": [],
                "source_refs": [f"vision:{image_name}:wall_{i}"],
                "assumptions": ["Dimensions estimated from visible plan scale."],
                "inputs": {"raw": w},
                "conflict_notes": [],
                "length_m": w.get("estimated_length_m"),
                "height_m": w.get("height_m"),
                "area_m2": w.get("estimated_area_m2"),
                "material_hint": w.get("material"),
                "interior_exterior_hint": (
                    w.get("location") if w.get("location") in {"interior", "exterior"} else None
                ),
                "confidence": 0.65,
                "evidence": [
                    f"Identified from plan image: material={w.get('material')}, "
                    f"location={w.get('location')}."
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
                "source_layers": [],
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
                "source_layers": [],
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
                "source_layers": [],
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
        structural_elements.append(
            {
                "id": f"vis-{etype}-{i:02d}",
                "source": "vision",
                "source_layers": [],
                "source_refs": [f"vision:{image_name}:{etype}_{i}"],
                "assumptions": [],
                "inputs": {"raw": e},
                "conflict_notes": [],
                "element_type": etype,
                "count": int(raw_count) if raw_count is not None else 1,
                "area_m2": e.get("area_m2"),
                "length_m": e.get("length_m"),
                "confidence": 0.60,
                "evidence": [f"Identified from plan image: type={etype}."],
            }
        )

    fixtures: list[dict[str, Any]] = []
    for i, f_item in enumerate(simple.get("fixtures") or [], 1):
        count = f_item.get("count")
        fixtures.append(
            {
                "id": f"vis-fixture-{i:02d}",
                "source": "vision",
                "source_layers": [],
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

    return {
        "level_id": level_id,
        "level_name": level_name,
        "source": "vision",
        "source_image": image_name,
        "floor_area_m2": simple.get("floor_area_m2"),
        "walls": walls,
        "doors": doors,
        "windows": windows,
        "wet_areas": wet_areas,
        "kitchens": kitchens,
        "stairs": stairs,
        "structural_elements": structural_elements,
        "fixtures": fixtures,
        "openings": [],
        "conflict_notes": [],
        "source_refs": [f"vision:{image_name}"],
        "assumptions": ["Quantities estimated from visual plan analysis."],
        "inputs": {"image": image_name},
        "notes": ["Simple vision extraction — Python-adapted to LevelInventory schema."],
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


def analyze_plan(image_path: Path, cad_summary: dict[str, Any], level_name: str) -> dict[str, Any]:
    client = get_client()
    image_path = Path(image_path).resolve()
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_b64 = encode_image(image_path)
    extension = image_path.suffix.lower().replace(".", "")
    mime = f"image/{extension}" if extension in {"png", "jpg", "jpeg", "webp"} else "image/png"

    # Step 1: Ask GPT-4o to return a simple flat inventory
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SIMPLE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _build_simple_user_prompt(image_path, level_name, cad_summary),
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
        max_tokens=2048,
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
    }
    return result


def run_full_vision_analysis(pages_dir: str, cad_summary: dict[str, Any]) -> list[dict[str, Any]]:
    pages_path = Path(pages_dir)
    images = sorted(
        path for path in pages_path.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )

    results: list[dict[str, Any]] = []
    for image_path in images:
        level_name = image_path.stem
        try:
            results.append(analyze_plan(image_path, cad_summary, level_name))
        except Exception as exc:  # pragma: no cover - depends on external API/runtime
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
        result = analyze_plan(image_path, cad_summary, level_name=image_path.stem)
        output_path = Path("vision_inventory_result.json")
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False)
        print(f"Vision inventory written to {output_path}")
    else:
        print("Place a test image at ./vision_test_image.png to run the module directly.")
