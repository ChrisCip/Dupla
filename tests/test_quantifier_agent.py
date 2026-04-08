from agents.quantifier_agent import quantify_inventory
from core.schemas import LevelInventory, Opening, StructuralElement, Wall


def test_quantify_inventory_generates_wall_net_floor_and_ceiling_takeoffs() -> None:
    level = LevelInventory(
        level_id="level_01",
        level_name="Level 01",
        floor_area_m2=120.0,
        ceiling_area_m2=115.0,
        walls=[
            Wall(
                id="wall_01",
                source="hybrid",
                length_m=10.0,
                height_m=3.0,
                thickness_m=0.15,
                source_layers=["A-WALL"],
                source_refs=["geometry:wall_01"],
                evidence=["Wall length measured from CAD and height confirmed visually."],
            )
        ],
        openings=[
            Opening(
                id="opening_01",
                source="vision",
                wall_id="wall_01",
                opening_type="door",
                count=1,
                width_m=1.0,
                height_m=2.0,
                source_refs=["vision:opening_01"],
            ),
            Opening(
                id="opening_02",
                source="vision",
                wall_id="wall_01",
                opening_type="window",
                count=1,
                area_m2=1.5,
                source_refs=["vision:opening_02"],
            ),
        ],
    )

    takeoffs = quantify_inventory([level])
    takeoff_map = {takeoff.item_key: takeoff for takeoff in takeoffs}

    assert takeoff_map["level_01:floor_area"].quantity == 120.0
    assert takeoff_map["level_01:floor_area"].formula == "level.floor_area_m2"
    assert takeoff_map["level_01:ceiling_area"].quantity == 115.0
    assert takeoff_map["wall_01:gross_area"].quantity == 30.0
    assert takeoff_map["wall_01:net_area"].quantity == 26.5
    assert takeoff_map["wall_01:net_area"].formula == "wall.length_m * wall.height_m - openings_area_m2"
    assert takeoff_map["wall_01:net_area"].inputs["openings_area_m2"] == 3.5
    assert "opening_01" in takeoff_map["wall_01:net_area"].trace.source_entity_ids


def test_quantify_inventory_records_assumption_when_opening_data_is_incomplete() -> None:
    level = LevelInventory(
        level_id="level_02",
        level_name="Level 02",
        walls=[
            Wall(
                id="wall_02",
                source="json",
                area_m2=24.0,
                source_refs=["hatch:wall_02"],
            )
        ],
        openings=[
            Opening(
                id="opening_unknown",
                source="vision",
                wall_id="wall_02",
                opening_type="window",
                count=1,
            )
        ],
    )

    takeoffs = quantify_inventory([level])
    takeoff_map = {takeoff.item_key: takeoff for takeoff in takeoffs}

    assert takeoff_map["wall_02:net_area"].quantity == 24.0
    assert any(
        "Incomplete opening data prevented full deduction" in note
        for note in takeoff_map["wall_02:net_area"].assumptions
    )


def test_quantify_inventory_deducts_only_one_instance_for_hybrid_aggregated_opening_size() -> None:
    level = LevelInventory(
        level_id="level_03",
        level_name="Level 03",
        walls=[
            Wall(
                id="wall_03",
                source="hybrid",
                length_m=10.0,
                height_m=3.0,
            )
        ],
        openings=[
            Opening(
                id="opening_hybrid",
                source="hybrid",
                wall_id="wall_03",
                opening_type="door",
                count=2,
                width_m=1.0,
                height_m=2.1,
                source_refs=["block:door_b1", "block:door_b2", "vision:door_01"],
                inputs={
                    "json": {"json_count": 2},
                    "vision": {"observed_instance_count": 1},
                },
                conflict_notes=["Conflict on count: kept JSON value 2, vision suggested 1."],
            )
        ],
    )

    takeoffs = quantify_inventory([level])
    takeoff_map = {takeoff.item_key: takeoff for takeoff in takeoffs}
    net_takeoff = takeoff_map["wall_03:net_area"]
    deduction = net_takeoff.trace.metadata["opening_deductions"][0]

    assert net_takeoff.quantity == 27.9
    assert any(
        "Deducted one observed instance only" in note
        for note in net_takeoff.assumptions
    )
    assert deduction["multiplication_policy"] == "single_observed_instance_only"
    assert deduction["deducted_instance_count"] == 1
    assert deduction["aggregated_count"] == 2
    assert deduction["dimension_source"] == "vision"


def test_quantify_inventory_allows_count_times_size_when_homogeneity_is_explicit() -> None:
    level = LevelInventory(
        level_id="level_04",
        level_name="Level 04",
        walls=[
            Wall(
                id="wall_04",
                source="hybrid",
                length_m=10.0,
                height_m=3.0,
            )
        ],
        openings=[
            Opening(
                id="opening_homogeneous",
                source="hybrid",
                wall_id="wall_04",
                opening_type="door",
                count=2,
                width_m=1.0,
                height_m=2.1,
                source_refs=["block:door_b1", "block:door_b2", "vision:door_01"],
                inputs={
                    "json": {"json_count": 2},
                    "vision": {
                        "observed_instance_count": 1,
                        "homogeneous_instances": True,
                    },
                },
            )
        ],
    )

    takeoffs = quantify_inventory([level])
    takeoff_map = {takeoff.item_key: takeoff for takeoff in takeoffs}
    net_takeoff = takeoff_map["wall_04:net_area"]
    deduction = net_takeoff.trace.metadata["opening_deductions"][0]

    assert net_takeoff.quantity == 25.8
    assert any(
        "homogeneous_instances was explicitly set true" in note
        for note in net_takeoff.assumptions
    )
    assert deduction["multiplication_policy"] == "count_times_size_with_explicit_homogeneity"
    assert deduction["deducted_instance_count"] == 2


def test_quantify_inventory_generates_structural_quantities_and_material_hints() -> None:
    level = LevelInventory(
        level_id="level_structural_qto",
        level_name="Level Structural QTO",
        structural_elements=[
            StructuralElement(
                id="beam_01",
                source="hybrid",
                element_type="beam",
                count=1,
                length_m=12.0,
                section_width_m=0.25,
                section_height_m=0.5,
                material_hint="concrete",
                reinforcement_hint="reinforced",
                concrete_grade_hint="H25",
                source_refs=["geometry:beam_01"],
            ),
            StructuralElement(
                id="column_01",
                source="hybrid",
                element_type="column",
                count=4,
                length_m=12.0,
                section_width_m=0.30,
                section_height_m=0.30,
                material_hint="concrete",
                reinforcement_hint="reinforced",
                source_refs=["geometry:column_01"],
            ),
            StructuralElement(
                id="slab_01",
                source="hybrid",
                element_type="slab",
                count=1,
                area_m2=30.0,
                section_height_m=0.15,
                material_hint="concrete",
                reinforcement_hint="reinforced",
                source_refs=["hatch:slab_01"],
            ),
        ],
    )

    takeoffs = quantify_inventory([level])
    takeoff_map = {takeoff.item_key: takeoff for takeoff in takeoffs}

    assert takeoff_map["beam_01:beam_length"].quantity == 12.0
    assert takeoff_map["beam_01:beam_volume"].quantity == 1.5
    assert takeoff_map["beam_01:concrete_volume"].quantity == 1.5
    assert takeoff_map["beam_01:formwork_area_hint"].quantity == 15.0
    assert takeoff_map["beam_01:reinforcement_kg"].quantity == 1.5 * 100.0

    assert round(takeoff_map["column_01:column_volume"].quantity, 4) == 1.08
    assert round(takeoff_map["column_01:formwork_area_hint"].quantity, 4) == 14.4
    assert round(takeoff_map["column_01:reinforcement_kg"].quantity, 2) == round(1.08 * 120.0, 2)

    assert takeoff_map["slab_01:slab_area"].quantity == 30.0
    assert takeoff_map["slab_01:slab_volume"].quantity == 4.5
    assert takeoff_map["slab_01:concrete_volume"].quantity == 4.5
    assert takeoff_map["slab_01:formwork_area_hint"].quantity == 30.0
    assert takeoff_map["slab_01:reinforcement_kg"].quantity == 4.5 * 80.0

    assert takeoff_map["beam_01:concrete_volume"].inputs["material_hint"] == "concrete"
    assert takeoff_map["beam_01:concrete_volume"].trace.metadata["material_hint"] == "concrete"
    assert takeoff_map["beam_01:reinforcement_kg"].inputs["rebar_ratio_kg_m3"] == 100.0
