from pathlib import Path

from openpyxl import Workbook

from analysis.day1_prep import build_day1_artifacts, select_holdout_pairs, summarize_training_pairs
from knowledge.training_data import extract_training_pairs


def _write_sample_pres(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Hoja1"
    sheet.append(["TORRE GIUALCA I"])
    sheet.append(["Presupuesto"])
    sheet.append(["Código", "Nat", "Ud", "Resumen", "CanPres", "PrPres", "ImpPres"])
    sheet.append(["TGIU0003", "Capítulo", "", "SEMISOTANO", 1, 1000, 1000])
    sheet.append(["P0303130", "Partida", "m3", "Zapata Z1", 7.56, 399.4, 3019.46])
    sheet.append(["P030320S", "Partida", "m3", "Columna C1", 10, 1055.26, 10552.6])
    sheet.append(["TGIU00305", "Capítulo", "", "TERMINACIÓN DE SUPERFICIES", 1, 100, 100])
    sheet.append(["P0501101", "Partida", "m2", "Pañete en muros interiores", 653.87, 8.4, 5492.51])
    sheet.append(["TGIU00406", "Capítulo", "", "TERMINACIÓN DE PISOS", 1, 300, 300])
    sheet.append(["P0610001", "Partida", "m2", "Piso Porcelanato Interior Apartamento", 20.37, 42.32, 862.06])
    workbook.save(path)


def test_select_holdout_pairs_balances_item_types(tmp_path: Path) -> None:
    pres_path = tmp_path / "PRES.xlsx"
    _write_sample_pres(pres_path)
    pairs = extract_training_pairs(pres_path)

    holdout = select_holdout_pairs(pairs, limit=3)

    assert len(holdout) == 3
    assert len({pair.input_item_type for pair in holdout}) == 3
    assert {pair.input_item_type for pair in holdout}.issubset(
        {"footing", "column", "wall_finish_plaster", "floor_finish"}
    )


def test_summarize_training_pairs_reports_expected_counts(tmp_path: Path) -> None:
    pres_path = tmp_path / "PRES.xlsx"
    _write_sample_pres(pres_path)
    pairs = extract_training_pairs(pres_path)

    summary = summarize_training_pairs(pairs)

    assert summary["total_pairs"] == 4
    assert summary["unique_item_types"] == 4
    assert summary["top_disciplines"][0][0] == "General"


def test_build_day1_artifacts_writes_manifest_and_report(tmp_path: Path) -> None:
    pres_path = tmp_path / "PRES.xlsx"
    generated_path = tmp_path / "generated.xlsx"
    output_dir = tmp_path / "day1"
    _write_sample_pres(pres_path)
    _write_sample_pres(generated_path)

    manifest = build_day1_artifacts(
        pres_path,
        output_dir,
        generated_path=generated_path,
        holdout_limit=3,
    )

    assert Path(manifest["manifest_path"]).exists()
    assert Path(manifest["holdout_path"]).exists()
    assert Path(manifest["report_path"]).exists()
    assert manifest["comparison"] is not None
    assert manifest["comparison"]["coverage"] == 100.0