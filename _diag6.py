import json, os
from collections import Counter

base = r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\output\20260418_162929_residencial_gebsa_iv"

bo = os.path.join(base, "electrico", "budget_output.json")
d = json.load(open(bo, "r", encoding="utf-8"))
inv = d.get("hybrid_inventory", [])
print(f"hybrid_inventory levels: {len(inv)}")
for i, lvl in enumerate(inv):
    fixtures = lvl.get("fixtures", [])
    doors = lvl.get("doors", [])
    walls = lvl.get("walls", [])
    windows = lvl.get("windows", [])
    struct = lvl.get("structural_elements", [])
    print(f"  level[{i}] ({lvl.get('level_name','?')}): "
          f"fixtures={len(fixtures)} doors={len(doors)} windows={len(windows)} "
          f"walls={len(walls)} struct={len(struct)}")
    for f in fixtures[:2]:
        print(f"    fixture: id={f.get('id')} type={f.get('fixture_type')} count={f.get('count')}")

# Check base_takeoffs for fixture_count
base_t = d.get("base_takeoffs", [])
fixture_takeoffs = [t for t in base_t if t.get("item_type") == "fixture_count"]
print(f"\nBase fixture_count takeoffs: {len(fixture_takeoffs)}")
for t in fixture_takeoffs[:5]:
    print(f"  key={t.get('item_key')} qty={t.get('quantity')}")

# Check dedup
keys = [t.get("item_key") for t in base_t]
unique = len(set(keys))
print(f"\nBase takeoff keys: {len(keys)} total, {unique} unique")
dupes = Counter(keys)
for k, c in dupes.most_common(5):
    if c > 1:
        print(f"  DUP: {k} x{c}")
