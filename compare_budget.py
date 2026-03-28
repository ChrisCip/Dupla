"""
Compare generated Dupla budget workbook against real PRES.xlsx baseline.

Usage:
    python compare_budget.py
    python compare_budget.py --generated "<path>" --real "./data/PRES.xlsx" --output-dir "<dir>"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        cleaned = str(value).replace(",", ".").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0


def _normalize(text: str) -> str:
    lowered = text.lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
        "�": "a",
    }
    for src, dst in replacements.items():
        lowered = lowered.replace(src, dst)
    return lowered


def _load_budget_rows(path: Path) -> list[dict[str, Any]]:
    workbook = load_workbook(path, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    rows: list[dict[str, Any]] = []
    for row in sheet.iter_rows(min_row=4, values_only=True):
        code = _safe_str(row[0] if len(row) > 0 else None)
        nat = _safe_str(row[1] if len(row) > 1 else None)
        unit = _safe_str(row[2] if len(row) > 2 else None)
        summary = _safe_str(row[3] if len(row) > 3 else None)
        qty = _safe_float(row[4] if len(row) > 4 else None)
        price = _safe_float(row[5] if len(row) > 5 else None)
        amount = _safe_float(row[6] if len(row) > 6 else None)
        if not any((code, nat, unit, summary)):
            continue
        rows.append(
            {
                "code": code,
                "nat": nat,
                "unit": unit,
                "summary": summary,
                "quantity": qty,
                "price": price,
                "amount": amount,
            }
        )
    return rows


def _is_partida(row: dict[str, Any]) -> bool:
    return "partida" in _normalize(str(row.get("nat", "")))


def _is_chapter(row: dict[str, Any]) -> bool:
    return "cap" in _normalize(str(row.get("nat", "")))


def _discipline_tags(text: str) -> set[str]:
    normalized = _normalize(text)
    tags: dict[str, tuple[str, ...]] = {
        "preliminares": ("prelimin",),
        "movimiento_tierra": ("movimiento de tierra", "excav", "relleno"),
        "hormigon_armado": ("hormigon", "hormigon armado", "concreto"),
        "acero_refuerzo": ("acero", "refuerzo", "varilla"),
        "muros_divisiones": ("muro", "bloque", "division"),
        "panete_revestimiento": ("panete", "pañete", "fraguache", "revest"),
        "pisos": ("piso", "porcelanato", "ceram", "zocalo"),
        "escaleras": ("escalera", "escalon"),
        "puertas": ("puerta",),
        "ventanas": ("ventana", "vidrio"),
        "ebanisteria": ("ebanister", "closet", "gabinete"),
        "electrico": ("electrico", "eléctrico", "luminaria", "tomacorr", "panel"),
        "sanitario": ("sanitario", "inodoro", "lavamanos", "plomer", "drenaje"),
        "pintura": ("pintura", "sellador", "imperme"),
        "techos_cubierta": ("techo", "cubierta"),
        "miscelaneos": ("miscelaneo", "miscelaneo"),
        "equipos_electricos": ("equipos electric",),
        "herreria": ("verja", "baranda", "herreria"),
        "impermeabilizacion": ("impermeabil",),
        "acabados": ("terminacion", "acabado"),
        "gastos_generales": ("gastos", "indirectos", "supervision"),
    }
    found: set[str] = set()
    for tag, hints in tags.items():
        if any(hint in normalized for hint in hints):
            found.add(tag)
    return found


def _line_precision(real_value: float, gen_value: float) -> float:
    if real_value == 0 and gen_value == 0:
        return 1.0
    if real_value == 0:
        return 0.0
    score = 1.0 - abs(gen_value - real_value) / abs(real_value)
    return max(0.0, min(1.0, score))


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def build_comparison_report(generated_path: Path, real_path: Path, output_dir: Path) -> Path:
    generated_rows = _load_budget_rows(generated_path)
    real_rows = _load_budget_rows(real_path)

    generated_partidas = [row for row in generated_rows if _is_partida(row)]
    real_partidas = [row for row in real_rows if _is_partida(row)]
    generated_chapters = [row for row in generated_rows if _is_chapter(row)]
    real_chapters = [row for row in real_rows if _is_chapter(row)]

    generated_by_code: dict[str, dict[str, Any]] = {
        _safe_str(row["code"]): row for row in generated_partidas if _safe_str(row["code"])
    }
    real_by_code: dict[str, dict[str, Any]] = {
        _safe_str(row["code"]): row for row in real_partidas if _safe_str(row["code"])
    }
    matching_codes = sorted(set(real_by_code) & set(generated_by_code))

    qty_precisions = [
        _line_precision(real_by_code[code]["quantity"], generated_by_code[code]["quantity"])
        for code in matching_codes
    ]
    price_precisions = [
        _line_precision(real_by_code[code]["price"], generated_by_code[code]["price"])
        for code in matching_codes
    ]

    generated_disciplines: set[str] = set()
    for row in generated_rows:
        generated_disciplines.update(_discipline_tags(row["summary"]))
    real_disciplines: set[str] = set()
    for row in real_rows:
        real_disciplines.update(_discipline_tags(row["summary"]))

    top20_real = sorted(real_partidas, key=lambda row: row["amount"], reverse=True)[:20]

    generated_non_empty_price = sum(1 for row in generated_partidas if row["price"] > 0)
    generated_non_empty_amount = sum(1 for row in generated_partidas if row["amount"] > 0)
    real_total = sum(row["amount"] for row in real_partidas)
    generated_total = sum(row["amount"] for row in generated_partidas)

    coverage = 100.0 * (len(matching_codes) / len(real_by_code)) if real_by_code else 0.0
    qty_accuracy = 100.0 * _mean(qty_precisions)
    price_accuracy = 100.0 * _mean(price_precisions)

    lines = [
        "COMPARISON REPORT - DUPLA VS PRES.xlsx",
        "",
        f"Generated workbook: {generated_path}",
        f"Real workbook: {real_path}",
        "",
        "1) High-level counts",
        f"- Partidas generated: {len(generated_partidas)} | real: {len(real_partidas)} (expected ~1565)",
        f"- Chapters generated: {len(generated_chapters)} | real: {len(real_chapters)} (expected ~296)",
        (
            f"- Disciplines covered: {len(generated_disciplines)} | "
            f"real: {len(real_disciplines)} (expected ~21)"
        ),
        "",
        "2) Price/amount completeness in generated",
        f"- Rows with PrPres > 0: {generated_non_empty_price}/{len(generated_partidas)}",
        f"- Rows with ImpPres > 0: {generated_non_empty_amount}/{len(generated_partidas)}",
        "",
        "3) Matching quality by code",
        f"- Matching codes: {len(matching_codes)}",
        f"- Coverage of real partidas by generated equivalent: {coverage:.2f}%",
        f"- Quantity precision (only matched codes): {qty_accuracy:.2f}%",
        f"- Price precision (only matched codes): {price_accuracy:.2f}%",
        "",
        "4) Totals",
        f"- Generated total (sum ImpPres): {generated_total:,.2f}",
        f"- Real total (sum ImpPres): {real_total:,.2f} (reference target: 4,404,786 USD)",
        f"- Delta generated-real: {generated_total - real_total:,.2f}",
        "",
        "5) Missing disciplines (in generated vs real)",
    ]
    missing_disciplines = sorted(real_disciplines - generated_disciplines)
    if missing_disciplines:
        lines.extend(f"- {discipline}" for discipline in missing_disciplines)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "6) Top 20 real partidas by amount vs generated",
        ]
    )
    for row in top20_real:
        code = row["code"]
        gen = generated_by_code.get(code)
        if gen is None:
            lines.append(
                f"- {code}: real_amount={row['amount']:,.2f} | generated=NOT_FOUND | summary={row['summary']}"
            )
            continue
        qty_score = 100.0 * _line_precision(row["quantity"], gen["quantity"])
        price_score = 100.0 * _line_precision(row["price"], gen["price"])
        lines.append(
            (
                f"- {code}: real_amount={row['amount']:,.2f} | gen_amount={gen['amount']:,.2f} | "
                f"qty_precision={qty_score:.2f}% | price_precision={price_score:.2f}%"
            )
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "comparison_report.txt"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _resolve_defaults() -> tuple[Path, Path, Path]:
    repo_root = Path(__file__).resolve().parent
    run_summary = Path(r"C:\Users\chris\Downloads\archivos dupla\dwg\run_summary.json")
    if run_summary.exists():
        payload = json.loads(run_summary.read_text(encoding="utf-8"))
        generated = Path(payload["budget_excel"])
        output_dir = generated.parent
        real = repo_root / "data" / "PRES.xlsx"
        return generated, real, output_dir
    return (
        repo_root / "output" / "dupla_budget_ready_full.xlsx",
        repo_root / "data" / "PRES.xlsx",
        repo_root / "output",
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare generated budget vs PRES.xlsx")
    defaults_generated, defaults_real, defaults_output = _resolve_defaults()
    parser.add_argument("--generated", default=str(defaults_generated))
    parser.add_argument("--real", default=str(defaults_real))
    parser.add_argument("--output-dir", default=str(defaults_output))
    return parser


def main() -> None:
    args = _build_arg_parser().parse_args()
    generated = Path(args.generated).resolve()
    real = Path(args.real).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not generated.exists():
        raise FileNotFoundError(f"Generated workbook not found: {generated}")
    if not real.exists():
        raise FileNotFoundError(f"Real workbook not found: {real}")

    report_path = build_comparison_report(generated, real, output_dir)
    print(f"Comparison report written to: {report_path}")


if __name__ == "__main__":
    main()
