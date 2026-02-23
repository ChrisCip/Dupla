"""
Parser de archivos BC3 (FIEBDC) exportados de Presto.

El formato FIEBDC usa registros con prefijo ~LETRA|
Registros clave:
  ~V  Versión del formato
  ~K  Coeficientes generales
  ~C  Conceptos (capitulos, partidas, precios unitarios)
  ~D  Descomposición (componentes de cada concepto)
  ~T  Textos largos
  ~M  Mediciones
  ~Y  Añadidos
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BC3_PATH = Path(r"c:\Users\chris\Documents\Dupla\presto_files\CTXI0000TRM.bc3")
OUT_DIR = Path(r"c:\Users\chris\Documents\Dupla\presto_files")

print("=" * 70)
print("PARSER BC3 (FIEBDC) - PRESTO 8.8")
print("=" * 70)

# Read file with latin-1 encoding (FIEBDC standard)
raw = BC3_PATH.read_text(encoding="latin-1", errors="replace")
print(f"Archivo: {BC3_PATH.name} ({len(raw):,} chars)")

# Split into records (each starts with ~)
# BC3 records can span multiple lines, ending at the next ~
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

print(f"Total registros: {len(records)}")

# Classify records
record_types = defaultdict(int)
for r in records:
    if len(r) > 1:
        record_types[r[1]] += 1

print("Tipos de registro:")
for t, count in sorted(record_types.items()):
    print(f"  ~{t}: {count}")

# ============================================================
# Parse ~C records (Conceptos)
# Format: ~C|CODE#CODE_PARENT\CODE_PARENT|UNIT|SUMMARY|PRICE_1|DATE|TYPE|
# ============================================================
concepts = {}  # code -> {unit, summary, price, type}

for r in records:
    if not r.startswith("~C|"):
        continue
    
    parts = r[3:].split("|")
    if len(parts) < 2:
        continue
    
    # First field: CODE#PARENT\PARENT or CODE#
    code_field = parts[0]
    code = code_field.split("#")[0].strip()
    parents = ""
    if "#" in code_field:
        parents = code_field.split("#", 1)[1]
    
    unit = parts[1].strip() if len(parts) > 1 else ""
    summary = parts[2].strip() if len(parts) > 2 else ""
    
    # Price
    price = 0.0
    if len(parts) > 3 and parts[3].strip():
        try:
            price = float(parts[3].strip())
        except ValueError:
            pass
    
    # Date
    date = parts[4].strip() if len(parts) > 4 else ""
    
    # Type
    ctype = parts[5].strip() if len(parts) > 5 else ""
    
    if code:
        concepts[code] = {
            "code": code,
            "unit": unit,
            "summary": summary,
            "price": price,
            "date": date,
            "type": ctype,
            "parents": parents,
        }

print(f"\nConceptos (~C): {len(concepts)}")

# ============================================================
# Parse ~D records (Descomposición / jerarquia)
# Format: ~D|PARENT_CODE#|CHILD_CODE\FACTOR\YIELD|CHILD_CODE\...|
# ============================================================
hierarchy = defaultdict(list)  # parent -> [(child, factor, yield)]

for r in records:
    if not r.startswith("~D|"):
        continue
    
    parts = r[3:].split("|")
    if len(parts) < 2:
        continue
    
    parent = parts[0].replace("#", "").strip()
    children_raw = parts[1] if len(parts) > 1 else ""
    
    for child_entry in children_raw.split("\\"):
        child_entry = child_entry.strip()
        if child_entry and child_entry != parent:
            # Children can have factor and yield after backslash
            hierarchy[parent].append(child_entry)

print(f"Relaciones padre-hijo (~D): {len(hierarchy)}")

# ============================================================
# Parse ~T records (Textos largos)
# Format: ~T|CODE#|LONG_TEXT|
# ============================================================
texts = {}

for r in records:
    if not r.startswith("~T|"):
        continue
    
    parts = r[3:].split("|")
    if len(parts) < 2:
        continue
    
    code = parts[0].replace("#", "").strip()
    text = parts[1].strip() if len(parts) > 1 else ""
    if code and text:
        texts[code] = text

print(f"Textos largos (~T): {len(texts)}")

# ============================================================
# Parse ~M records (Mediciones)
# Format: ~M|PARENT#CHILD|Position|TOTAL_LINES|LINE_DATA|
# ============================================================
measurements = defaultdict(list)

for r in records:
    if not r.startswith("~M|"):
        continue
    
    parts = r[3:].split("|")
    if len(parts) < 2:
        continue
    
    codes = parts[0].strip()
    if "#" in codes:
        parent, child = codes.split("#", 1)
    else:
        parent = codes
        child = ""
    
    meas_data = "|".join(parts[1:])
    measurements[parent.strip()].append({
        "child": child.strip(),
        "data": meas_data[:200],
    })

print(f"Mediciones (~M): {len(measurements)}")

# ============================================================
# Build tree and generate report
# ============================================================
print("\nGenerando reporte...")

# Identify chapters (concepts with children that are also concepts)
# Root is usually "" or the project code
root_codes = []
for code, children in hierarchy.items():
    if code in concepts:
        c = concepts[code]
        if not c["unit"]:  # Chapters typically have no unit
            root_codes.append(code)

# Collect all items with prices
items_with_price = []
for code, concept in concepts.items():
    if concept["price"] > 0 and concept["unit"]:
        concept["long_text"] = texts.get(code, "")
        items_with_price.append(concept)

items_with_price.sort(key=lambda x: x["code"])
print(f"Partidas con precio: {len(items_with_price)}")

# Chapters (no unit = grouping concept)
chapters = []
for code, concept in concepts.items():
    if not concept["unit"] and concept["summary"]:
        chapters.append(concept)

chapters.sort(key=lambda x: x["code"])
print(f"Capitulos/grupos: {len(chapters)}")

# ============================================================
# Generate report
# ============================================================
lines = []
lines.append("=" * 95)
lines.append("ESTRUCTURA COMPLETA DE PRESUPUESTO PRESTO")
lines.append(f"Archivo: {BC3_PATH.name}")
lines.append(f"Fecha export: {datetime.now().strftime('%Y-%m-%d')}")
lines.append(f"Conceptos totales: {len(concepts)}")
lines.append(f"Partidas con precio: {len(items_with_price)}")
lines.append(f"Capitulos: {len(chapters)}")
lines.append(f"Textos largos: {len(texts)}")
lines.append(f"Mediciones: {len(measurements)}")
lines.append("=" * 95)

# Chapters
lines.append(f"\n{'_' * 95}")
lines.append("CAPITULOS / AGRUPACIONES")
lines.append(f"{'_' * 95}")
for ch in chapters[:50]:
    code = ch["code"]
    children_count = len(hierarchy.get(code, []))
    lines.append(f"  {code:<20} {ch['summary'][:60]:<60} ({children_count} hijos)")

# All partidas with prices
lines.append(f"\n{'_' * 95}")
lines.append("TODAS LAS PARTIDAS CON PRECIOS")
lines.append(f"{'_' * 95}")
lines.append(f"\n  {'Codigo':<16} {'Ud':<6} {'Precio':>14} {'Descripcion'}")
lines.append(f"  {'-'*16} {'-'*6} {'-'*14} {'-'*55}")

for item in items_with_price:
    desc = item["summary"][:55]
    lines.append(
        f"  {item['code']:<16} {item['unit']:<6} "
        f"{item['price']:>14,.2f} {desc}"
    )
    # Add long text if available
    lt = item.get("long_text", "")
    if lt and lt != item["summary"]:
        lines.append(f"{'':>40} >> {lt[:70]}")

lines.append(f"\n{'=' * 95}")
lines.append(f"Total partidas: {len(items_with_price)}")
lines.append(f"{'=' * 95}")

report = "\n".join(lines)
report_path = OUT_DIR / "BC3_ESTRUCTURA_COMPLETA.txt"
report_path.write_text(report, encoding="utf-8")

# Save JSON
json_data = {
    "file": BC3_PATH.name,
    "total_concepts": len(concepts),
    "chapters": chapters[:100],
    "partidas": items_with_price,
    "hierarchy": {k: v for k, v in list(hierarchy.items())[:200]},
    "texts": dict(list(texts.items())[:200]),
}

json_path = OUT_DIR / "bc3_full_data.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)

print(f"\nReporte: {report_path}")
print(f"JSON:    {json_path}")
print(f"\nPrimeras 15 partidas:")
for item in items_with_price[:15]:
    print(f"  {item['code']:<16} {item['unit']:<6} "
          f"${item['price']:>12,.2f}  {item['summary'][:45]}")
