"""
Vision agent for normalized building inventory extraction.

This module treats images as an inventory source, not as a direct budget
discipline generator. The goal is to infer structured building elements that
the deterministic quantifier and rule engine can process later.
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


SYSTEM_PROMPT = """You extract normalized building inventory from plan images.

Rules:
1. Return only valid JSON. No markdown.
2. Do not output budget chapters, BC3 codes, Presto disciplines, or project-specific calibrations.
3. Use null for unknown dimensions instead of assuming defaults.
4. Keep evidence short and concrete.
5. Prefer conservative counts when visibility is ambiguous.

Use this schema:
{
  "level_id": "string",
  "level_name": "string",
  "source_view": "plan|elevation|site|unknown",
  "notes": ["string"],
  "confidence": 0.0,
  "walls": [
    {
      "id": "string",
      "source_layers": ["string"],
      "length_m": 0.0,
      "height_m": null,
      "thickness_m": null,
      "area_m2": null,
      "material_hint": null,
      "structural": null,
      "openings_count": 0,
      "confidence": 0.0,
      "evidence": ["string"]
    }
  ],
  "doors": [
    {
      "id": "string",
      "source_layers": ["string"],
      "count": 1,
      "width_m": null,
      "height_m": null,
      "type_hint": null,
      "material_hint": null,
      "exterior": null,
      "confidence": 0.0,
      "evidence": ["string"]
    }
  ],
  "windows": [
    {
      "id": "string",
      "source_layers": ["string"],
      "count": 1,
      "width_m": null,
      "height_m": null,
      "type_hint": null,
      "glazing_hint": null,
      "confidence": 0.0,
      "evidence": ["string"]
    }
  ],
  "wet_areas": [
    {
      "id": "string",
      "kind": "bathroom|laundry|service",
      "count": 1,
      "estimated_area_m2": null,
      "fixture_ids": [],
      "confidence": 0.0,
      "evidence": ["string"]
    }
  ],
  "kitchens": [
    {
      "id": "string",
      "count": 1,
      "estimated_area_m2": null,
      "island_present": null,
      "fixture_ids": [],
      "confidence": 0.0,
      "evidence": ["string"]
    }
  ],
  "stairs": [
    {
      "id": "string",
      "count": 1,
      "flights": null,
      "riser_count": null,
      "tread_count": null,
      "width_m": null,
      "elevation_change_m": null,
      "confidence": 0.0,
      "evidence": ["string"]
    }
  ],
  "fixtures": [
    {
      "id": "string",
      "fixture_type": "sink|toilet|shower|basin|switch|outlet|other",
      "count": 1,
      "unit": "unit",
      "location_hint": null,
      "confidence": 0.0,
      "evidence": ["string"]
    }
  ],
  "structural_elements": [
    {
      "id": "string",
      "element_type": "column|beam|slab|footing|wall|other",
      "count": 1,
      "length_m": null,
      "area_m2": null,
      "volume_m3": null,
      "material_hint": null,
      "confidence": 0.0,
      "evidence": ["string"]
    }
  ]
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


def _build_user_prompt(
    image_path: Path,
    level_name: str,
    cad_summary: dict[str, Any],
) -> str:
    return f"""Analyze this drawing image and extract a normalized building inventory.

Level name: {level_name}
View type hint: {_detect_view_type(image_path)}

Focus on:
- walls and wall systems
- doors
- windows
- wet areas
- kitchens
- stairs
- fixtures
- structural elements

Only include dimensions when they are directly visible in the image or supported by the CAD hints below.
Avoid project-specific defaults such as assumed floor heights, fixed bathroom counts, or tower calibration tables.

CAD hints:
{format_cad_facts_for_prompt(cad_summary)}
"""


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

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _build_user_prompt(image_path, level_name, cad_summary),
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
    payload = _extract_json(raw_text)
    if payload.get("parse_error"):
        return {
            "parse_error": True,
            "raw_text": raw_text,
            "_metadata": {
                "file": image_path.name,
                "timestamp": datetime.now().isoformat(),
            },
        }

    payload.setdefault("level_name", level_name)
    payload.setdefault("level_id", level_name.lower().replace(" ", "_"))
    payload.setdefault("source", "vision")
    payload.setdefault("source_image", image_path.name)
    payload.setdefault("source_view", _detect_view_type(image_path))
    payload.setdefault("cad_hints", {})

    for collection_name in (
        "walls",
        "openings",
        "doors",
        "windows",
        "wet_areas",
        "kitchens",
        "stairs",
        "fixtures",
        "structural_elements",
    ):
        for item in payload.get(collection_name, []):
            if isinstance(item, dict):
                item.setdefault("source", "vision")

    level_inventory = level_inventory_from_dict(payload, default_source="vision")
    result = level_inventory.to_dict()
    result["cad_cross_checks"] = _build_cross_checks(level_inventory, cad_summary)
    result["_raw_response"] = raw_text
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
