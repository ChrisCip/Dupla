from knowledge.methodology_generator import generate_methodology_context
from knowledge.training_data import TrainingPair


def _sample_pairs() -> list[TrainingPair]:
    return [
        TrainingPair(
            input_item_type="footing",
            input_unit="m3",
            input_context="SEMISOTANO | HORMIGON ARMADO",
            output_bc3_code="P0303130",
            output_description="Zapata Z1",
            output_unit="m3",
            output_quantity=7.56,
            output_price=399.4,
        ),
        TrainingPair(
            input_item_type="wall_finish_plaster",
            input_unit="m2",
            input_context="SEMISOTANO | TERMINACIÓN DE SUPERFICIES",
            output_bc3_code="P0501101",
            output_description="Pañete en muros interiores",
            output_unit="m2",
            output_quantity=653.87,
            output_price=8.4,
        ),
        TrainingPair(
            input_item_type="floor_finish",
            input_unit="m2",
            input_context="NIVEL 5 | TERMINACIÓN DE PISOS",
            output_bc3_code="P0610001",
            output_description="Piso Porcelanato Interior Apartamento",
            output_unit="m2",
            output_quantity=20.37,
            output_price=42.32,
        ),
        TrainingPair(
            input_item_type="fixture_count",
            input_unit="u",
            input_context="NIVEL 5 | INSTALACIONES ELÉCTRICAS",
            output_bc3_code="E0101001",
            output_description="Tomacorriente doble 120V",
            output_unit="u",
            output_quantity=12.0,
            output_price=25.0,
        ),
    ]


def _sample_bc3() -> dict:
    return {
        "items": [
            {"code": "P0303130", "unit": "m3", "price": 399.4, "summary": "Zapata Z1"},
            {"code": "P0501101", "unit": "m2", "price": 8.4, "summary": "Pañete muros int"},
            {"code": "P0610001", "unit": "m2", "price": 42.32, "summary": "Piso porcelanato"},
        ],
        "chapters": [
            {"code": "01", "summary": "MOVIMIENTO DE TIERRAS"},
            {"code": "02", "summary": "HORMIGON ARMADO"},
            {"code": "03", "summary": "MUROS Y PANETE"},
        ],
    }


def test_generates_nonempty_from_pres_and_bc3() -> None:
    text = generate_methodology_context(
        training_pairs=_sample_pairs(),
        bc3_catalog=_sample_bc3(),
    )
    assert len(text) > 200
    assert "PRESUPUESTO DE REFERENCIA" in text
    assert "CATÁLOGO BC3" in text
    assert "Zapata" in text
    assert "footing" in text
    assert "m3" in text


def test_generates_from_pres_only() -> None:
    text = generate_methodology_context(
        training_pairs=_sample_pairs(),
        bc3_catalog=None,
    )
    assert "PRESUPUESTO DE REFERENCIA" in text
    assert "CATÁLOGO BC3" not in text


def test_generates_from_bc3_only() -> None:
    text = generate_methodology_context(
        training_pairs=None,
        bc3_catalog=_sample_bc3(),
    )
    assert "CATÁLOGO BC3" in text
    assert "PRESUPUESTO DE REFERENCIA" not in text


def test_returns_empty_when_no_data() -> None:
    assert generate_methodology_context() == ""
    assert generate_methodology_context(training_pairs=[], bc3_catalog={}) == ""


def test_truncates_when_over_limit() -> None:
    pairs = _sample_pairs() * 500
    text = generate_methodology_context(training_pairs=pairs, max_chars=500)
    assert len(text) <= 600
    assert "truncado" in text.lower()


def test_discipline_filter_focuses_on_matching_discipline() -> None:
    pairs = _sample_pairs()
    text_all = generate_methodology_context(training_pairs=pairs)
    text_elec = generate_methodology_context(training_pairs=pairs, discipline="Eléctrico")

    # Filtered context should mention the discipline
    assert "Eléctrico" in text_elec or "INSTALACIONES ELÉCTRICAS" in text_elec.upper()
    # Electrical items should appear in filtered view
    assert "Tomacorriente" in text_elec

    # Global context always lists all disciplines
    assert "Disciplinas encontradas" in text_all


def test_discipline_filter_label_in_header() -> None:
    text = generate_methodology_context(
        training_pairs=_sample_pairs(),
        discipline="Arquitectura",
    )
    assert "Arquitectura" in text
