from core.schemas import LevelInventory
from knowledge.pres_expansion import synthetic_takeoffs_from_pres
from knowledge.training_data import TrainingPair


def test_synthetic_takeoffs_match_nivel_by_page_index() -> None:
    pairs = [
        TrainingPair(
            input_item_type="footing",
            input_unit="m3",
            input_context="NIVEL 5 | HORMIGON ARMADO",
            output_bc3_code="P0303130",
            output_description="Zapata Z1",
            output_unit="m3",
            output_quantity=7.56,
            output_price=399.4,
        )
    ]
    levels = [
        LevelInventory(
            level_id="binder1_page_005",
            level_name="Binder1_page_005",
            source="hybrid",
        )
    ]
    out = synthetic_takeoffs_from_pres(levels, pairs, max_per_level=50)
    assert len(out) == 1
    assert out[0].item_type == "pres_reference_line"
    assert out[0].quantity == 7.56
    assert out[0].inputs["pres_bc3_code"] == "P0303130"


def test_synthetic_takeoffs_match_level_nn_ids() -> None:
    pairs = [
        TrainingPair(
            input_item_type="footing",
            input_unit="m3",
            input_context="NIVEL 3 | HORMIGON ARMADO",
            output_bc3_code="P0303000",
            output_description="Hormigon limpieza",
            output_unit="m3",
            output_quantity=1.0,
            output_price=85.83,
        )
    ]
    levels = [
        LevelInventory(
            level_id="level_03",
            level_name="level_03",
            source="hybrid",
        )
    ]
    out = synthetic_takeoffs_from_pres(levels, pairs, max_per_level=50)
    assert len(out) == 1
    assert out[0].inputs["pres_bc3_code"] == "P0303000"


def test_pres_fallback_template_when_level_name_does_not_match() -> None:
    pairs = [
        TrainingPair(
            input_item_type="footing",
            input_unit="m3",
            input_context="NIVEL 5 | HORMIGON ARMADO",
            output_bc3_code="P0303130",
            output_description="Zapata",
            output_unit="m3",
            output_quantity=1.0,
            output_price=1.0,
        ),
        TrainingPair(
            input_item_type="footing",
            input_unit="m3",
            input_context="NIVEL 5 | HORMIGON ARMADO",
            output_bc3_code="P0303135",
            output_description="Zapata 2",
            output_unit="m3",
            output_quantity=2.0,
            output_price=2.0,
        ),
    ]
    levels = [
        LevelInventory(
            level_id="cover_sheet",
            level_name="Portada",
            source="hybrid",
        )
    ]
    out = synthetic_takeoffs_from_pres(
        levels, pairs, max_per_level=50, fallback_unmatched=True
    )
    assert len(out) == 2
    assert all("pres_fb" in t.item_key for t in out)
    assert all(t.inputs.get("pres_fallback") for t in out)


def test_synthetic_takeoffs_no_match_when_level_differs() -> None:
    pairs = [
        TrainingPair(
            input_item_type="footing",
            input_unit="m3",
            input_context="NIVEL 9 | HORMIGON ARMADO",
            output_bc3_code="P0303130",
            output_description="Zapata",
            output_unit="m3",
            output_quantity=1.0,
            output_price=1.0,
        )
    ]
    levels = [
        LevelInventory(
            level_id="binder1_page_005",
            level_name="Binder1_page_005",
            source="hybrid",
        )
    ]
    out = synthetic_takeoffs_from_pres(
        levels, pairs, max_per_level=50, fallback_unmatched=False
    )
    assert out == []
