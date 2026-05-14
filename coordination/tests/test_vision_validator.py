"""Tests para coordination/semantic/vision_validator.py."""

from __future__ import annotations

import builtins
import json
from unittest.mock import patch

from coordination.core.models_25d import Discipline, Element25D, ZInterval
from coordination.reporting.tile_renderer import RenderedTile
from coordination.semantic.vision_validator import (
    VisionClashAssessment,
    VisionElementResult,
    VisionTileResult,
    _build_coordination_prompt,
    _extract_json,
    _parse_vision_payload,
    _svg_to_png_base64,
    apply_vision_results,
    validate_incident_tiles,
    validate_tile,
)


def _make_element(id: str = "e1", discipline: Discipline = Discipline.ARCH) -> Element25D:
    return Element25D(
        id=id,
        source_ref=f"test|layer|LINE|{id}",
        discipline=discipline,
        category="wall",
        footprint_coords_mm=[(0, 0), (1000, 0), (1000, 1000), (0, 1000)],
        z_data=ZInterval(level_id="NPT_P1", z_ref_raw_mm=0.0, thickness_mm=3000.0),
        metadata={"level_id": "NPT_P1"},
    )


def _tile(tile_id: str = "tile_1", incident_id: str | None = "incident_0001") -> RenderedTile:
    return RenderedTile(
        tile_id=tile_id,
        svg_content='<svg xmlns="http://www.w3.org/2000/svg"><polygon points="0,0 1,0 1,1"/></svg>',
        bbox_cad_mm=(0.0, 0.0, 2000.0, 2000.0),
        width_px=800,
        height_px=800,
        scale_mm_per_px=2.5,
        elements_in_tile=["e1"],
        texts_in_tile=[{"content": "P-01", "centroid_mm": (500.0, 500.0)}],
        incident_id=incident_id,
    )


def _valid_payload() -> dict:
    raw = json.dumps(
        {
            "elements_identified": [
                {
                    "element_id": "e1",
                    "semantic_type": "muro",
                    "name": "P-01",
                    "confidence": "high",
                    "evidence": "texto P-01 cercano",
                }
            ],
            "clash_assessment": {
                "appears_real": True,
                "reason": "intersección visible en rojo",
                "severity_visual": "major",
            },
        }
    )
    parsed = json.loads(raw)
    parsed["_raw_response"] = raw
    parsed["_model_used"] = "test-model"
    return parsed


def test_build_coordination_prompt() -> None:
    prompt = _build_coordination_prompt(_tile(), [_make_element()], _tile().texts_in_tile)

    assert "Área cubierta: (0, 0) a (2000, 2000) mm" in prompt
    assert "ARQUITECTURA" in prompt
    assert "P-01" in prompt
    assert "zona roja semitransparente" in prompt


def test_parse_vision_response_valid() -> None:
    result = _parse_vision_payload(
        _valid_payload(),
        tile_id="tile_1",
        incident_id="incident_0001",
        model_used="test-model",
    )

    assert result.success is True
    assert result.elements_identified[0].semantic_type == "muro"
    assert result.clash_assessment is not None
    assert result.clash_assessment.severity_visual == "major"


def test_parse_vision_response_with_backticks() -> None:
    raw = "```json\n" + json.dumps({"elements_identified": [], "clash_assessment": {"appears_real": False}}) + "\n```"

    parsed = _extract_json(raw)

    assert parsed["elements_identified"] == []
    assert parsed["clash_assessment"]["appears_real"] is False


def test_parse_vision_response_invalid() -> None:
    parsed = _extract_json("not-json")
    result = _parse_vision_payload(
        parsed,
        tile_id="tile_1",
        incident_id="incident_0001",
        model_used="test-model",
    )

    assert result.success is False
    assert "invalid_json" in str(result.error)


def test_validate_tile_mock() -> None:
    with patch("coordination.semantic.vision_validator._svg_to_png_base64", return_value=""), patch(
        "coordination.semantic.vision_validator._call_vision_model",
        return_value=_valid_payload(),
    ):
        result = validate_tile(_tile(), [_make_element()], model="test-model")

    assert result.success is True
    assert result.model_used == "test-model"
    assert result.elements_identified[0].element_id == "e1"


def test_validate_incident_tiles_max() -> None:
    fake_result = VisionTileResult(
        tile_id="tile_0",
        incident_id="incident_0",
        elements_identified=[],
        clash_assessment=None,
        model_used="test-model",
        raw_response="{}",
        success=True,
    )
    tiles = [_tile(f"tile_{idx}", f"incident_{idx}") for idx in range(10)]

    with patch("coordination.semantic.vision_validator.validate_tile", return_value=fake_result) as mocked:
        results = validate_incident_tiles(tiles, [_make_element()], max_tiles=3, model="test-model")

    assert len(results) == 3
    assert mocked.call_count == 3


def test_apply_vision_results() -> None:
    result = VisionTileResult(
        tile_id="tile_1",
        incident_id="incident_0001",
        elements_identified=[
            VisionElementResult("e1", "muro", None, "medium", "polígono azul"),
        ],
        clash_assessment=VisionClashAssessment(True, "real", "minor"),
        model_used="test-model",
        raw_response="{}",
        success=True,
    )

    overrides = apply_vision_results([result])

    assert overrides["incident_0001"] is result


def test_svg_to_png_fallback() -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):
        if name == "cairosvg":
            raise ImportError("no cairosvg")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        assert _svg_to_png_base64("<svg></svg>") == ""
