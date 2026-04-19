"""Contract tests for agents/partida_adapter.py.

These tests verify that adapt_generated_to_legacy_format() produces output
with the same type and structure that match_takeoffs_to_bc3() returns, so
compose_budget() can consume it without modification.
"""

from __future__ import annotations

import pytest

from agents.partida_adapter import adapt_generated_to_legacy_format
from core.schemas import BudgetCandidate, QuantityTakeoff, QuantityTrace


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_generated() -> list[dict]:
    return [
        {
            "chapter_code": "06",
            "chapter_name": "MUROS Y DIVISIONES",
            "discipline": "arquitectura",
            "partida_code": "06.001",
            "partida_description": "Muro de bloque 15x20x40 SNP con panete ambas caras, h=3.00m",
            "unit": "m2",
            "quantity": 145.3,
            "source_takeoff_key": "wall-001:net_area",
        }
    ]


@pytest.fixture
def sample_takeoffs() -> list[QuantityTakeoff]:
    return [
        QuantityTakeoff(
            item_key="wall-001:net_area",
            item_type="wall_net_area",
            unit="m2",
            quantity=145.3,
            formula="",
            trace=QuantityTrace(),
        )
    ]


@pytest.fixture
def minimal_bc3_catalog() -> dict:
    return {
        "items": [{"code": "P0501101", "unit": "m2", "summary": "Panete generico", "price": 327.63}],
        "concepts_by_code": {"P0501101": {"unit": "m2", "price": 327.63}},
    }


# ---------------------------------------------------------------------------
# Type contract — output must match match_takeoffs_to_bc3 return type
# ---------------------------------------------------------------------------

def test_returns_dict(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    candidates, _ = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    assert isinstance(candidates, dict)


def test_keys_are_takeoff_item_keys(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    candidates, _ = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    assert "wall-001:net_area" in candidates


def test_values_are_lists_of_budget_candidates(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    candidates, _ = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    for key, candidate_list in candidates.items():
        assert isinstance(candidate_list, list)
        assert len(candidate_list) >= 1
        for c in candidate_list:
            assert isinstance(c, BudgetCandidate)


def test_budget_candidate_has_all_required_fields(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    candidates, _ = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    cand = candidates["wall-001:net_area"][0]
    assert hasattr(cand, "takeoff_key")
    assert hasattr(cand, "bc3_code")
    assert hasattr(cand, "summary")
    assert hasattr(cand, "unit")
    assert hasattr(cand, "score")
    assert hasattr(cand, "rationale")
    assert hasattr(cand, "source")
    assert hasattr(cand, "bc3_origin")


# ---------------------------------------------------------------------------
# Field values — what compose_budget depends on
# ---------------------------------------------------------------------------

def test_score_is_1_0(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    candidates, _ = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    cand = candidates["wall-001:net_area"][0]
    assert cand.score == 1.0


def test_source_is_partida_generator(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    candidates, _ = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    cand = candidates["wall-001:net_area"][0]
    assert cand.source == "partida_generator"


def test_unit_matches_takeoff_unit(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    """Critical: select_strong_candidate requires unit equality with takeoff."""
    candidates, _ = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    cand = candidates["wall-001:net_area"][0]
    takeoff = sample_takeoffs[0]
    assert cand.unit == takeoff.unit


def test_summary_contains_generated_description(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    """ConstruCosto pricing uses candidate.summary to find the best price."""
    candidates, _ = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    cand = candidates["wall-001:net_area"][0]
    assert "bloque" in cand.summary.lower()


def test_takeoff_key_matches_item_key(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    candidates, _ = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    cand = candidates["wall-001:net_area"][0]
    assert cand.takeoff_key == "wall-001:net_area"


# ---------------------------------------------------------------------------
# Extended catalog — guard check compatibility
# ---------------------------------------------------------------------------

def test_synthetic_code_in_extended_catalog_items(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    _, extended = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    codes_in_items = {item.get("code") for item in extended["items"]}
    assert "06.001" in codes_in_items


def test_synthetic_code_in_extended_catalog_concepts(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    _, extended = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    assert "06.001" in extended["concepts_by_code"]


def test_original_catalog_not_mutated(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    original_item_count = len(minimal_bc3_catalog["items"])
    original_concept_count = len(minimal_bc3_catalog["concepts_by_code"])

    adapt_generated_to_legacy_format(sample_generated, sample_takeoffs, minimal_bc3_catalog)

    assert len(minimal_bc3_catalog["items"]) == original_item_count
    assert len(minimal_bc3_catalog["concepts_by_code"]) == original_concept_count


def test_original_bc3_entries_still_present(sample_generated, sample_takeoffs, minimal_bc3_catalog):
    _, extended = adapt_generated_to_legacy_format(
        sample_generated, sample_takeoffs, minimal_bc3_catalog
    )
    assert "P0501101" in extended["concepts_by_code"]


# ---------------------------------------------------------------------------
# Error handling / edge cases
# ---------------------------------------------------------------------------

def test_skips_partida_with_missing_source_key(sample_takeoffs, minimal_bc3_catalog):
    bad = [{"partida_code": "06.001", "partida_description": "test"}]
    candidates, _ = adapt_generated_to_legacy_format(bad, sample_takeoffs, minimal_bc3_catalog)
    assert len(candidates) == 0


def test_skips_partida_with_unknown_takeoff_key(sample_takeoffs, minimal_bc3_catalog):
    orphan = [{
        "partida_code": "06.001",
        "partida_description": "test",
        "source_takeoff_key": "nonexistent:key",
    }]
    candidates, _ = adapt_generated_to_legacy_format(orphan, sample_takeoffs, minimal_bc3_catalog)
    assert len(candidates) == 0


def test_empty_generated_returns_empty_candidates(sample_takeoffs, minimal_bc3_catalog):
    candidates, extended = adapt_generated_to_legacy_format([], sample_takeoffs, minimal_bc3_catalog)
    assert candidates == {}
    # Catalog unchanged (only original entries)
    assert len(extended["items"]) == len(minimal_bc3_catalog["items"])


def test_multiple_partidas_produce_multiple_candidates(sample_takeoffs, minimal_bc3_catalog):
    two_takeoffs = [
        QuantityTakeoff(item_key="t1", item_type="wall_net_area", unit="m2", quantity=10.0, formula="", trace=QuantityTrace()),
        QuantityTakeoff(item_key="t2", item_type="floor_area", unit="m2", quantity=20.0, formula="", trace=QuantityTrace()),
    ]
    two_partidas = [
        {"partida_code": "06.001", "partida_description": "Muro A", "unit": "m2", "quantity": 10.0, "source_takeoff_key": "t1"},
        {"partida_code": "08.001", "partida_description": "Piso B", "unit": "m2", "quantity": 20.0, "source_takeoff_key": "t2"},
    ]
    candidates, extended = adapt_generated_to_legacy_format(two_partidas, two_takeoffs, minimal_bc3_catalog)
    assert "t1" in candidates
    assert "t2" in candidates
    assert "06.001" in extended["concepts_by_code"]
    assert "08.001" in extended["concepts_by_code"]
