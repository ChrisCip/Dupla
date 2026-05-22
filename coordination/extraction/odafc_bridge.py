"""Bridge utilities for DWG conversion via ODA File Converter."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = REPO_ROOT / "analysis_output" / "odafc_cache"


def detect_oda_file_converter() -> Path | None:
    candidates = []
    for env_var in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = os.getenv(env_var)
        if not root:
            continue
        candidates.extend(
            [
                Path(root) / "ODA" / "ODAFileConverter" / "ODAFileConverter.exe",
                Path(root) / "ODA File Converter" / "ODAFileConverter.exe",
            ]
        )
    for path in candidates:
        if path.is_file():
            return path
    return None


def odafc_available() -> bool:
    return detect_oda_file_converter() is not None


def convert_to_dxf(
    source_dwg: Path,
    *,
    target_version: str = "ACAD2018",
    cache_dir: Path | None = None,
    timeout_seconds: int = 120,
) -> Path | None:
    converter = detect_oda_file_converter()
    if converter is None or not source_dwg.is_file():
        return None

    root = cache_dir or DEFAULT_CACHE_DIR
    source_hash = _file_hash(source_dwg)
    run_dir = root / f"{source_dwg.stem}_{source_hash[:12]}"
    input_dir = run_dir / "in"
    output_dir = run_dir / "out"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    staged_source = input_dir / source_dwg.name
    if not staged_source.is_file() or staged_source.stat().st_mtime < source_dwg.stat().st_mtime:
        shutil.copy2(source_dwg, staged_source)

    expected_dxf = output_dir / f"{source_dwg.stem}.dxf"
    if expected_dxf.is_file() and expected_dxf.stat().st_mtime >= source_dwg.stat().st_mtime:
        return expected_dxf

    # ODA CLI args: inDir outDir inVersion outVersion recurse audit [file_filter]
    cmd = [
        str(converter),
        str(input_dir),
        str(output_dir),
        "ACAD2018",
        target_version,
        "0",
        "1",
        source_dwg.name,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return expected_dxf if expected_dxf.is_file() else None


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
