from coordination.extraction.from_dwg_com import _bbox_footprint_mm, _skip_entity


def test_bbox_footprint_mm_builds_rectangle_and_applies_translation():
    result = _bbox_footprint_mm(
        min_pt=(1.0, 2.0, 0.0),
        max_pt=(4.0, 6.0, 0.0),
        factor_mm=1000.0,
        translation_mm=(10.0, -20.0),
    )
    assert result is not None
    footprint, area = result
    assert footprint == [
        (1010.0, 1980.0),
        (4010.0, 1980.0),
        (4010.0, 5980.0),
        (1010.0, 5980.0),
    ]
    assert area == 12_000_000.0


def test_skip_entity_filters_annotation_and_title_layers():
    assert _skip_entity("TEXT", "A-ANNO")
    assert _skip_entity("INSERT", "A-ANNO-TEXT")
    assert _skip_entity("INSERT", "E Leyenda")
    assert _skip_entity("INSERT", "A-TARJETA")
    assert not _skip_entity("INSERT", "S-COLS")
