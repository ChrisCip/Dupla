"""Tests for pricing.excel_price_loader against the real constructor Excel."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXCEL_FIXTURE = REPO_ROOT / "data" / "Lista de precios-analisis-MO.xlsx"


pytestmark = pytest.mark.skipif(
    not EXCEL_FIXTURE.exists(),
    reason=f"Fixture not present: {EXCEL_FIXTURE}",
)


@pytest.fixture(scope="module")
def store():
    from pricing.excel_price_loader import load_constructor_pricing
    return load_constructor_pricing(str(EXCEL_FIXTURE))


# ---------------------------------------------------------------------------
# Counts (sprint targets)
# ---------------------------------------------------------------------------

def test_apus_parsed_at_least_190(store):
    """analisis may25 -> >=190 APUs (de 204 declarados)."""
    assert len(store.apus) >= 190, f"got {len(store.apus)} APUs"


def test_materials_parsed_at_least_450(store):
    """Lista de precios may25 -> >=450 materiales."""
    assert len(store.materials) >= 450, f"got {len(store.materials)} materials"


def test_labor_parsed_at_least_500(store):
    """MO 25 -> >=500 actividades."""
    assert len(store.labor) >= 500, f"got {len(store.labor)} labor activities"


# ---------------------------------------------------------------------------
# Concrete value verifications
# ---------------------------------------------------------------------------

def test_hormigon_140_unit_price(store):
    """APU 'HORMIGON 140 KG/CM2' = 7,121.15 DOP/M3."""
    apu = next(
        a for a in store.apus.values()
        if "HORMIGON 140 KG/CM2" in a.description.upper()
    )
    assert apu.unit == "M3"
    assert abs(apu.unit_price_total - 7121.15) < 0.01


def test_columnas_c1_has_concrete_steel_formwork_and_labor(store):
    """APU 'COLUMNAS C1 (0.30X0.20)' debe tener hormigón + acero + encofrado + MO."""
    apu = next(
        a for a in store.apus.values()
        if "COLUMNAS C1" in a.description.upper()
        and "0.30X0.20" in a.description.upper().replace(" ", "")
    )
    descs = " | ".join(c.description.lower() for c in apu.components)
    types = {c.component_type for c in apu.components}

    assert "hormig" in descs, f"missing concrete in {descs!r}"
    assert "acero" in descs, f"missing steel in {descs!r}"
    # Encofrado en este APU aparece como 'Carpintería' / 'Envarillado' (labor de encofrado).
    assert ("encofrado" in descs) or ("carpinter" in descs) or ("envarillado" in descs), (
        f"missing formwork/encofrado in {descs!r}"
    )
    assert "labor" in types, f"no labor components classified, only {types}"


# ---------------------------------------------------------------------------
# Round-trip via JSON cache
# ---------------------------------------------------------------------------

def test_json_round_trip_preserves_store(tmp_path, store):
    from pricing.excel_price_loader import save_pricing_store, load_pricing_store

    cache_file = tmp_path / "store.json"
    save_pricing_store(store, cache_file)
    restored = load_pricing_store(cache_file)

    assert restored.to_dict() == store.to_dict()
    assert len(restored.apus) == len(store.apus)
    assert len(restored.materials) == len(store.materials)
    assert len(restored.labor) == len(store.labor)
    # Spot-check a concrete APU survives intact (including components).
    apu_before = store.apus["3.01"]
    apu_after = restored.apus["3.01"]
    assert apu_after == apu_before


def test_load_or_cache_uses_cache_on_second_call(tmp_path):
    from pricing.excel_price_loader import (
        cache_path_for,
        load_or_cache_constructor_pricing,
    )

    s1 = load_or_cache_constructor_pricing(
        EXCEL_FIXTURE, project_id="test_proj", cache_dir=tmp_path,
    )
    cache_file = cache_path_for("test_proj", tmp_path)
    assert cache_file.exists()

    s2 = load_or_cache_constructor_pricing(
        EXCEL_FIXTURE, project_id="test_proj", cache_dir=tmp_path,
    )
    assert s1.to_dict() == s2.to_dict()


def test_wall_budget_uses_constructor_apu_from_pricing_excel(store):
    from agents.quantifier_agent import quantify_inventory
    from budget.composer import compose_budget_rows
    from core.schemas import LevelInventory, ProjectContext, Wall
    from pricing.apu_matcher import APUMatcher

    level = LevelInventory(
        level_id="level_01",
        level_name="Level 01",
        walls=[
            Wall(
                id="json-wall-mb",
                source="hybrid",
                length_m=10.0,
                height_m=2.8,
                thickness_m=0.15,
                material_hint="masonry",
                wall_system="masonry_wall",
                interior_exterior_hint="interior",
            )
        ],
    )
    takeoffs = quantify_inventory([level])
    matcher = APUMatcher(store, log_path=None)

    _, lines, _ = compose_budget_rows(
        ProjectContext(project_id="pricing_wall_test", project_name="Pricing Wall Test"),
        takeoffs,
        {},
        apu_matcher=matcher,
    )
    by_type = {line.metadata["item_type"]: line for line in lines}
    wall_line = by_type["wall_net_area"]

    assert wall_line.summary == "Muro de bloques, espesor 15 cm, ubicacion interior"
    assert "json-wall" not in wall_line.summary
    assert wall_line.code == "10.08"
    assert wall_line.unit_price == pytest.approx(2167.5386)
    assert wall_line.metadata["source_type"] == "constructor_apu"


# ---------------------------------------------------------------------------
# Robustness against quirky inputs in the spec
# ---------------------------------------------------------------------------

def test_codes_rounded_to_two_decimals(store):
    """Excel float codes like 3.0199999 must end up as '3.02', not '3.0199999...'."""
    for apu in store.apus.values():
        if "." in apu.code:
            int_part, _, frac = apu.code.partition(".")
            assert len(frac) <= 2, f"APU code {apu.code!r} has more than 2 decimals"


def test_units_normalised_uppercase(store):
    for mat in list(store.materials.values())[:50]:
        assert mat.unit == mat.unit.upper(), f"material unit {mat.unit!r} not upper"
    for lab in list(store.labor.values())[:50]:
        assert lab.unit == lab.unit.upper(), f"labor unit {lab.unit!r} not upper"
