import json
from pathlib import Path

from openpyxl import Workbook

from knowledge.training_data import (
    export_corpus_jsonl,
    extract_level_templates,
    extract_training_pairs,
    generate_few_shot_examples,
    load_training_corpus,
    load_training_corpus_from_folder,
)


def _write_sample_pres(path: Path, *, project_prefix: str = "TGIU") -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Hoja1"
    sheet.append(["TORRE GIUALCA I"])
    sheet.append(["Presupuesto"])
    sheet.append(["Código", "Nat", "Ud", "Resumen", "CanPres", "PrPres", "ImpPres"])
    sheet.append([f"{project_prefix}0003", "Capítulo", "", "SEMISOTANO", 1, 1000, 1000])
    sheet.append([f"{project_prefix}00301", "Capítulo", "", "HORMIGON ARMADO", 1, 500, 500])
    sheet.append(["P0303130", "Partida", "m3", "Zapata Z1", 7.56, 399.4, 3019.46])
    sheet.append(["P030320S", "Partida", "m3", "Columna C1", 10, 1055.26, 10552.6])
    sheet.append([f"{project_prefix}00305", "Capítulo", "", "TERMINACIÓN DE SUPERFICIES", 1, 100, 100])
    sheet.append(["P0501101", "Partida", "m2", "Pañete en muros interiores", 653.87, 8.4, 5492.51])
    sheet.append([f"{project_prefix}0004", "Capítulo", "", "NIVEL 5", 1, 1200, 1200])
    sheet.append([f"{project_prefix}00406", "Capítulo", "", "TERMINACIÓN DE PISOS", 1, 300, 300])
    sheet.append(["P0610001", "Partida", "m2", "Piso Porcelanato Interior Apartamento", 20.37, 42.32, 862.06])
    workbook.save(path)


def _write_unique_pres(path: Path) -> None:
    """Write a PRES file with codes that don't overlap with _write_sample_pres."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Hoja1"
    sheet.append(["OBRA NUEVA"])
    sheet.append(["Presupuesto"])
    sheet.append(["Código", "Nat", "Ud", "Resumen", "CanPres", "PrPres", "ImpPres"])
    sheet.append(["OBRA0001", "Capítulo", "", "NIVEL 1", 1, 500, 500])
    sheet.append(["OBRA00011", "Capítulo", "", "PISOS", 1, 300, 300])
    sheet.append(["PX001001", "Partida", "m2", "Porcelanato 60x60 rectificado", 45.0, 55.0, 2475.0])
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


# ---------------------------------------------------------------------------
# Multi-source corpus tests
# ---------------------------------------------------------------------------

def test_load_training_corpus_merges_multiple_files(tmp_path: Path) -> None:
    path1 = tmp_path / "PRES1.xlsx"
    path2 = tmp_path / "PRES2.xlsx"
    _write_sample_pres(path1, project_prefix="AAA")
    _write_unique_pres(path2)

    corpus = load_training_corpus([path1, path2])

    # Both files contribute pairs
    assert len(corpus) >= 4  # at least the 4 from PRES1
    sources = {p.source for p in corpus}
    assert "PRES1.xlsx" in sources
    assert "PRES2.xlsx" in sources


def test_load_training_corpus_deduplicates_by_code_and_desc(tmp_path: Path) -> None:
    path1 = tmp_path / "PRES1.xlsx"
    path2 = tmp_path / "PRES2.xlsx"
    # Both files have the same content → all duplicates should be removed
    _write_sample_pres(path1, project_prefix="AAA")
    _write_sample_pres(path2, project_prefix="BBB")

    corpus_dedup = load_training_corpus([path1, path2], deduplicate=True)
    corpus_all = load_training_corpus([path1, path2], deduplicate=False)

    assert len(corpus_dedup) < len(corpus_all)
    # Deduped corpus must equal the number of unique (code, desc) pairs from one file
    single_file_pairs = extract_training_pairs(path1)
    unique_keys = {(p.output_bc3_code, p.output_description) for p in single_file_pairs}
    assert len(corpus_dedup) == len(unique_keys)


def test_load_training_corpus_skips_missing_files(tmp_path: Path) -> None:
    valid_path = tmp_path / "PRES.xlsx"
    _write_sample_pres(valid_path)
    missing_path = tmp_path / "NONEXISTENT.xlsx"

    corpus = load_training_corpus([valid_path, missing_path])

    assert len(corpus) == 4  # only from the valid file


def test_load_training_corpus_from_folder(tmp_path: Path) -> None:
    _write_sample_pres(tmp_path / "OBRA1.xlsx", project_prefix="O1")
    _write_unique_pres(tmp_path / "OBRA2.xlsx")

    corpus = load_training_corpus_from_folder(tmp_path)

    assert len(corpus) >= 4
    sources = {p.source for p in corpus}
    assert "OBRA1.xlsx" in sources
    assert "OBRA2.xlsx" in sources


def test_load_training_corpus_from_folder_missing_raises(tmp_path: Path) -> None:
    import pytest
    with pytest.raises(NotADirectoryError):
        load_training_corpus_from_folder(tmp_path / "doesnotexist")


def test_export_corpus_jsonl_produces_valid_jsonl(tmp_path: Path) -> None:
    pres_path = tmp_path / "PRES.xlsx"
    _write_sample_pres(pres_path)
    pairs = extract_training_pairs(pres_path)

    out_path = tmp_path / "corpus.jsonl"
    result = export_corpus_jsonl(pairs, out_path)

    assert result == out_path
    assert out_path.exists()

    lines = out_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(pairs)

    for line in lines:
        record = json.loads(line)
        assert "messages" in record
        assert len(record["messages"]) == 3
        assert record["messages"][0]["role"] == "system"
        assert record["messages"][2]["role"] == "assistant"
        payload = json.loads(record["messages"][2]["content"])
        assert "bc3_code" in payload
        assert "price" in payload
