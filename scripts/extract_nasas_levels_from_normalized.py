#!/usr/bin/env python3
"""
Extrae cotas tipo «N ±x.xx» del JSON CAD normalizado NASAS y las imprime en orden.

No modifica el repo; sirve para auditar o regenerar `sample_project_levels.json`.

  python scripts/extract_nasas_levels_from_normalized.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_JSON = (
    REPO
    / "aps_integration"
    / "NASAS 09"
    / "outputs"
    / "corridas"
    / "_cad_merge"
    / "27.11.2025 LAS NASAS 09, DUPLA.normalized.json"
)


def _walk_collect_content(obj: object, out: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "content" and isinstance(v, str):
                out.append(v)
            else:
                _walk_collect_content(v, out)
    elif isinstance(obj, list):
        for i in obj:
            _walk_collect_content(i, out)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSON
    if not path.is_file():
        print("No existe:", path, file=sys.stderr)
        sys.exit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    texts: list[str] = []
    _walk_collect_content(data, texts)
    pat = re.compile(r"\bN\s*([+-]?[0-9]+(?:[.,][0-9]+)?)", re.I)
    found: set[float] = set()
    for t in texts:
        for m in pat.finditer(t):
            s = m.group(1).replace(",", ".")
            try:
                found.add(float(s))
            except ValueError:
                pass
    for v in sorted(found):
        mm = round(v * 1000.0, 6)
        print(f"N {v:+.5g} m  ->  {mm:+.1f} mm")


if __name__ == "__main__":
    main()
