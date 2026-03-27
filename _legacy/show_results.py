import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
files = sorted((PROJECT_ROOT / "analysis_output").glob("ANALISIS_INTEGRAL_*.json"))
if not files:
    raise FileNotFoundError("No se encontraron archivos ANALISIS_INTEGRAL_*.json en analysis_output")
j = json.loads(files[-1].read_text(encoding="utf-8"))

print(f"Project: {j['project']}")
print(f"DWG Entities: {j['dwg_entities']:,}")
print(f"Native clashes: {len(j['native_clashes'])}")
print(f"Visual clashes: {len(j['visual_clashes'])}")
print(f"Total items: {j['total_items']}")
print(f"Grand total: RD$ {j['grand_total']:,.2f}")
print(f"Costo/m2: RD$ {j['costo_m2']:,.2f}")

print(f"\nChapters:")
for ch in j["budget_chapters"]:
    n = len(ch.get("items",[]))
    st = ch.get("subtotal",0)
    print(f"  {ch.get('category','?'):<45} {n:>3} items  RD$ {st:>18,.2f}")

# Count clash severity
from collections import Counter
sevs = Counter(c["severity"] for c in j["native_clashes"])
print(f"\nClash severity: {dict(sevs)}")

# Show a few visual clashes
for vc in j["visual_clashes"][:5]:
    print(f"  Visual: [{vc.get('severity','')}] {vc.get('description','')[:60]}")
