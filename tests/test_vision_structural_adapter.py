"""Adapter structural_elements JSON → LevelInventory (sin llamar a OpenAI)."""

from pathlib import Path

from agents.vision_agent import (
    _build_simple_user_prompt,
    _cad_suggests_structural,
    _coerce_vision_list,
    _simple_to_level_inventory,
)
from core.schemas import level_inventory_from_dict


def test_upload_discipline_arquitectura_skips_cad_structural_hint() -> None:
    """Si el usuario ya subió por ruta 'arquitectura', no sugerimos estructura por capas."""
    cad = {"inventory_hints": {"layer_names": ["S-COLUM-01", "A-WALL"]}}
    body = _build_simple_user_prompt(
        Path("planta.png"),
        "Nivel 1",
        cad,
        upload_discipline_id="arquitectura",
    )
    assert "CONTEXTO DE SUBIDA" in body
    assert "NOTA (CAD)" not in body
    assert "REGLA DE DESGLOSE POR TIPO" in body


def test_upload_discipline_estructura_includes_upload_block() -> None:
    body = _build_simple_user_prompt(
        Path("est.png"),
        "Nivel 1",
        {},
        upload_discipline_id="estructura",
    )
    assert "ESTRUCTURA" in body
    assert "REGLA DE DESGLOSE POR TIPO" in body


def test_cad_suggests_structural_from_layers() -> None:
    assert _cad_suggests_structural(
        {"inventory_hints": {"layer_names": ["A-COLUM-01", "PARED"]}}
    )
    assert not _cad_suggests_structural({"inventory_hints": {"layer_names": ["A-WALL-FIN"]}})


def test_coerce_vision_list_flattens_items_wrapper() -> None:
    nested = {"items": [{"id": "M1", "material": "block_6in", "estimated_length_m": 10.0}]}
    assert len(_coerce_vision_list(nested)) == 1
    assert _coerce_vision_list(nested)[0]["id"] == "M1"


def test_structural_notation_from_tipo_when_id_missing() -> None:
    simple = {
        "plan_type": "structural",
        "structural_elements": [
            {
                "tipo": "CB",
                "type": "column",
                "count": 4,
                "section_width_m": 0.4,
                "section_height_m": 0.4,
                "material": "concrete",
            }
        ],
    }
    adapted = _simple_to_level_inventory(simple, "Nivel 1", "nivel_1", "page.png")
    inv = level_inventory_from_dict(adapted, default_source="vision")
    assert inv.structural_elements[0].id == "CB"


def test_structural_gebsa_fields_flow_to_inventory_inputs() -> None:
    simple = {
        "plan_type": "structural",
        "structural_elements": [
            {
                "id": "C1",
                "type": "column",
                "count": 12,
                "section_width_m": 0.3,
                "section_height_m": 0.6,
                "material": "concrete",
                "concrete_grade": "fc_280",
                "has_reinforcement": True,
                "reinforcement_visible": False,
                "spec_source": "schedule_table",
                "schedule_row_text": "C1 0.30x0.60 fc280",
                "missing_detail_sheets": True,
                "notes": "Tabla legible",
            }
        ],
    }
    adapted = _simple_to_level_inventory(simple, "Nivel 1", "nivel_1", "EST_PAGE_03.png")
    inv = level_inventory_from_dict(adapted, default_source="vision")
    assert len(inv.structural_elements) == 1
    col = inv.structural_elements[0]
    assert col.id == "C1"
    assert col.section_width_m == 0.3
    assert col.section_height_m == 0.6
    inp = col.inputs
    assert inp.get("structural_label") == "C1"
    assert inp.get("spec_source") == "schedule_table"
    assert inp.get("schedule_row_text") == "C1 0.30x0.60 fc280"
    assert inp.get("missing_detail_sheets") is True
    assert inp.get("reinforcement_visible") is False
    assert any("Armado" in a for a in col.assumptions)
