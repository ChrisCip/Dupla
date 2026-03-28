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
    out = synthetic_takeoffs_from_pres(levels, pairs, max_per_level=50)
    assert out == []
