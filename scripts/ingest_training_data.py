"""
Training data ingestion from a folder of completed budget files (Dropbox).

Usage
-----
    python scripts/ingest_training_data.py --folder /path/to/dropbox/presupuestos
    python scripts/ingest_training_data.py --folder ./data --output ./knowledge/cache/corpus.jsonl
    python scripts/ingest_training_data.py --files ./data/PRES.xlsx ./data/OBRA2.xlsx

The script scans the given folder for XLSX files, extracts budget training pairs
from each, deduplicates, and writes:
- A JSONL corpus file (for fine-tuning / offline analysis)
- A summary JSON with statistics per source file

This supports the multi-project training workflow where the client provides
completed budgets from Dropbox for each obra/project.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

# Ensure repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from knowledge.training_data import (
    TrainingPair,
    export_corpus_jsonl,
    extract_training_pairs,
    load_training_corpus,
    load_training_corpus_from_folder,
)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stdout,
    )


def _print_summary(pairs: list[TrainingPair], output_jsonl: Path, summary_path: Path) -> None:
    type_counts: Counter[str] = Counter(p.input_item_type for p in pairs)
    unit_counts: Counter[str] = Counter(p.output_unit.lower() for p in pairs if p.output_unit)
    source_counts: Counter[str] = Counter(p.source for p in pairs)
    discipline_counts: Counter[str] = Counter()
    for p in pairs:
        _, _, disc = p.input_context.partition("|")
        discipline_counts[disc.strip() or "General"] += 1

    summary = {
        "total_pairs": len(pairs),
        "by_item_type": dict(type_counts.most_common()),
        "by_unit": dict(unit_counts.most_common(20)),
        "by_source_file": dict(source_counts.most_common()),
        "by_discipline": dict(discipline_counts.most_common()),
        "output_jsonl": str(output_jsonl),
    }

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Training Corpus Summary ===")
    print(f"Total pairs      : {len(pairs)}")
    print(f"Source files     : {len(source_counts)}")
    print(f"Item types       : {', '.join(f'{t}({c})' for t, c in type_counts.most_common(8))}")
    print(f"Top units        : {', '.join(f'{u}({c})' for u, c in unit_counts.most_common(6))}")
    print(f"Disciplines      : {', '.join(f'{d}({c})' for d, c in discipline_counts.most_common(6))}")
    print(f"\nJSONL output     : {output_jsonl}")
    print(f"Summary JSON     : {summary_path}")


def _stats_per_file(paths: list[Path]) -> None:
    """Print per-file statistics before deduplication."""
    print("\n=== Per-file statistics ===")
    for path in paths:
        if not path.exists():
            print(f"  [MISSING] {path.name}")
            continue
        try:
            pairs = extract_training_pairs(path)
            type_counts = Counter(p.input_item_type for p in pairs)
            top = ", ".join(f"{t}({c})" for t, c in type_counts.most_common(4))
            print(f"  {path.name:40s} — {len(pairs):4d} pairs | {top}")
        except Exception as exc:
            print(f"  [ERROR] {path.name}: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest construction budget XLSX files into Dupla training corpus."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--folder",
        metavar="DIR",
        help="Folder to scan for XLSX budget files (e.g., Dropbox presupuestos folder).",
    )
    source_group.add_argument(
        "--files",
        metavar="FILE",
        nargs="+",
        help="Explicit list of XLSX files to ingest.",
    )
    parser.add_argument(
        "--pattern",
        default="*.xlsx",
        help="Glob pattern for folder scan (default: *.xlsx). Use '**/*.xlsx' for recursive.",
    )
    parser.add_argument(
        "--output",
        default="./knowledge/cache/training_corpus.jsonl",
        metavar="JSONL",
        help="Output JSONL file path (default: ./knowledge/cache/training_corpus.jsonl).",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Disable deduplication (keep all pairs, including identical codes across files).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)
    logger = logging.getLogger("dupla.ingest")

    output_jsonl = (_REPO_ROOT / args.output).resolve()
    summary_path = output_jsonl.with_suffix(".summary.json")
    deduplicate = not args.no_dedup

    if args.folder:
        folder = (_REPO_ROOT / args.folder).resolve()
        logger.info("Scanning folder: %s (pattern=%r)", folder, args.pattern)
        from knowledge.training_data import load_training_corpus_from_folder

        pairs = load_training_corpus_from_folder(
            folder,
            pattern=args.pattern,
            deduplicate=deduplicate,
        )
    else:
        xlsx_paths = [(_REPO_ROOT / f).resolve() for f in args.files]
        _stats_per_file(xlsx_paths)
        pairs = load_training_corpus(xlsx_paths, deduplicate=deduplicate)

    if not pairs:
        logger.error("No training pairs extracted. Check that the XLSX files use the PRES format.")
        return 1

    export_corpus_jsonl(pairs, output_jsonl)
    _print_summary(pairs, output_jsonl, summary_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
