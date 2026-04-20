"""B3: wet_area_fixture_count emission and dedupe vs fixture_count."""

from agents.quantifier_agent import quantify_inventory
from core.schemas import Fixture, LevelInventory, WetArea


def test_wet_area_fixture_count_from_vision_flags() -> None:
    level = LevelInventory(
        level_id="L1",
        level_name="Nivel 1",
        wet_areas=[
            WetArea(
                id="ba1",
                source="vision",
                kind="full_bathroom",
                count=3,
                inputs={
                    "raw": {
                        "has_toilet": True,
                        "has_sink": True,
                        "has_shower": True,
                        "has_bathtub": False,
                        "has_bidet": False,
                    }
                },
                source_refs=["vision:ba1"],
            ),
        ],
    )
    takeoffs = quantify_inventory([level])
    waf = [t for t in takeoffs if t.item_type == "wet_area_fixture_count"]
    by_ft = {t.inputs["fixture_type"]: t for t in waf}
    assert len(by_ft) == 3
    assert by_ft["toilet"].quantity == 3.0
    assert by_ft["sink"].quantity == 3.0
    assert by_ft["shower_base"].quantity == 3.0
    assert "Inodoro en baño" in by_ft["toilet"].inputs["takeoff_description"]
    assert by_ft["toilet"].trace.metadata.get("source_discipline") == "sanitaria"


def test_fixture_count_sanitary_skipped_when_wet_area_fixtures_emitted() -> None:
    level = LevelInventory(
        level_id="L1",
        level_name="Nivel 1",
        wet_areas=[
            WetArea(
                id="ba1",
                source="vision",
                kind="full_bathroom",
                count=1,
                inputs={"raw": {"has_toilet": True}},
                source_refs=["v:1"],
            ),
        ],
        fixtures=[
            Fixture(
                id="fx-toilet",
                source="vision",
                fixture_type="toilet",
                count=1,
                unit="unit",
                inputs={},
                source_refs=["v:fx"],
            ),
        ],
    )
    takeoffs = quantify_inventory([level])
    assert any(t.item_type == "wet_area_fixture_count" for t in takeoffs)
    assert not any(
        t.item_type == "fixture_count" and t.inputs.get("fixture_type") == "toilet"
        for t in takeoffs
    )


def test_fixture_count_sanitary_kept_when_no_wet_area_fixture_flags() -> None:
    level = LevelInventory(
        level_id="L1",
        level_name="Nivel 1",
        wet_areas=[
            WetArea(
                id="ba1",
                source="vision",
                kind="bathroom",
                count=1,
                inputs={"raw": {}},
                source_refs=["v:1"],
            ),
        ],
        fixtures=[
            Fixture(
                id="fx-toilet",
                source="vision",
                fixture_type="toilet",
                count=2,
                unit="unit",
                inputs={},
                source_refs=["v:fx"],
            ),
        ],
    )
    takeoffs = quantify_inventory([level])
    assert not any(t.item_type == "wet_area_fixture_count" for t in takeoffs)
    toilet_counts = [
        t for t in takeoffs
        if t.item_type == "fixture_count" and t.inputs.get("fixture_type") == "toilet"
    ]
    assert len(toilet_counts) == 1
    assert toilet_counts[0].quantity == 2.0


def test_electrical_fixture_not_skipped_when_wet_area_fixtures_exist() -> None:
    level = LevelInventory(
        level_id="L1",
        level_name="Nivel 1",
        wet_areas=[
            WetArea(
                id="ba1",
                source="vision",
                kind="full_bathroom",
                count=1,
                inputs={"raw": {"has_sink": True}},
                source_refs=["v:1"],
            ),
        ],
        fixtures=[
            Fixture(
                id="fx-out",
                source="vision",
                fixture_type="outlet_110v",
                count=4,
                unit="unit",
                inputs={"discipline": "electrical"},
                source_refs=["v:e"],
            ),
        ],
    )
    takeoffs = quantify_inventory([level])
    assert any(t.item_type == "wet_area_fixture_count" for t in takeoffs)
    assert any(
        t.item_type == "fixture_count" and t.inputs.get("fixture_type") == "outlet_110v"
        for t in takeoffs
    )
