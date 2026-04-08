from agents.quantifier_agent import quantify_inventory
from core.schemas import LevelInventory, StructuralElement


def test_quantifier_generates_structural_takeoffs_from_explicit_and_inferred_inputs() -> None:
    level = LevelInventory(
        level_id="level_structural_takeoffs",
        level_name="Level Structural Takeoffs",
        structural_elements=[
            StructuralElement(
                id="beam_inferred",
                source="hybrid",
                element_type="beam",
                count=2,
                span_m=5.0,
                section_width_m=0.25,
                section_height_m=0.45,
                material_hint="concrete",
                reinforcement_hint="reinforced",
                concrete_grade_hint="H25",
                host_level="level_structural_takeoffs",
                adjacent_elements=["column_a", "column_b"],
                assumptions=["Beam section depth was inferred from elevation graphics."],
                inputs={"context_tags": ["frame", "primary_structure"]},
            ),
            StructuralElement(
                id="column_explicit",
                source="json",
                element_type="column",
                count=4,
                length_m=12.0,
                section_width_m=0.30,
                section_height_m=0.30,
                material_hint="concrete",
                reinforcement_hint="reinforced",
                host_level="level_structural_takeoffs",
                inputs={"context_tags": ["frame", "vertical_support"]},
            ),
            StructuralElement(
                id="slab_explicit",
                source="hybrid",
                element_type="slab",
                count=1,
                area_m2=42.0,
                section_height_m=0.16,
                material_hint="concrete",
                reinforcement_hint="reinforced",
                host_level="level_structural_takeoffs",
                assumptions=["Slab thickness remained a design-stage hint pending structural sheets."],
                inputs={"context_tags": ["horizontal_structure", "wet_area_zone"]},
            ),
        ],
    )

    takeoffs = quantify_inventory([level])
    takeoff_map = {takeoff.item_key: takeoff for takeoff in takeoffs}

    assert takeoff_map["beam_inferred:beam_length"].quantity == 10.0
    assert takeoff_map["beam_inferred:beam_length"].formula == "structural_element.span_m * structural_element.count"
    assert takeoff_map["beam_inferred:beam_volume"].quantity == 1.125
    assert takeoff_map["beam_inferred:concrete_volume"].quantity == 1.125
    assert takeoff_map["beam_inferred:formwork_area_hint"].quantity == 11.5
    assert takeoff_map["beam_inferred:reinforcement_kg"].quantity == 1.125 * 100.0

    assert round(takeoff_map["column_explicit:column_volume"].quantity, 4) == 1.08
    assert round(takeoff_map["column_explicit:formwork_area_hint"].quantity, 4) == 14.4
    assert round(takeoff_map["column_explicit:reinforcement_kg"].quantity, 2) == round(1.08 * 120.0, 2)

    assert takeoff_map["slab_explicit:slab_area"].quantity == 42.0
    assert takeoff_map["slab_explicit:slab_volume"].quantity == 6.72
    assert takeoff_map["slab_explicit:concrete_volume"].quantity == 6.72
    assert takeoff_map["slab_explicit:formwork_area_hint"].quantity == 42.0
    assert takeoff_map["slab_explicit:reinforcement_kg"].quantity == 6.72 * 80.0


def test_quantifier_propagates_material_hints_context_and_uncertainty_for_structural_items() -> None:
    level = LevelInventory(
        level_id="level_structural_trace",
        level_name="Level Structural Trace",
        structural_elements=[
            StructuralElement(
                id="beam_trace",
                source="hybrid",
                element_type="beam",
                count=2,
                span_m=4.5,
                section_width_m=0.25,
                section_height_m=0.40,
                material_hint="concrete",
                reinforcement_hint="reinforced",
                load_bearing=True,
                host_level="level_structural_trace",
                adjacent_elements=["column_left", "column_right"],
                assumptions=["Beam length was inferred from repeated bay spacing."],
                inputs={"context_tags": ["frame", "primary_structure"]},
            )
        ],
    )

    takeoffs = quantify_inventory([level])
    takeoff_map = {takeoff.item_key: takeoff for takeoff in takeoffs}

    beam_length = takeoff_map["beam_trace:beam_length"]
    beam_concrete = takeoff_map["beam_trace:concrete_volume"]
    beam_reinforcement = takeoff_map["beam_trace:reinforcement_kg"]

    assert any(
        "total length was inferred from span_m * count" in note
        for note in beam_length.assumptions
    )
    assert beam_concrete.inputs["material_hint"] == "concrete"
    assert beam_concrete.inputs["host_level"] == "level_structural_trace"
    assert beam_concrete.inputs["adjacent_elements"] == ["column_left", "column_right"]
    assert beam_concrete.trace.metadata["material_hint"] == "concrete"
    assert beam_concrete.trace.metadata["host_level"] == "level_structural_trace"
    assert beam_concrete.trace.metadata["adjacent_elements"] == ["column_left", "column_right"]
    assert beam_concrete.inputs["context_tags"] == [
        "structural",
        "beam",
        "concrete",
        "volume",
        "frame",
        "primary_structure",
    ]
    assert beam_reinforcement.inputs["rebar_ratio_kg_m3"] == 100.0
    assert beam_reinforcement.unit == "kg"
