from __future__ import annotations

from coordination.extraction.from_aps_viewer_dump import elements_from_viewer_dump
from coordination.core.models_25d import Discipline, ProjectLevel
from coordination.core.registry import ProjectLevelRegistryDocument, ViewLevelPattern


def test_elements_from_viewer_dump_rect_primitive() -> None:
    viewer_dump = {
        "views": [
            {
                "name": "Primer nivel",
                "objects": [
                    {
                        "dbId": 10,
                        "name": "Muro",
                        "layer": "A-WALL",
                        "primitives": [
                            {"type": "rect", "x": 0, "y": 0, "width": 1000, "height": 500},
                        ],
                    }
                ],
            }
        ]
    }
    doc = ProjectLevelRegistryDocument(
        levels=[ProjectLevel(id="P1", name="Primer", offset_to_project_zero_mm=0.0)],
        view_level_patterns=[ViewLevelPattern(pattern="primer nivel", level_id="P1")],
    )
    elements = elements_from_viewer_dump(
        viewer_dump,
        discipline=Discipline.ARCH,
        level_doc=doc,
        default_level_id="P1",
        translation_mm=(0.0, 0.0),
        path_label="demo",
        coordination_issue_key="d:20260320",
    )
    assert len(elements) == 1
    assert elements[0].z_data.level_id == "P1"
    assert elements[0].metadata["geometry_quality"] == "high"
    assert elements[0].metadata["geometry_source"] == "dwg_aps_viewer_2d"
