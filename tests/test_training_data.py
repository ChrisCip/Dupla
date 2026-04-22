from pathlib import Path

from openpyxl import Workbook

from knowledge.training_data import (
    extract_level_templates,
    extract_training_pairs,
    generate_few_shot_examples,
)


def _write_sample_pres(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Hoja1"
    sheet.append(["TORRE GIUALCA I"])
    sheet.append(["Presupuesto"])
    sheet.append(["Código", "Nat", "Ud", "Resumen", "CanPres", "PrPres", "ImpPres"])
    sheet.append(["TGIU0003", "Capítulo", "", "SEMISOTANO", 1, 1000, 1000])
    sheet.append(["TGIU00301", "Capítulo", "", "HORMIGON ARMADO", 1, 500, 500])
    sheet.append(["P0303130", "Partida", "m3", "Zapata Z1", 7.56, 399.4, 3019.46])
    sheet.append(["P030320S", "Partida", "m3", "Columna C1", 10, 1055.26, 10552.6])
    sheet.append(["TGIU00305", "Capítulo", "", "TERMINACIÓN DE SUPERFICIES", 1, 100, 100])
    sheet.append(["P0501101", "Partida", "m2", "Pañete en muros interiores", 653.87, 8.4, 5492.51])
    sheet.append(["TGIU0004", "Capítulo", "", "NIVEL 5", 1, 1200, 1200])
    sheet.append(["TGIU00406", "Capítulo", "", "TERMINACIÓN DE PISOS", 1, 300, 300])
    sheet.append(["P0610001", "Partida", "m2", "Piso Porcelanato Interior Apartamento", 20.37, 42.32, 862.06])
    workbook.save(path)


def _write_sample_nasas(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "NASAS"
    sheet.append([None, None, None, None, None, None, None, None])
    sheet.append([None, None, None, None, None, None, None, None])
    sheet.append([None, None, None, None, None, None, None, None])
    sheet.append([None, None, None, None, None, None, None, None])
    sheet.append([None, None, None, None, None, None, None, None])
    sheet.append(["C�digo", "Nat", "Resumen", "Resume", "CanPres", "Ud", "Pres", "ImpPres"])
    sheet.append(["NAS-9.1", "Capítulo", "COSTOS DIRECTOS", "DIRECT COSTS", 1, "UD", 915627.85, 915627.85])
    sheet.append(["1.00", "Capítulo", "Trabajos preliminares", "Preliminary Works", 1, "UD", 9292.49, 9292.49])
    sheet.append(["1.01", "Partida", "Fumigación", "Fumigation (foundations)", 2868.89, " M2", 1.5, 4303.34])
    sheet.append(["1.02", "Partida", "Limpieza del solar", "Lot cleaning", 1794.66, " M2", 2.78, 4989.15])
    workbook.save(path)


def test_extract_training_pairs_builds_structured_pairs(tmp_path: Path) -> None:
    pres_path = tmp_path / "PRES.xlsx"
    _write_sample_pres(pres_path)

    pairs = extract_training_pairs(pres_path)

    assert len(pairs) == 4
    assert pairs[0].input_item_type == "footing"
    assert pairs[0].output_bc3_code == "P0303130"
    assert "SEMISOTANO" in pairs[0].input_context
    assert pairs[2].input_item_type == "wall_finish_plaster"
    assert pairs[3].input_item_type == "floor_finish"


def test_extract_training_pairs_parses_nasas_format(tmp_path: Path) -> None:
    pres_path = tmp_path / "NASAS.xlsx"
    _write_sample_nasas(pres_path)

    pairs = extract_training_pairs(pres_path)

    assert len(pairs) == 2
    assert pairs[0].output_bc3_code == "1.01"
    assert pairs[0].input_unit.strip() == "M2"
    assert "Trabajos preliminares" in pairs[0].input_context


def test_extract_level_templates_groups_repeated_signatures(tmp_path: Path) -> None:
    pres_path = tmp_path / "PRES.xlsx"
    _write_sample_pres(pres_path)
    templates = extract_level_templates(pres_path)

    assert templates
    assert all(template.signature for template in templates)
    assert any("P0303130" in template.signature for template in templates)


def test_generate_few_shot_examples_filters_category(tmp_path: Path) -> None:
    pres_path = tmp_path / "PRES.xlsx"
    _write_sample_pres(pres_path)
    pairs = extract_training_pairs(pres_path)

    formatted = generate_few_shot_examples(pairs, "muros")

    assert "few-shot" in formatted.lower()
    assert "wall_finish_plaster" in formatted
