#!/usr/bin/env python3
"""One-off PDF output analyzer for final verification."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import fitz

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
OUT = REPO / "references" / "report_style" / "verification"


def analyze(path: Path) -> dict:
    doc = fitz.open(path)
    text = "\n".join(p.get_text("text") for p in doc)
    sizes = [(p.rect.width, p.rect.height) for p in doc]
    raw = path.read_bytes()
    doc.close()
    return {
        "pages": len(sizes),
        "landscape": sum(1 for w, h in sizes if w > h),
        "bytes": len(raw),
        "text": text,
        "has_svg_marker": b"clash-marker" in raw or b"#DC2626" in raw,
        "has_placeholder": "Vista de plano no disponible" in text,
    }


def main() -> None:
    files = {
        "TEST_01_human": OUT / "TEST_01_human.pdf",
        "TEST_01_technical": OUT / "TEST_01_technical.pdf",
        "SERENA18_human": OUT / "SERENA18_human.pdf",
        "SERENA18_technical": OUT / "SERENA18_technical.pdf",
        "TORTUGA_C40_human": OUT / "TORTUGA_C40_human.pdf",
        "TORTUGA_C40_technical": OUT / "TORTUGA_C40_technical.pdf",
    }
    for name, p in files.items():
        a = analyze(p)
        print(f"=== {name} ===")
        print(f"  path: {p}")
        print(f"  size: {a['bytes']} bytes | pages: {a['pages']} | landscape: {a['landscape']}")
        print(f"  svg_marker_bytes: {a['has_svg_marker']} | placeholder_text: {a['has_placeholder']}")

    for label in ("TEST_01_human", "SERENA18_human", "TORTUGA_C40_human"):
        t = analyze(files[label])["text"]
        print(f"--- {label} human checks ---")
        for key, ok in {
            "DUPLA": "DUPLA" in t,
            "Matriz de chequeo": "Matriz de chequeo" in t,
            "Entrega de planos corregidos": "Entrega de planos corregidos" in t,
            "DWG A/B labels": "DWG A" in t and "DWG B" in t,
            "no overwrite language": "no reemplazar" in t.lower(),
            "Comparación DWG sheets": "Comparación DWG" in t,
            "Z W commands": "Z W" in t,
            "Bitácora": "Bitácora" in t,
        }.items():
            print(f"  {'OK' if ok else 'MISS'}: {key}")

    for label in ("TEST_01_technical", "SERENA18_technical", "TORTUGA_C40_technical"):
        t = analyze(files[label])["text"]
        print(f"--- {label} technical checks ---")
        print(f"  {'OK' if 'Inventario analizado' not in t else 'FAIL'}: no Inventario analizado")
        print(f"  {'OK' if 'Indice de incidencias' in t else 'MISS'}: incident index")
        print(f"  {'OK' if 'Z W' in t else 'MISS'}: Z W commands")
        print(f"  {'OK' if 'Detalle tecnico' in t else 'MISS'}: detail sections")
        print(f"  markdown '---' count: {t.count('---')}")
        q = t.count("?")
        print(f"  '?' count: {q}")
        if q:
            for line in t.splitlines():
                if "?" in line:
                    print(f"    ? {line.strip()[:110]}")

    from coordination.reporting.element_loaders import load_elements_for_visual_reporting
    from coordination.reporting.human_report_pdf import prepare_clash_sheet_rows

    for run_name in ("serena18_analysis_06", "tortuga_c40_package_run"):
        run = REPO / "analysis_output" / run_name
        if not run.is_dir():
            continue
        primary = json.loads((run / "primary_incidents.json").read_text(encoding="utf-8"))
        context = json.loads((run / "coordination_report_context.json").read_text(encoding="utf-8"))
        rev = next((p.read_text(encoding="utf-8") for p in run.glob("REVISION_CLASHES*.md")), "")
        els = load_elements_for_visual_reporting(run / "elements_by_dwg.json")
        rows, _ = prepare_clash_sheet_rows(
            project_name=str(primary.get("project_name", run_name)),
            report_context=context,
            primary_payload=primary,
            all_elements=els,
            revision_md=rev,
        )
        vis = sum(1 for r in rows if r.has_visual)
        print(f"--- {run_name} panel stats ---")
        print(f"  elements loaded: {len(els)}")
        print(f"  incidents: {len(rows)} | geometry panels: {vis} | placeholder-only: {len(rows) - vis}")
    for bucket in ("critical", "high", "medium", "low"):
        print(f"  {bucket}: {sum(1 for r in rows if r.severity_bucket == bucket)}")


if __name__ == "__main__":
    main()
