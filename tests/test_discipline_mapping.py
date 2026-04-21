from budget.discipline_mapping import (
    ELECTRICAL,
    FINISHES_ARCH,
    GENERAL,
    SANITARY,
    STRUCTURAL,
    canonical_discipline_for_summary,
    chapter_prefixes_for,
    normalize_discipline_key,
)


def test_normalize_discipline_key() -> None:
    assert normalize_discipline_key("structural") == STRUCTURAL
    assert normalize_discipline_key("ESTRUCTURA") == STRUCTURAL
    assert normalize_discipline_key(None) == GENERAL


def test_canonical_discipline_for_summary() -> None:
    assert canonical_discipline_for_summary("Hormigón armado en vigas") == STRUCTURAL
    assert canonical_discipline_for_summary("Luminarias LED pasillo") == ELECTRICAL
    assert canonical_discipline_for_summary("Inodoros marca X") == SANITARY
    assert canonical_discipline_for_summary("Porcelanato 60x60") == FINISHES_ARCH


def test_chapter_prefixes_non_empty() -> None:
    assert "01" in chapter_prefixes_for(STRUCTURAL)
    assert "08.01" in chapter_prefixes_for(ELECTRICAL)
