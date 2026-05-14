from __future__ import annotations

from pathlib import Path

import ezdxf

from coordination.extraction.from_dwg_ezdxf import extract_elements_from_dwg
from coordination.core.models_25d import Discipline


def test_extract_elements_from_dxf_closed_polyline(tmp_path: Path) -> None:
    dxf_path = tmp_path / "simple.dxf"
    doc = ezdxf.new("R2010")
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (400, 0), (400, 300), (0, 300)], close=True, dxfattribs={"layer": "TEST"})
    doc.saveas(dxf_path)
    elements = extract_elements_from_dwg(
        dxf_path,
        Discipline.STRUC,
        level_id="NPT_P1",
        min_area_mm2=10_000.0,
    )
    assert len(elements) == 1
    assert elements[0].metadata["geometry_source"] == "dxf_ezdxf"
    assert elements[0].metadata["source"] == "cad_ezdxf"
