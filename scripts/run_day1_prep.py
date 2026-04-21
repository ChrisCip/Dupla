"""Prepare the Day 1 training bundle for Dupla.

Produces a compact evaluation set, a manifest and a markdown report from a
PRES.xlsx source. Optionally compares a generated workbook against PRES.

Usage:
    python scripts/run_day1_prep.py --pres data/PRES.xlsx --output-dir output/day1
    python scripts/run_day1_prep.py --pres <Dropbox>/PRES.xlsx --generated output/run.xlsx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.day1_prep import build_day1_artifacts


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Day 1 dataset and baseline prep artifacts")
    parser.add_argument(
        "--pres",
        default=str(REPO_ROOT / "data" / "PRES.xlsx"),
        help="Path to the PRES.xlsx training source",
    )
    parser.add_argument(
        "--generated",
        default=None,
        help="Optional generated workbook to compare against PRES.xlsx",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "output" / "day1_prep"),
        help="Directory where the manifest, report and holdout set will be written",
    )
    parser.add_argument(
        "--holdout-limit",
        type=int,
        default=40,
        help="Maximum number of evaluation examples to sample from PRES",
    )
    return parser


def main() -> None:
    args = _build_arg_parser().parse_args()
    manifest = build_day1_artifacts(
        args.pres,
        args.output_dir,
        generated_path=args.generated,
        holdout_limit=args.holdout_limit,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
