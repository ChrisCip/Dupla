"""Run Day 3 calibration and A/B comparison for Dupla.

This script executes baseline and enhanced runs for selected disciplines,
performs threshold sweeps for the enhanced flow, computes comparison metrics,
and writes a consolidated markdown/json report with go/no-go decision.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from compare_budget import analyze_budget_pair


def _parse_thresholds(raw: str) -> list[float]:
    values: list[float] = []
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        values.append(float(token))
    unique_sorted = sorted(set(values))
    if not unique_sorted:
        raise ValueError("No threshold values provided")
    return unique_sorted


def _run_command(command: list[str], *, label: str) -> tuple[int, str, str]:
    print(f"[RUN] {label}")
    print("[CMD] " + " ".join(command))

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    combined_lines: list[str] = []
    if proc.stdout is not None:
        for line in proc.stdout:
            combined_lines.append(line)
            print(line.rstrip())

    return_code = proc.wait()
    combined_output = "".join(combined_lines)
    return return_code, combined_output, ""


def _extract_output_dir(output_text: str) -> str | None:
    # dupla_run_gebsa.py logs either "Output directory: <path>" or "Output: <path>"
    for line in reversed(output_text.splitlines()):
        match = re.search(r"Output(?:\s+directory)?:\s*(.+)$", line.strip(), flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _compute_metrics(generated_excel: Path, real_excel: Path) -> dict[str, Any]:
    stats = analyze_budget_pair(generated_excel, real_excel)
    return {
        "coverage": float(stats["coverage"]),
        "coverage_exact": float(stats.get("coverage_exact", stats["coverage"])),
        "mapped_coverage_pres_code": float(stats.get("mapped_coverage_pres_code", 0.0)),
        "qty_accuracy": float(stats["qty_accuracy"]),
        "mapped_qty_accuracy": float(stats.get("mapped_qty_accuracy", 0.0)),
        "price_accuracy": float(stats["price_accuracy"]),
        "mapped_price_accuracy": float(stats.get("mapped_price_accuracy", 0.0)),
        "semantic_avg_best_similarity": float(stats.get("semantic_avg_best_similarity", 0.0)),
        "semantic_match_rate_60": float(stats.get("semantic_match_rate_60", 0.0)),
        "semantic_match_rate_70": float(stats.get("semantic_match_rate_70", 0.0)),
        "matching_codes": len(stats["matching_codes"]),
        "matching_codes_exact": len(stats.get("matching_codes_exact", stats["matching_codes"])),
        "mapped_count": int(stats.get("mapped_count", 0)),
        "generated_partidas": len(stats["generated_partidas"]),
        "real_partidas": len(stats["real_partidas"]),
    }


def _build_runner_base_command(skip_aps: bool) -> list[str]:
    command = [sys.executable, str(REPO_ROOT / "dupla_run_gebsa.py")]
    if skip_aps:
        command.append("--skip-aps")
    return command


def _run_discipline(
    discipline: str,
    *,
    baseline_sources: list[str],
    enhanced_sources: list[str],
    min_source_quality: float,
    day2_validation_limit: int,
    skip_aps: bool,
    enhanced: bool,
) -> dict[str, Any]:
    command = _build_runner_base_command(skip_aps)
    command.extend(["--only", discipline])

    if enhanced:
        sources = enhanced_sources
        command.append("--day2-prep")
        command.extend(["--day2-validation-limit", str(day2_validation_limit)])
        command.extend(["--day2-min-source-quality", str(min_source_quality)])
        for source in sources:
            command.extend(["--day2-pres", source])
    else:
        sources = baseline_sources

    command.extend(["--training-min-source-quality", str(min_source_quality)])
    for source in sources:
        command.extend(["--training-pres", source])

    run_label = f"{'enhanced' if enhanced else 'baseline'} | {discipline} | min_quality={min_source_quality:.2f}"
    return_code, stdout, stderr = _run_command(command, label=run_label)
    output_dir = _extract_output_dir("\n".join([stdout, stderr]))

    return {
        "return_code": return_code,
        "stdout": stdout,
        "stderr": stderr,
        "output_dir": output_dir,
        "command": command,
    }


def _discipline_excel_from_run(output_dir: Path, discipline: str) -> Path:
    return output_dir / discipline / f"presupuesto_{discipline}.xlsx"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _write_report(
    output_path: Path,
    *,
    baseline: dict[str, dict[str, Any]],
    enhanced_by_threshold: dict[float, dict[str, dict[str, Any]]],
    winner_threshold: float,
    go_threshold: float,
    go_mode: str,
    go: bool,
    notes: list[str],
) -> None:
    winner = enhanced_by_threshold[winner_threshold]
    lines: list[str] = [
        "# Day 3 A/B Calibration Report",
        "",
        "## Scope",
        "",
        "- Disciplines: arquitectura, estructura",
        "- Comparison: baseline vs enhanced flow with threshold sweep",
        f"- Go mode: {go_mode}",
        f"- Go/No-Go threshold: +{go_threshold:.1f}% in both coverage and quantity accuracy",
        "",
        "## Column definitions",
        "",
        "- `coverage`: percentage of PRES real codes present by raw/normalized code overlap.",
        "- `mapped_coverage`: percentage of PRES real codes reached by inferred mapping (family+unit+similarity).",
        "- `coverage_exact`: strict exact-code coverage without normalization.",
        "- `qty_accuracy`: average quantity precision over matching codes.",
        "- `mapped_qty`: quantity precision over inferred mapped pairs.",
        "- `price_accuracy`: average unit-price precision over matching codes.",
        "- `semantic_avg`: average best textual similarity against PRES summaries.",
        "- `delta_cov`: enhanced coverage minus baseline coverage.",
        "- `delta_qty`: enhanced quantity accuracy minus baseline quantity accuracy.",
        "",
        f"## Winning threshold: {winner_threshold}",
        "",
        "| Discipline | Base cov_exact | Base mapped_cov | Enh mapped_cov | delta_mcov | Base mapped_qty | Enh mapped_qty | delta_mqty | Base semantic_avg | Enh semantic_avg |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for discipline in sorted(baseline):
        b = baseline[discipline]
        e = winner[discipline]
        lines.append(
            "| {d} | {bce:.2f}% | {bmc:.2f}% | {emc:.2f}% | {dmc:+.2f}% | {bmq:.2f}% | {emq:.2f}% | {dmq:+.2f}% | {bs:.2f}% | {es:.2f}% |".format(
                d=discipline,
                bce=b["coverage_exact"],
                bmc=b["mapped_coverage_pres_code"],
                emc=e["mapped_coverage_pres_code"],
                dmc=e["mapped_coverage_pres_code"] - b["mapped_coverage_pres_code"],
                bmq=b["mapped_qty_accuracy"],
                emq=e["mapped_qty_accuracy"],
                dmq=e["mapped_qty_accuracy"] - b["mapped_qty_accuracy"],
                bs=b["semantic_avg_best_similarity"],
                es=e["semantic_avg_best_similarity"],
            )
        )

    lines.extend([
        "",
        "## Threshold sweep summary",
        "",
        "| Threshold | Avg delta_cov | Avg delta_qty | Avg delta_price | Avg delta_semantic | Avg delta_mapped_cov | Avg delta_mapped_qty |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])

    for threshold in sorted(enhanced_by_threshold):
        candidate = enhanced_by_threshold[threshold]
        delta_cov = _mean([candidate[d]["coverage"] - baseline[d]["coverage"] for d in baseline])
        delta_qty = _mean([candidate[d]["qty_accuracy"] - baseline[d]["qty_accuracy"] for d in baseline])
        delta_price = _mean([candidate[d]["price_accuracy"] - baseline[d]["price_accuracy"] for d in baseline])
        delta_semantic = _mean(
            [
                candidate[d]["semantic_avg_best_similarity"] - baseline[d]["semantic_avg_best_similarity"]
                for d in baseline
            ]
        )
        delta_mapped_cov = _mean(
            [
                candidate[d]["mapped_coverage_pres_code"] - baseline[d]["mapped_coverage_pres_code"]
                for d in baseline
            ]
        )
        delta_mapped_qty = _mean(
            [
                candidate[d]["mapped_qty_accuracy"] - baseline[d]["mapped_qty_accuracy"]
                for d in baseline
            ]
        )
        lines.append(
            f"| {threshold:.2f} | {delta_cov:+.2f}% | {delta_qty:+.2f}% | {delta_price:+.2f}% | {delta_semantic:+.2f}% | {delta_mapped_cov:+.2f}% | {delta_mapped_qty:+.2f}% |"
        )

    lines.extend([
        "",
        "## Decision",
        "",
        f"- Result: {'GO' if go else 'NO-GO'}",
        "",
        "## Notes",
        "",
    ])
    if notes:
        lines.extend([f"- {note}" for note in notes])
    else:
        lines.append("- No additional notes.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Day 3 A/B calibration")
    parser.add_argument(
        "--disciplines",
        nargs="+",
        default=["arquitectura", "estructura"],
        help="Disciplines to run in A/B",
    )
    parser.add_argument(
        "--real-pres",
        default=str(REPO_ROOT / "data" / "PRES.xlsx"),
        help="Reference PRES workbook for comparison metrics",
    )
    parser.add_argument(
        "--baseline-pres",
        action="append",
        default=None,
        help="Baseline training source (repeatable). Defaults to data/PRES.xlsx",
    )
    parser.add_argument(
        "--enhanced-pres",
        action="append",
        default=None,
        help="Enhanced training sources (repeatable). Defaults to PRES + NASAS file",
    )
    parser.add_argument(
        "--thresholds",
        default="0.60,0.75,0.90",
        help="Comma-separated min_source_quality values for enhanced sweep",
    )
    parser.add_argument(
        "--day2-validation-limit",
        type=int,
        default=60,
        help="Validation limit passed to day2 prep when enhanced runs are executed",
    )
    parser.add_argument(
        "--go-threshold",
        type=float,
        default=10.0,
        help="Required improvement percentage for both coverage and qty_accuracy",
    )
    parser.add_argument(
        "--go-mode",
        choices=["mapped", "code"],
        default="mapped",
        help="Use mapped metrics or raw code metrics for GO/NO-GO decision",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "output" / "day3_ab"),
        help="Directory for Day 3 artifacts",
    )
    parser.add_argument(
        "--skip-aps",
        action="store_true",
        help="Forward --skip-aps to runner",
    )
    return parser


def main() -> None:
    args = _build_arg_parser().parse_args()

    real_pres = Path(args.real_pres).resolve()
    if not real_pres.exists():
        raise FileNotFoundError(f"Real PRES not found: {real_pres}")

    baseline_sources = args.baseline_pres or [str((REPO_ROOT / "data" / "PRES.xlsx").resolve())]
    enhanced_sources = args.enhanced_pres or [
        str((REPO_ROOT / "data" / "PRES.xlsx").resolve()),
        str((REPO_ROOT / "data" / "Prelimary Budget NASAS 9-2, 17-02-2026.xlsx").resolve()),
    ]
    thresholds = _parse_thresholds(args.thresholds)

    baseline_metrics: dict[str, dict[str, Any]] = {}
    enhanced_metrics: dict[float, dict[str, dict[str, Any]]] = {}
    notes: list[str] = []

    for discipline in args.disciplines:
        baseline_run = _run_discipline(
            discipline,
            baseline_sources=baseline_sources,
            enhanced_sources=enhanced_sources,
            min_source_quality=1.0,
            day2_validation_limit=args.day2_validation_limit,
            skip_aps=args.skip_aps,
            enhanced=False,
        )
        if baseline_run["return_code"] != 0:
            raise RuntimeError(
                f"Baseline run failed for {discipline}\nSTDOUT:\n{baseline_run['stdout']}\nSTDERR:\n{baseline_run['stderr']}"
            )
        if not baseline_run["output_dir"]:
            raise RuntimeError(f"Could not extract output directory for baseline run ({discipline})")

        baseline_excel = _discipline_excel_from_run(Path(baseline_run["output_dir"]), discipline)
        if not baseline_excel.exists():
            raise FileNotFoundError(f"Baseline excel not found: {baseline_excel}")
        baseline_metrics[discipline] = _compute_metrics(baseline_excel, real_pres)

    for threshold in thresholds:
        enhanced_metrics[threshold] = {}
        for discipline in args.disciplines:
            enhanced_run = _run_discipline(
                discipline,
                baseline_sources=baseline_sources,
                enhanced_sources=enhanced_sources,
                min_source_quality=threshold,
                day2_validation_limit=args.day2_validation_limit,
                skip_aps=args.skip_aps,
                enhanced=True,
            )
            if enhanced_run["return_code"] != 0:
                raise RuntimeError(
                    f"Enhanced run failed for {discipline} threshold={threshold}\nSTDOUT:\n{enhanced_run['stdout']}\nSTDERR:\n{enhanced_run['stderr']}"
                )
            if not enhanced_run["output_dir"]:
                raise RuntimeError(
                    f"Could not extract output directory for enhanced run ({discipline}, threshold={threshold})"
                )

            enhanced_excel = _discipline_excel_from_run(Path(enhanced_run["output_dir"]), discipline)
            if not enhanced_excel.exists():
                raise FileNotFoundError(f"Enhanced excel not found: {enhanced_excel}")
            enhanced_metrics[threshold][discipline] = _compute_metrics(enhanced_excel, real_pres)

    def score(threshold: float) -> tuple[float, float, float]:
        data = enhanced_metrics[threshold]
        cov_delta = _mean([data[d]["coverage"] - baseline_metrics[d]["coverage"] for d in baseline_metrics])
        qty_delta = _mean([data[d]["qty_accuracy"] - baseline_metrics[d]["qty_accuracy"] for d in baseline_metrics])
        mapped_cov_delta = _mean(
            [
                data[d]["mapped_coverage_pres_code"] - baseline_metrics[d]["mapped_coverage_pres_code"]
                for d in baseline_metrics
            ]
        )
        mapped_qty_delta = _mean(
            [
                data[d]["mapped_qty_accuracy"] - baseline_metrics[d]["mapped_qty_accuracy"]
                for d in baseline_metrics
            ]
        )
        semantic_delta = _mean(
            [
                data[d]["semantic_avg_best_similarity"] - baseline_metrics[d]["semantic_avg_best_similarity"]
                for d in baseline_metrics
            ]
        )
        if args.go_mode == "mapped":
            primary = mapped_cov_delta + mapped_qty_delta
        else:
            primary = cov_delta + qty_delta
        return primary, semantic_delta, mapped_cov_delta

    winner_threshold = max(thresholds, key=score)
    winner = enhanced_metrics[winner_threshold]

    go_by_discipline: list[bool] = []
    for discipline in sorted(baseline_metrics):
        if args.go_mode == "mapped":
            cov_delta = (
                winner[discipline]["mapped_coverage_pres_code"]
                - baseline_metrics[discipline]["mapped_coverage_pres_code"]
            )
            qty_delta = (
                winner[discipline]["mapped_qty_accuracy"]
                - baseline_metrics[discipline]["mapped_qty_accuracy"]
            )
            cov_label = "delta_mapped_cov"
            qty_label = "delta_mapped_qty"
        else:
            cov_delta = winner[discipline]["coverage"] - baseline_metrics[discipline]["coverage"]
            qty_delta = winner[discipline]["qty_accuracy"] - baseline_metrics[discipline]["qty_accuracy"]
            cov_label = "delta_cov"
            qty_label = "delta_qty"
        ok = cov_delta >= args.go_threshold and qty_delta >= args.go_threshold
        go_by_discipline.append(ok)
        notes.append(
            f"{discipline}: {cov_label}={cov_delta:+.2f}%, {qty_label}={qty_delta:+.2f}% -> {'OK' if ok else 'NO'}"
        )
    go = all(go_by_discipline)

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "day3_ab_report.md"
    _write_report(
        report_path,
        baseline=baseline_metrics,
        enhanced_by_threshold=enhanced_metrics,
        winner_threshold=winner_threshold,
        go_threshold=args.go_threshold,
        go_mode=args.go_mode,
        go=go,
        notes=notes,
    )

    summary = {
        "disciplines": args.disciplines,
        "real_pres": str(real_pres),
        "baseline_sources": baseline_sources,
        "enhanced_sources": enhanced_sources,
        "thresholds": thresholds,
        "winner_threshold": winner_threshold,
        "go_threshold": args.go_threshold,
        "go_mode": args.go_mode,
        "go": go,
        "baseline_metrics": baseline_metrics,
        "enhanced_metrics": enhanced_metrics,
        "report_path": str(report_path),
    }
    summary_path = output_dir / "day3_ab_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Day 3 A/B report: {report_path}")
    print(f"Day 3 A/B summary: {summary_path}")


if __name__ == "__main__":
    main()
