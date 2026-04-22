import json, os
from collections import Counter

base = r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\output\20260418_162929_residencial_gebsa_iv"

for disc in ["electrico", "sanitario"]:
    print(f"\n{'='*40} {disc.upper()} {'='*40}")
    bo = os.path.join(base, disc, "budget_output.json")
    d = json.load(open(bo, "r", encoding="utf-8"))

    base_t = d.get("base_takeoffs", [])
    expanded_t = d.get("takeoffs", [])

    print(f"  base_takeoffs: {len(base_t)}")
    bt_types = Counter()
    for t in base_t:
        bt_types[t.get("item_type", "?")] += 1
    for k, v in sorted(bt_types.items()):
        print(f"    {k}: {v}")

    print(f"\n  expanded_takeoffs (takeoffs): {len(expanded_t)}")
    et_types = Counter()
    for t in expanded_t:
        et_types[t.get("item_type", "?")] += 1
    for k, v in sorted(et_types.items()):
        print(f"    {k}: {v}")

    # Budget diagnostics
    diag = d.get("budget_diagnostics", {})
    print(f"\n  budget_diagnostics:")
    print(f"    total: {diag.get('takeoffs_total')}")
    print(f"    budgetable: {diag.get('takeoffs_budgetable')}")
    print(f"    excluded: {diag.get('takeoffs_excluded')}")
    print(f"    excluded_by_reason: {diag.get('excluded_by_reason')}")
    print(f"    excluded_top_types: {diag.get('excluded_top_item_types')}")
