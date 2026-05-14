"""Tests para coordination/reporting/tile_renderer.py."""

from __future__ import annotations

from pathlib import Path

from coordination.core.clash import ClashConflict, ClashIncident
from coordination.core.models_25d import Discipline, Element25D, ZInterval
from coordination.reporting.tile_renderer import (
    CLASH_ZONE_FILL,
    DISCIPLINE_COLORS,
    TileSpec,
    _cad_to_svg,
    collect_elements_in_bbox,
    compute_tile_bbox,
    render_incident_tile,
    render_tile_svg,
    save_tile,
)


def _make_element(
    id: str,
    discipline: Discipline,
    footprint: list[tuple[float, float]],
    level_id: str = "NPT_P1",
    nearby_texts: list[dict] | None = None,
) -> Element25D:
    return Element25D(
        id=id,
        source_ref=f"test|layer|LINE|{id}",
        discipline=discipline,
        category=f"LINE:{discipline.value}",
        footprint_coords_mm=footprint,
        z_data=ZInterval(
            level_id=level_id,
            z_ref_raw_mm=0.0,
            thickness_mm=3000.0,
            measurement_uncertainty_mm=0.0,
        ),
        metadata={
            "level_id": level_id,
            "file_level_id": f"test_file|{level_id}",
            "nearby_texts": nearby_texts or [],
        },
    )


def _conflict() -> ClashConflict:
    return ClashConflict(
        element_id_a="a",
        element_id_b="b",
        discipline_a=Discipline.ARCH,
        discipline_b=Discipline.STRUC,
        overlap_depth_z_mm=100.0,
        z_overlap_range_project_mm=(0.0, 100.0),
        plan_intersection_area_mm2=250000.0,
        plan_intersection_centroid_mm=(750.0, 750.0),
        plan_intersection_bounds_mm=(500.0, 500.0, 1000.0, 1000.0),
        level_ids=("NPT_P1", "NPT_P1"),
        source_refs=("test_a|layer|LINE|a", "test_b|layer|LINE|b"),
    )


def _incident() -> ClashIncident:
    return ClashIncident(
        incident_id="incident_0001",
        file_pair=("test_a.dwg", "test_b.dwg"),
        level_id="NPT_P1",
        cell_key=(0, 0),
        member_count=1,
        representative_conflict=_conflict(),
        plan_centroid_mm=(750.0, 750.0),
        plan_bounds_mm=(500.0, 500.0, 1000.0, 1000.0),
    )


def test_compute_tile_bbox_padding() -> None:
    incident = _incident().model_copy(update={"plan_bounds_mm": (100.0, 100.0, 200.0, 200.0), "plan_centroid_mm": (150.0, 150.0)})

    assert compute_tile_bbox(incident, padding_factor=0.3) == (70.0, 70.0, 230.0, 230.0)


def test_compute_tile_bbox_degenerate() -> None:
    incident = _incident().model_copy(update={"plan_bounds_mm": (100.0, 100.0, 100.0, 100.0), "plan_centroid_mm": (100.0, 100.0)})

    bbox = compute_tile_bbox(incident, padding_factor=0.3)

    assert bbox[0] < bbox[2]
    assert bbox[1] < bbox[3]
    assert bbox == (-1500.0, -1500.0, 1700.0, 1700.0)


def test_collect_elements_in_bbox() -> None:
    elements = [
        _make_element(str(idx), Discipline.ARCH, [(idx * 1000, 0), (idx * 1000 + 100, 0), (idx * 1000 + 100, 100), (idx * 1000, 100)])
        for idx in range(5)
    ]

    found = collect_elements_in_bbox(elements, (-100.0, -100.0, 2200.0, 200.0), level_id="NPT_P1")

    assert [element.id for element in found] == ["0", "1", "2"]


def test_collect_elements_invalid_footprint() -> None:
    elements = [
        _make_element("valid", Discipline.ARCH, [(0, 0), (100, 0), (100, 100), (0, 100)]),
        _make_element("bad", Discipline.ARCH, [(0, 0), (100, 0)]),
    ]

    found = collect_elements_in_bbox(elements, (-100.0, -100.0, 200.0, 200.0), level_id="NPT_P1")

    assert [element.id for element in found] == ["valid"]


def test_cad_to_svg_corners() -> None:
    min_x = 100.0
    max_y = 300.0
    scale = 2.0

    assert _cad_to_svg(100.0, 100.0, min_x, max_y, scale) == (0.0, 400.0)
    assert _cad_to_svg(500.0, 300.0, min_x, max_y, scale) == (800.0, 0.0)


def test_render_tile_svg_basic() -> None:
    elements = [
        _make_element("a", Discipline.ARCH, [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]),
        _make_element("b", Discipline.STRUC, [(500, 500), (1500, 500), (1500, 1500), (500, 1500)]),
    ]
    tile_spec = TileSpec("tile_1", (0.0, 0.0, 2000.0, 2000.0), "NPT_P1", ["test.dwg"])

    tile = render_tile_svg(tile_spec, elements, [{"content": "P-1", "centroid_mm": (600.0, 600.0)}])

    assert "<svg" in tile.svg_content
    assert "<polygon" in tile.svg_content
    assert "<text" in tile.svg_content
    assert DISCIPLINE_COLORS["ARQUITECTURA"] in tile.svg_content


def test_render_tile_svg_with_clash() -> None:
    elements = [
        _make_element("a", Discipline.ARCH, [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]),
        _make_element("b", Discipline.STRUC, [(500, 500), (1500, 500), (1500, 1500), (500, 1500)]),
    ]
    tile_spec = TileSpec("tile_1", (0.0, 0.0, 2000.0, 2000.0), "NPT_P1", ["test.dwg"])

    tile = render_tile_svg(tile_spec, elements, [], clash_conflicts=[_conflict()])

    assert CLASH_ZONE_FILL in tile.svg_content
    assert 'stroke-dasharray="6 4"' in tile.svg_content


def test_render_tile_svg_empty() -> None:
    tile_spec = TileSpec("empty", (0.0, 0.0, 2000.0, 2000.0), "NPT_P1", [])

    tile = render_tile_svg(tile_spec, [], [])

    assert tile.svg_content.startswith("<svg")
    assert 'class="grid"' in tile.svg_content
    assert 'class="legend"' in tile.svg_content


def test_render_tile_svg_has_legend() -> None:
    elements = [_make_element("a", Discipline.ARCH, [(0, 0), (1000, 0), (1000, 1000), (0, 1000)])]
    tile_spec = TileSpec("legend", (0.0, 0.0, 2000.0, 2000.0), "NPT_P1", [])

    tile = render_tile_svg(tile_spec, elements, [])

    assert "ARQUITECTURA" in tile.svg_content
    assert "1mm =" in tile.svg_content
    assert "1m" in tile.svg_content


def test_render_incident_tile() -> None:
    elements = [
        _make_element("a", Discipline.ARCH, [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]),
        _make_element("b", Discipline.STRUC, [(500, 500), (1500, 500), (1500, 1500), (500, 1500)]),
    ]

    tile = render_incident_tile(_incident(), elements)

    assert tile.incident_id == "incident_0001"
    assert tile.svg_content
    assert set(tile.elements_in_tile) == {"a", "b"}


def test_save_tile(tmp_path: Path) -> None:
    tile_spec = TileSpec("save", (0.0, 0.0, 2000.0, 2000.0), "NPT_P1", [])
    tile = render_tile_svg(tile_spec, [], [])
    output = tmp_path / "tile.svg"

    path = save_tile(tile, output)

    assert Path(path).exists()
    assert output.read_text(encoding="utf-8").startswith("<svg")
