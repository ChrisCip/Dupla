"""Re-parse the raw GPT-4o response with number-comma fix."""
import json, re
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(r"c:\Users\chris\Documents\Dupla\vision_output")

raw = (OUTPUT_DIR / "gpt4o_budget_raw.txt").read_text(encoding="utf-8")
print(f"Raw length: {len(raw)} chars")

# Strip commas from numbers 
def clean_json_numbers(text):
    return re.sub(r'(?<=\d),(?=\d{3})', '', text)

cleaned = clean_json_numbers(raw)

# Extract JSON from code block
match = re.search(r"```(?:json)?\s*\n(.*?)\n```", cleaned, re.DOTALL)
if match:
    json_str = match.group(1)
else:
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    json_str = cleaned[start:end+1]

# Fix trailing commas
json_str = re.sub(r',\s*}', '}', json_str)
json_str = re.sub(r',\s*]', ']', json_str)

budget = json.loads(json_str)

# Save fixed JSON
json_path = OUTPUT_DIR / "PRESUPUESTO_FINAL.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(budget, f, ensure_ascii=False, indent=2)

# Generate report
lines = []
lines.append("=" * 100)
lines.append(f"  PRESUPUESTO DE OBRA - {budget.get('project', '')}")
lines.append(f"  Ubicacion: {budget.get('location', '')}")
lines.append(f"  Moneda: {budget.get('currency', 'RD$')}")
lines.append(f"  Catalogo: {budget.get('bc3_source', 'CTXI0000TRM.bc3')}")
lines.append(f"  Fecha: {datetime.now().strftime('%Y-%m-%d')}")
lines.append(f"  Metodo: Precios Presto BC3 + Mediciones CAD DWG + GPT-4o")
lines.append("=" * 100)

grand_total = 0
total_items = 0

for chapter in budget.get("chapters", []):
    ch_code = chapter.get("code", "")
    ch_name = chapter.get("name", "")
    items = chapter.get("items", [])
    ch_total = sum(float(i.get("total", 0)) for i in items)
    grand_total += ch_total
    
    lines.append(f"\n{'_' * 100}")
    lines.append(f"  {ch_code}. {ch_name.upper()}")
    lines.append(f"  Subtotal: RD$ {ch_total:>18,.2f}")
    lines.append(f"{'_' * 100}")
    lines.append("")
    lines.append(
        f"  {'Cod Presto':<14} {'Descripcion':<35} {'Ud':<5}"
        f"{'Cant':>10} {'P.Unit RD$':>14} {'Total RD$':>16} {'Fuente'}"
    )
    lines.append(f"  {'-'*14} {'-'*35} {'-'*5}{'-'*10} {'-'*14} {'-'*16} {'-'*10}")
    
    for item in items:
        total_items += 1
        desc = str(item.get("description", ""))[:33]
        total = float(item.get("total", 0))
        qty = float(item.get("quantity", 0))
        price = float(item.get("unit_price", 0))
        lines.append(
            f"  {str(item.get('presto_code','')):<14} {desc:<35} "
            f"{str(item.get('unit','')):<5}"
            f"{qty:>10.2f} "
            f"{price:>14,.2f} "
            f"{total:>16,.2f} "
            f"{str(item.get('cad_source',''))[:10]}"
        )

lines.append(f"\n{'=' * 100}")
lines.append(f"  TOTAL GENERAL:  RD$ {grand_total:>18,.2f}")

area = 3426
costo_m2 = grand_total / area if area > 0 else 0
lines.append(f"  Area construida:  {area:,.0f} m2")
lines.append(f"  Costo por m2:     RD$ {costo_m2:,.2f}")
lines.append(f"  Partidas:         {total_items}")
lines.append(f"{'=' * 100}")

summary = budget.get("summary", {})
if summary.get("observations"):
    lines.append(f"\n  Observaciones: {summary['observations']}")

report = "\n".join(lines)
report_path = OUTPUT_DIR / "PRESUPUESTO_FINAL_GIUALCA.txt"
report_path.write_text(report, encoding="utf-8")

print(f"\nPresupuesto: {report_path}")
print(f"JSON: {json_path}")
print(f"Total: RD$ {grand_total:,.2f}")
print(f"Costo/m2: RD$ {costo_m2:,.2f}")
print(f"Partidas: {total_items}")

# Show all chapters
for ch in budget.get("chapters", []):
    ch_total = sum(float(i.get("total", 0)) for i in ch.get("items", []))
    print(f"  {ch['code']}. {ch['name']}: RD$ {ch_total:,.2f}")
