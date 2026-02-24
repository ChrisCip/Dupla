import json
from pathlib import Path

dump = Path(r"c:\Users\chris\Documents\Dupla\analysis_output\dump")

# BC3
partidas = json.loads((dump / "bc3_partidas.json").read_text(encoding="utf-8"))
chapters = json.loads((dump / "bc3_chapters.json").read_text(encoding="utf-8"))
print(f"BC3: {len(partidas)} partidas, {len(chapters)} chapters")
for c in chapters[:8]:
    print(f"  CH: {c['code']}: {c['summary'][:60]}")
print()
for p in partidas[:15]:
    print(f"  {p['code']:<16} {p['unit']:<6} {p['price']:12.2f}  {p['summary'][:50]}")

# XLSX
xls = json.loads((dump / "xlsx_structure.json").read_text(encoding="utf-8"))
sheets = set(r["sheet"] for r in xls)
print(f"\nXLSX: {len(xls)} rows, sheets: {sheets}")
for r in xls[:25]:
    cells = [str(c)[:25] if c else "" for c in r["cells"][:8]]
    print(f"  [{r['sheet'][:10]}:{r['row']:3}] {'  |  '.join(cells)}")
