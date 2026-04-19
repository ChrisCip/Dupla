"""Tests for agents/partida_generator.py — all OpenAI calls are mocked."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.partida_generator import (
    CHAPTER_CATALOG,
    PartidaGenerator,
    _assign_chapter,
    _infer_discipline,
)
from core.schemas import QuantityTakeoff, QuantityTrace


def _make_takeoff(item_key: str, item_type: str, unit: str = "m2", quantity: float = 10.0, discipline: str = "") -> QuantityTakeoff:
    meta = {"source_discipline": discipline} if discipline else {}
    return QuantityTakeoff(
        item_key=item_key,
        item_type=item_type,
        unit=unit,
        quantity=quantity,
        formula="",
        trace=QuantityTrace(metadata=meta),
    )


# ---------------------------------------------------------------------------
# Chapter assignment
# ---------------------------------------------------------------------------

def test_assign_chapter_wall_net_area():
    t = _make_takeoff("k", "wall_net_area")
    assert _assign_chapter(t) == "06"


def test_assign_chapter_beam_concrete():
    t = _make_takeoff("k", "beam_concrete_volume", unit="m3")
    assert _assign_chapter(t) == "02"


def test_assign_chapter_slab_volume():
    t = _make_takeoff("k", "slab_concrete_volume", unit="m3")
    assert _assign_chapter(t) == "03"


def test_assign_chapter_footing_volume():
    t = _make_takeoff("k", "footing_concrete_volume", unit="m3")
    assert _assign_chapter(t) == "01"


def test_assign_chapter_reinforcement():
    t = _make_takeoff("k", "column_reinforcement_kg", unit="kg")
    assert _assign_chapter(t) == "04"


def test_assign_chapter_door_count():
    t = _make_takeoff("k", "door_count", unit="ud")
    assert _assign_chapter(t) == "10"


def test_assign_chapter_fixture_count_plumbing():
    t = QuantityTakeoff(
        item_key="k", item_type="fixture_count", unit="ud", quantity=1.0, formula="",
        inputs={"discipline": "plumbing"},
        trace=QuantityTrace(),
    )
    assert _assign_chapter(t) == "19"


def test_assign_chapter_fixture_count_electrical():
    t = QuantityTakeoff(
        item_key="k", item_type="fixture_count", unit="ud", quantity=1.0, formula="",
        inputs={"discipline": "electrical"},
        trace=QuantityTrace(),
    )
    assert _assign_chapter(t) == "23"


def test_assign_chapter_unknown_falls_to_24():
    t = _make_takeoff("k", "completely_unknown_type")
    assert _assign_chapter(t) == "24"


# ---------------------------------------------------------------------------
# Discipline inference
# ---------------------------------------------------------------------------

def test_infer_discipline_arquitectura_from_stamped():
    t = _make_takeoff("k", "wall_net_area", discipline="arquitectonica")
    assert _infer_discipline(t) == "arquitectura"


def test_infer_discipline_estructural_from_stamped():
    t = _make_takeoff("k", "beam_concrete_volume", discipline="estructural")
    assert _infer_discipline(t) == "estructural"


def test_infer_discipline_electrico_from_stamped():
    t = _make_takeoff("k", "fixture_count", discipline="electrica")
    assert _infer_discipline(t) == "electrico"


def test_infer_discipline_estructural_from_item_type():
    t = _make_takeoff("k", "beam_concrete_volume")
    assert _infer_discipline(t) == "estructural"


# ---------------------------------------------------------------------------
# CHAPTER_CATALOG coverage
# ---------------------------------------------------------------------------

def test_chapter_catalog_has_24_entries():
    assert len(CHAPTER_CATALOG) == 24


def test_chapter_catalog_covers_all_disciplines():
    disciplines = {disc for _, disc in CHAPTER_CATALOG.values()}
    assert "arquitectura" in disciplines
    assert "estructural" in disciplines
    assert "sanitario" in disciplines
    assert "electrico" in disciplines


# ---------------------------------------------------------------------------
# PartidaGenerator.generate — mocked OpenAI
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_takeoffs():
    return [
        _make_takeoff("wall-001:net_area", "wall_net_area", unit="m2", quantity=145.3, discipline="arquitectonica"),
        _make_takeoff("beam-001:concrete_volume", "beam_concrete_volume", unit="m3", quantity=8.5, discipline="estructural"),
    ]


def _mock_openai_resp(content: str) -> MagicMock:
    resp = MagicMock()
    resp.choices[0].message.content = content
    return resp


def test_generate_returns_partidas_for_each_takeoff(sample_takeoffs):
    batch_responses = [
        json.dumps([{
            "chapter_code": "06",
            "chapter_name": "MUROS Y DIVISIONES",
            "discipline": "arquitectura",
            "partida_code": "06.001",
            "partida_description": "Muro de bloque de 6\" con panete ambas caras, h=3.00m",
            "unit": "m2",
            "quantity": 145.3,
            "source_takeoff_key": "wall-001:net_area",
        }]),
        json.dumps([{
            "chapter_code": "02",
            "chapter_name": "HORMIGON ARMADO - COLUMNAS Y VIGAS",
            "discipline": "estructural",
            "partida_code": "02.001",
            "partida_description": "Hormigon armado f'c=280kg/cm2 en vigas V-1 nivel 2",
            "unit": "m3",
            "quantity": 8.5,
            "source_takeoff_key": "beam-001:concrete_volume",
        }]),
    ]

    with patch("agents.partida_generator.OpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        mock_client.chat.completions.create.side_effect = [
            _mock_openai_resp(r) for r in batch_responses
        ]
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            generator = PartidaGenerator()
            result = generator.generate(sample_takeoffs)

    keys = {p["source_takeoff_key"] for p in result}
    assert "wall-001:net_area" in keys
    assert "beam-001:concrete_volume" in keys


def test_generate_returns_empty_on_api_failure(sample_takeoffs):
    with patch("agents.partida_generator.OpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            generator = PartidaGenerator()
            result = generator.generate(sample_takeoffs)

    assert result == []


def test_generate_skips_pres_reference_lines():
    pres = QuantityTakeoff(
        item_key="pres:wall",
        item_type="pres_reference_line",
        unit="m2",
        quantity=10.0,
        formula="",
        trace=QuantityTrace(),
    )
    with patch("agents.partida_generator.OpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        mock_client.chat.completions.create.return_value = _mock_openai_resp("[]")
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            generator = PartidaGenerator()
            generator.generate([pres])

    mock_client.chat.completions.create.assert_not_called()


def test_generate_raises_without_api_key():
    with patch.dict("os.environ", {}, clear=True):
        # Remove OPENAI_API_KEY if present
        import os
        os.environ.pop("OPENAI_API_KEY", None)
        with pytest.raises((ValueError, ImportError)):
            PartidaGenerator()


def test_generate_partida_description_is_specific(sample_takeoffs):
    """Generated descriptions must not be generic placeholders."""
    mock_resp_content = json.dumps([{
        "chapter_code": "06",
        "chapter_name": "MUROS Y DIVISIONES",
        "discipline": "arquitectura",
        "partida_code": "06.001",
        "partida_description": "Muro de bloque 15x20x40 SNP con panete ambas caras, acabado liso",
        "unit": "m2",
        "quantity": 145.3,
        "source_takeoff_key": "wall-001:net_area",
    }])

    wall_takeoff = [sample_takeoffs[0]]

    with patch("agents.partida_generator.OpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value
        mock_client.chat.completions.create.return_value = _mock_openai_resp(mock_resp_content)
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            generator = PartidaGenerator()
            result = generator.generate(wall_takeoff)

    assert len(result) == 1
    desc = result[0]["partida_description"]
    # Should not be a generic one-word description
    assert len(desc) > 10
    assert desc != "Muro"
