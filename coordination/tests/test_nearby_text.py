from __future__ import annotations

from coordination.core.models_25d import Discipline, Element25D, ZInterval
from coordination.semantic.nearby_text import (
    CadText,
    build_text_index,
    enrich_elements_with_nearby_text,
    extract_texts_from_accore_payload,
    find_nearby_texts,
)


def _bounds(x0: float, y0: float, x1: float, y1: float) -> dict:
    return {"Min": {"X": x0, "Y": y0, "Z": 0}, "Max": {"X": x1, "Y": y1, "Z": 0}}


def _text(content: str, x: float, y: float, handle: str = "T") -> CadText:
    return CadText(
        content=content,
        centroid_mm=(x, y),
        bbox_mm=(x - 10, y - 10, x + 10, y + 10),
        layer="ANNO",
        handle=handle,
        entity_type="DBText",
        source_file="a.dwg",
    )


def _element(element_id: str, x: float, y: float) -> Element25D:
    return Element25D(
        id=element_id,
        source_ref=f"a.dwg|L|Polyline|{element_id}",
        discipline=Discipline.ARCH,
        category="Polyline:L",
        footprint_coords_mm=[
            (x - 100, y - 100),
            (x + 100, y - 100),
            (x + 100, y + 100),
            (x - 100, y + 100),
        ],
        z_data=ZInterval(level_id="N1", z_ref_raw_mm=0, thickness_mm=250),
        metadata={},
    )


def test_extract_texts_basic() -> None:
    payload = {
        "UnitsToMmFactor": 1000.0,
        "Entities": [
            {"Type": "DBText", "Layer": "TXT", "Handle": "1", "TextString": "P-1", "Bounds": _bounds(1, 2, 2, 3)},
            {"Type": "MText", "Layer": "TXT", "Handle": "2", "Contents": "BAÑO", "Bounds": _bounds(4, 5, 6, 7)},
            {"Type": "LWPOLYLINE", "Layer": "WALL", "Handle": "3", "Bounds": _bounds(0, 0, 1, 1)},
        ],
    }
    texts = extract_texts_from_accore_payload(payload, source_file="a.dwg")
    assert [item.content for item in texts] == ["P-1", "BAÑO"]
    assert texts[0].centroid_mm == (1500.0, 2500.0)


def test_extract_texts_missing_content() -> None:
    payload = {"Entities": [{"Type": "DBText", "Layer": "TXT", "Handle": "1", "Bounds": _bounds(0, 0, 1, 1)}]}
    texts = extract_texts_from_accore_payload(payload, source_file="a.dwg")
    assert texts == []


def test_extract_texts_empty_payload() -> None:
    assert extract_texts_from_accore_payload({}, source_file="a.dwg") == []


def test_build_text_index() -> None:
    index = build_text_index([_text(str(i), i * 100, 0) for i in range(5)])
    assert index is not None


def test_find_nearby_texts_basic() -> None:
    texts = [_text("A", 0, 0), _text("B", 200, 0), _text("C", 3000, 0)]
    index = build_text_index(texts)
    found = find_nearby_texts((50, 0), index, texts, radius_mm=500, max_results=5)
    assert [item["content"] for item in found] == ["A", "B"]


def test_find_nearby_texts_empty() -> None:
    index = build_text_index([])
    assert find_nearby_texts((0, 0), index, []) == []


def test_find_nearby_texts_radius() -> None:
    texts = [_text("near", 500, 0), _text("far", 2000, 0)]
    found = find_nearby_texts((0, 0), build_text_index(texts), texts, radius_mm=1000)
    assert [item["content"] for item in found] == ["near"]


def test_enrich_elements() -> None:
    elements = [_element("e1", 0, 0), _element("e2", 5000, 0)]
    texts = [_text("P-1", 100, 0), _text("V-2", 300, 0), _text("BAÑO", 5000, 100), _text("COCINA", 5200, 0)]
    enrich_elements_with_nearby_text(elements, texts, radius_mm=800, max_results=3)
    assert [item["content"] for item in elements[0].metadata["nearby_texts"]] == ["P-1", "V-2"]
    assert [item["content"] for item in elements[1].metadata["nearby_texts"]] == ["BAÑO", "COCINA"]
