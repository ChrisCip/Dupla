import json, os, glob
from pathlib import Path

# find latest json file
files = glob.glob(r"c:\Users\chris\Documents\Dupla\analysis_output\ANALISIS_INTEGRAL_*.json")
latest = max(files, key=os.path.getctime)

j = json.loads(Path(latest).read_text(encoding="utf-8"))

print(f"Latest file: {os.path.basename(latest)}")
print(f"Project: {j.get('project')}")
print(f"Total items: {j.get('total_items')}")
print(f"Grand total: RD$ {j.get('grand_total', 0):,.2f}")
print(f"Costo/m2: RD$ {j.get('costo_m2', 0):,.2f}")

print("\nChapters:")
for ch in j.get("budget_chapters", []):
    n = len(ch.get("items",[]))
    st = ch.get("subtotal",0)
    print(f"  {ch.get('category','?'):<35} {n:>3} items  RD$ {st:>15,.2f}")
