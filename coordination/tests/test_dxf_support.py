from __future__ import annotations

from pathlib import Path

import ezdxf
import pytest

from coordination.extraction.from_dwg_ezdxf import extract_elements_from_dwg
from coordination.core.models_25d import Discipline
from coordination.extraction.odafc_bridge import odafc_available


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


def test_extract_elements_from_dxf_line_and_hatch(tmp_path: Path) -> None:
    dxf_path = tmp_path / "line_hatch.dxf"
    doc = ezdxf.new("R2010")
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    msp.add_line((0, 0), (1000, 0), dxfattribs={"layer": "MUROS"})
    hatch = msp.add_hatch(color=2, dxfattribs={"layer": "EST. MUROS H.A."})
    hatch.paths.add_polyline_path([(0, 0), (500, 0), (500, 500), (0, 500)], is_closed=True)
    doc.saveas(dxf_path)
    elements = extract_elements_from_dwg(
        dxf_path,
        Discipline.STRUC,
        level_id="NPT_P1",
        min_area_mm2=100.0,
    )
    assert len(elements) >= 2
    roles = {str(item.metadata.get("canonical_role")) for item in elements}
    assert "WALL" in roles


@pytest.mark.skipif(not odafc_available(), reason="ODA File Converter not available")
def test_extract_elements_from_binary_dwg_uses_odafc(tmp_path: Path) -> None:
    dwg_path = tmp_path / "fake.dwg"
    dwg_path.write_bytes(b"AC1027fakecontent")
    elements = extract_elements_from_dwg(
        dwg_path,
        Discipline.STRUC,
        level_id="NPT_P1",
        min_area_mm2=100.0,
    )
    assert isinstance(elements, list)
