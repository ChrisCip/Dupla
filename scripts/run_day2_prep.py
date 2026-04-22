"""CLI entrypoint for Day 2 dataset preparation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.day2_prep import build_day2_dataset_artifacts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Day 2 training dataset artifacts")
    parser.add_argument(
        "--pres",
        action="append",
        default=None,
        help="PRES.xlsx source workbook (repeat flag to add multiple sources)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "output" / "day2_prep"),
        help="Directory to write the dataset bundle",
    )
    parser.add_argument(
        "--validation-limit",
        type=int,
        default=40,
        help="Maximum validation examples sampled from PRES",
    )
    parser.add_argument(
        "--min-source-quality",
        type=float,
        default=0.75,
        help="Minimum source quality score required to include a PRES source",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    pres_sources = args.pres or [str(REPO_ROOT / "data" / "PRES.xlsx")]
    manifest = build_day2_dataset_artifacts(
        pres_sources,
        args.output_dir,
        validation_limit=args.validation_limit,
        min_source_quality=args.min_source_quality,
    )
    print(manifest["report_path"])


if __name__ == "__main__":
    main()