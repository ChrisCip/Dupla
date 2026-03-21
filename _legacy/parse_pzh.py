"""
Parser de archivos PZH (Presto 8.8).

Extrae la estructura de presupuesto: codigos, descripciones, unidades,
precios, y jerarquia de capitulos/partidas.
"""
import struct
from pathlib import Path

path = r"c:\Users\chris\Documents\Dupla\presto_files\CTXI0000TRM.pzh"
out_path = r"c:\Users\chris\Documents\Dupla\presto_files\pzh_budget_structure.txt"
json_path = r"c:\Users\chris\Documents\Dupla\presto_files\pzh_budget.json"

with open(path, "rb") as f:
    data = f.read()

print(f"PZH: {len(data):,} bytes")

# Strategy: scan for item records.
# From the probe, items look like:
#   CODE (padded to ~13 chars)  SPACE  FLAGS  UNIT (2-3 chars)  DESCRIPTION
# Examples:
#   A0109009     .0....m³..Hormigón H180 Ligado en Obra
#   A0301043     .0....m3..Mezcla 1:3
#   B0305110     ...m2..M.O. de Coloc. Ceramica hasta 40x40 cm

items = []
i = 0
while i < len(data) - 100:
    # Look for patterns that match a Presto item code
    # Codes are alphanumeric, typically 8-12 chars, followed by spaces
    
    # Check if current position looks like a code start
    # Codes start with uppercase letter or digit
    b = data[i]
    if (65 <= b <= 90 or 48 <= b <= 57):  # A-Z or 0-9
        # Try to read a code (up to 13 chars)
        code_end = i
        for j in range(i, min(i + 14, len(data))):
            if data[j] == 0 or data[j] == 32:
                break
            code_end = j + 1
        
        code_len = code_end - i
        if 5 <= code_len <= 13:
            code = data[i:code_end].decode("latin-1", errors="replace")
            
            # After code there should be spaces, then flags, then unit
            # Search forward for a unit marker
            search_zone = data[code_end:code_end + 30]
            
            unit = ""
            unit_pos = -1
            for u in [b"m\xb3", b"m\xb2", b"p\xb2", b"m3", b"m2", b"ml", b"ud",
                       b"kg", b"gl", b"pa", b"mes", b"dia"]:
                p = search_zone.find(u)
                if p >= 0 and (unit_pos == -1 or p < unit_pos):
                    unit_pos = p
                    unit = u.decode("latin-1", errors="replace")
            
            if unit and unit_pos >= 0:
                # Found unit - now read description after unit
                desc_start = code_end + unit_pos + len(unit)
                # Skip separators
                while desc_start < len(data) and data[desc_start] in (0, 0x2E, 0x20):
                    desc_start += 1
                
                # Read description (until null or control char sequence)
                desc_chars = []
                for j in range(desc_start, min(desc_start + 100, len(data))):
                    c = data[j]
                    if c == 0:
                        # Multiple nulls = end of description
                        if j + 1 < len(data) and data[j + 1] == 0:
                            break
                        desc_chars.append(" ")
                    elif 32 <= c <= 255:
                        desc_chars.append(chr(c))
                    else:
                        break
                
                desc = "".join(desc_chars).strip()
                
                if len(desc) > 3 and any(c.isalpha() for c in desc):
                    # Try to read price (IEEE 754 double after description)
                    # Look for doubles in the area after description
                    price = 0.0
                    price_zone_start = desc_start + len(desc)
                    for offset in range(0, 60, 1):
                        try:
                            val = struct.unpack_from("<d", data, price_zone_start + offset)[0]
                            if 0.01 < val < 1_000_000 and val == val:  # not NaN
                                price = val
                                break
                        except:
                            pass
                    
                    items.append({
                        "code": code,
                        "unit": unit,
                        "description": desc,
                        "price": price,
                        "offset": i,
                    })
                    i = desc_start + len(desc)
                    continue
    i += 1

print(f"\nItems found: {len(items)}")

# Categorize: items starting with digits are often chapters
# Items with letter prefixes are partidas
chapters = []
partidas = []
for item in items:
    if item["code"][0].isdigit() or item["code"].startswith("%"):
        chapters.append(item)
    else:
        partidas.append(item)

# Generate report
lines = []
lines.append("=" * 90)
lines.append("ESTRUCTURA DE PRESUPUESTO - PRESTO 8.8 (.pzh)")
lines.append(f"Archivo: CTXI0000TRM.pzh")
lines.append(f"Total items extraidos: {len(items)}")
lines.append(f"Capitulos/conceptos: {len(chapters)}")
lines.append(f"Partidas: {len(partidas)}")
lines.append("=" * 90)

lines.append(f"\n{'Cod':<15}{'Ud':<6}{'Precio':>12}  {'Descripcion'}")
lines.append(f"{'-'*15}{'-'*6}{'-'*12}  {'-'*50}")

# Deduplicate by code
seen = set()
unique_items = []
for item in items:
    if item["code"] not in seen:
        seen.add(item["code"])
        unique_items.append(item)

for item in unique_items:
    price_str = f"{item['price']:>12.2f}" if item["price"] > 0 else f"{'':>12}"
    desc = item["description"][:55]
    lines.append(f"{item['code']:<15}{item['unit']:<6}{price_str}  {desc}")

lines.append(f"\n{'=' * 90}")
lines.append(f"Total partidas unicas: {len(unique_items)}")
lines.append(f"{'=' * 90}")

report = "\n".join(lines)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report)

# Save JSON
import json
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(unique_items, f, ensure_ascii=False, indent=2, default=str)

print(f"Report: {out_path}")
print(f"JSON: {json_path}")
print(f"Unique items: {len(unique_items)}")
print(f"\nFirst 10 items:")
for item in unique_items[:10]:
    print(f"  {item['code']:<15} {item['unit']:<6} ${item['price']:>10.2f}  {item['description'][:50]}")
