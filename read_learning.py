"""Read and dump the XLSX + BC3 structure for analysis."""
import json, openpyxl
from pathlib import Path
from collections import defaultdict

DUMP = Path(r"c:\Users\chris\Documents\Dupla\analysis_output\dump")
DUMP.mkdir(parents=True, exist_ok=True)

# ============================================================
# 1. READ XLSX
# ============================================================
print("=" * 70)
print("READING PRES.xlsx")
print("=" * 70)

wb = openpyxl.load_workbook(
    r"c:\Users\chris\Documents\Dupla\learning_input\PRES.xlsx",
    read_only=True, data_only=True
)

xls_dump = []

for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    
    print(f"\nSheet: '{sheet_name}' ({len(rows)} rows)")
    
    # Show first 30 rows for structure analysis
    for i, row in enumerate(rows[:40]):
        cells = [str(c)[:40] if c is not None else "" for c in row[:12]]
        row_str = " | ".join(cells)
        print(f"  [{i:>3}] {row_str}")
        xls_dump.append({"sheet": sheet_name, "row": i, "cells": [str(c) if c is not None else None for c in row[:12]]})

wb.close()

# Save dump
with open(DUMP / "xlsx_structure.json", "w", encoding="utf-8") as f:
    json.dump(xls_dump, f, ensure_ascii=False, indent=2, default=str)

# ============================================================
# 2. READ BC3
# ============================================================
print(f"\n{'=' * 70}")
print("READING TGIU.bc3")
print("=" * 70)

raw = Path(r"c:\Users\chris\Documents\Dupla\learning_input\TGIU.bc3").read_text(
    encoding="latin-1", errors="replace"
)
print(f"Size: {len(raw):,} chars")

# Parse records
records = []
current = ""
for line in raw.split("\n"):
    line = line.strip()
    if line.startswith("~"):
        if current:
            records.append(current)
        current = line
    else:
        current += line
if current:
    records.append(current)

# Count record types
from collections import Counter
types = Counter(r[1] if len(r) > 1 else "?" for r in records)
print(f"Records: {len(records)}")
print(f"Types: {dict(types)}")

# Parse concepts
concepts = {}
for r in records:
    if not r.startswith("~C|"):
        continue
    parts = r[3:].split("|")
    if len(parts) < 2:
        continue
    code = parts[0].split("#")[0].strip()
    parents = parts[0].split("#", 1)[1] if "#" in parts[0] else ""
    unit = parts[1].strip() if len(parts) > 1 else ""
    summary = parts[2].strip() if len(parts) > 2 else ""
    price = 0.0
    if len(parts) > 3 and parts[3].strip():
        try: price = float(parts[3].strip())
        except: pass
    
    if code:
        concepts[code] = {
            "code": code, "unit": unit, "summary": summary,
            "price": price, "parents": parents,
        }

# Show partidas
partidas = [c for c in concepts.values() if c["price"] > 0 and c["unit"]]
chapters = [c for c in concepts.values() if not c["unit"] and c["summary"]]

print(f"\nConcepts: {len(concepts)}")
print(f"Partidas with price: {len(partidas)}")
print(f"Chapters: {len(chapters)}")

print(f"\nFirst 30 chapters:")
for ch in sorted(chapters, key=lambda x: x["code"])[:30]:
    print(f"  {ch['code']:<25} {ch['summary'][:60]}")

print(f"\nFirst 40 partidas:")
for p in sorted(partidas, key=lambda x: x["code"])[:40]:
    print(f"  {p['code']:<16} {p['unit']:<6} {p['price']:>12,.2f}  {p['summary'][:50]}")

# Save dump
with open(DUMP / "bc3_partidas.json", "w", encoding="utf-8") as f:
    json.dump(partidas, f, ensure_ascii=False, indent=2)
with open(DUMP / "bc3_chapters.json", "w", encoding="utf-8") as f:
    json.dump(chapters, f, ensure_ascii=False, indent=2)

print(f"\nDumped to: {DUMP}")
