"""Quick summary of BC3 parse results."""
import json

data = json.loads(
    open(r"c:\Users\chris\Documents\Dupla\presto_files\bc3_full_data.json",
         "r", encoding="utf-8").read()
)

print(f"Total concepts: {data['total_concepts']}")
print(f"Chapters: {len(data['chapters'])}")
print(f"Partidas con precio: {len(data['partidas'])}")
print(f"Hierarchy entries: {len(data['hierarchy'])}")
print(f"Texts: {len(data['texts'])}")

print("\n=== CAPITULOS ===")
for ch in data["chapters"][:30]:
    print(f"  {ch['code']:<25} {ch['summary'][:55]}")

print(f"\n=== PRIMERAS 30 PARTIDAS CON PRECIO ===")
print(f"  {'Codigo':<16} {'Ud':<6} {'Precio':>12}  {'Descripcion'}")
print(f"  {'-'*16} {'-'*6} {'-'*12}  {'-'*50}")
for p in data["partidas"][:30]:
    print(f"  {p['code']:<16} {p['unit']:<6} {p['price']:>12,.2f}  {p['summary'][:50]}")

print(f"\n=== RESUMEN PRECIOS ===")
prices = [p["price"] for p in data["partidas"] if p["price"] > 0]
print(f"  Total partidas: {len(prices)}")
if prices:
    print(f"  Min precio: ${min(prices):,.2f}")
    print(f"  Max precio: ${max(prices):,.2f}")
    print(f"  Promedio:   ${sum(prices)/len(prices):,.2f}")

# Units distribution
from collections import Counter
units = Counter(p["unit"] for p in data["partidas"])
print(f"\n=== UNIDADES ===")
for u, c in units.most_common(15):
    print(f"  {u:<10} {c:>5} partidas")
