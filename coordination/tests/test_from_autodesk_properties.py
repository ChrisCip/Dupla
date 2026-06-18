"""Pruebas ligeras del extractor APS → Element25D (sin cargar el JSON completo de NASAS)."""

from __future__ import annotations

from coordination.extraction.from_autodesk_properties import (
    pick_best_entities,
    square_footprint_mm,
)


def test_square_footprint_area() -> None:
    sq = square_footprint_mm(1.0)
    w = sq[1][0] - sq[0][0]
    assert abs(w * w - 1_000_000.0) < 1.0


def test_pick_best_entities_minimal() -> None:
    raw = {
        "views": [
            {
                "objects": [
                    {
                        "externalId": "S1",
                        "name": "Hatch [S1]",
                        "properties": {
                            "General": {"Name ": "Hatch", "Layer": "SE-3"},
                            "Geometry": {"Area": "10.0", "Elevation": "0.000 m"},
                        },
                    },
                    {
                        "externalId": "E1",
                        "name": "Poly [E1]",
                        "properties": {
                            "General": {"Name ": "Polyline", "Layer": "EL1"},
                            "Geometry": {"Area": "5.0", "Elevation": "0.000 m"},
                            "Misc": {"Closed": "Yes"},
                        },
                    },
                ]
            }
        ]
    }
    struct, mep = pick_best_entities(raw, min_area_m2=1.0)
    assert struct is not None and struct.external_id == "S1"
    assert mep is not None and mep.external_id == "E1"
