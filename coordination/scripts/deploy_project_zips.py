#!/usr/bin/env python3
"""Extract SERENA / TORTUGA / NASAS zips from Downloads into Dupla layout."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOWNLOADS = Path.home() / "Downloads"


def extract_zip(
    zip_path: Path,
    dest_root: Path,
    *,
    strip_prefix: str = "",
) -> int:
    """Extract zip entries under dest_root. Returns extracted file count."""
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)
    dest_root.mkdir(parents=True, exist_ok=True)
    count = 0
    prefix = strip_prefix.replace("\\", "/")
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            name = member.filename.replace("\\", "/")
            if prefix:
                if not name.startswith(prefix):
                    continue
                rel = name[len(prefix) :].lstrip("/")
            else:
                rel = name.lstrip("/")
            if not rel or rel.endswith("/"):
                continue
            target = dest_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, target.open("wb") as out:
                out.write(src.read())
            count += 1
    return count


def _write_provisional_registry(path: Path, project_name: str, level_ids: list[str]) -> None:
    if path.is_file():
        return
    levels = [
        f'    {{"id": "{lid}", "name": "{lid}", "offset_to_project_zero_mm": {idx * 3200.0}, "provisional": true}}'
        for idx, lid in enumerate(level_ids)
    ]
    body = ",\n".join(levels)
    path.write_text(
        f'{{\n  "project_name": "{project_name}",\n  "levels": [\n{body}\n  ],\n  "level_aliases": {{}},\n  "view_level_patterns": [],\n  "source_exclude_patterns": []\n}}\n',
        encoding="utf-8",
    )


def deploy_serena(downloads: Path, repo: Path) -> Path:
    zip_path = downloads / "SERENA 18.zip"
    dest = repo / "repositorios" / "SERENA 18"
    n = extract_zip(zip_path, dest)
    print(f"  extracted {n} files")
    coord = dest / "coordination"
    coord.mkdir(parents=True, exist_ok=True)
    _write_provisional_registry(
        coord / "serena18_project_levels.json",
        "SERENA 18 — registro provisional de niveles para coordinacion 2.5D",
        ["NPT_P1", "NPT_P2", "SOTANO", "CIMENTACION", "TECHO"],
    )
    return dest


def deploy_tortuga(downloads: Path, repo: Path) -> Path:
    zip_path = downloads / "TORTUGA C40.zip"
    dest = repo / "repositorios" / "TORTUGA C40"
    n = extract_zip(zip_path, dest, strip_prefix="TORTUGA C40")
    print(f"  extracted {n} files")
    coord = dest / "coordination"
    coord.mkdir(parents=True, exist_ok=True)
    _write_provisional_registry(
        coord / "tortuga_c40_project_levels.json",
        "TORTUGA C40 — registro provisional de niveles para coordinacion 2.5D",
        ["NPT_P1"],
    )
    return dest


def deploy_nasas(downloads: Path, repo: Path) -> Path:
    zip_path = downloads / "NASAS 09.zip"
    dest = repo / "aps_integration" / "NASAS 09" / "NASAS arquitectura"
    n = extract_zip(zip_path, dest)
    print(f"  extracted {n} files")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy project zips from Downloads")
    parser.add_argument("--downloads", type=Path, default=DOWNLOADS)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--only", choices=("serena", "tortuga", "nasas", "all"), default="all")
    args = parser.parse_args()

    if args.only in ("tortuga", "all"):
        print("Extracting TORTUGA C40...")
        print("  ->", deploy_tortuga(args.downloads, args.repo))
    if args.only in ("nasas", "all"):
        print("Extracting NASAS 09...")
        print("  ->", deploy_nasas(args.downloads, args.repo))
    if args.only in ("serena", "all"):
        print("Extracting SERENA 18 (large archive)...")
        print("  ->", deploy_serena(args.downloads, args.repo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
