import json, os

base = r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\output\20260418_162929_residencial_gebsa_iv"

ITEM_KEYS = ["walls", "openings", "doors", "windows", "wet_areas", "kitchens",
             "stairs", "fixtures", "structural_elements"]

for disc in ["electrico", "sanitario", "arquitectura", "estructura"]:
    print(f"\n{'='*40} {disc.upper()} {'='*40}")

    vi = os.path.join(base, disc, "vision_inventory.json")
    if not os.path.exists(vi):
        print("  NO vision_inventory.json")
        continue

    levels = json.load(open(vi, "r", encoding="utf-8"))
    total_by_key = {}
    for lvl in levels:
        for k in ITEM_KEYS:
            items = lvl.get(k, [])
            if items:
                total_by_key.setdefault(k, 0)
                total_by_key[k] += len(items)

    print(f"  Levels: {len(levels)}")
    if total_by_key:
        for k, count in total_by_key.items():
            print(f"    {k}: {count} items total")
    else:
        print("  ALL item categories are EMPTY across all levels")

    # Show _raw_response length to see if Vision actually returned useful data
    for i, lvl in enumerate(levels[:3]):
        raw = lvl.get("_raw_response", "")
        simple = lvl.get("_simple_payload", {})
        meta = lvl.get("_metadata", {})
        notes = lvl.get("notes", [])
        sys_notes = lvl.get("system_notes", [])
        struct_notes = lvl.get("structural_notes", [])
        view = lvl.get("source_view", "?")
        print(f"  level[{i}]: view={view} raw_len={len(raw) if raw else 0} "
              f"simple_keys={list(simple.keys()) if isinstance(simple, dict) else '?'} "
              f"notes={len(notes)} sys_notes={len(sys_notes)}")
        if raw and len(raw) > 50:
            print(f"    raw_response preview: {raw[:200]}")

    # Check the takeoffs
    bo = os.path.join(base, disc, "budget_output.json")
    if os.path.exists(bo):
        d = json.load(open(bo, "r", encoding="utf-8"))
        takeoffs = d.get("takeoffs", [])
        base_takeoffs = d.get("base_takeoffs", [])
        print(f"  takeoffs: {len(takeoffs)}, base_takeoffs: {len(base_takeoffs)}")
        for t in takeoffs[:3]:
            if isinstance(t, dict):
                itype = t.get("item_type", "?")
                ikey = t.get("item_key", "?")
                qty = t.get("quantity", 0)
                unit = t.get("unit", "?")
                print(f"    {itype} | {ikey} | qty={qty} {unit}")
