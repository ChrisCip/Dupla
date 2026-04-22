import json, os

base = r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\output\20260418_162929_residencial_gebsa_iv"

for disc in ["electrico", "sanitario"]:
    print(f"\n{'='*40} {disc.upper()} {'='*40}")

    vi = os.path.join(base, disc, "vision_inventory.json")
    levels = json.load(open(vi, "r", encoding="utf-8"))

    for i, lvl in enumerate(levels):
        sp = lvl.get("_simple_payload", {})
        elec = sp.get("electrical", [])
        plumb = sp.get("plumbing", [])
        fixtures = lvl.get("fixtures", [])
        ext_works = sp.get("exterior_works", [])
        annot = sp.get("annotations_and_notes", [])
        notes = lvl.get("notes", [])

        if elec or plumb or fixtures:
            print(f"\n  level[{i}] ({lvl.get('level_name','?')}):")
            if elec:
                print(f"    electrical: {len(elec)} items")
                for e in elec[:3]:
                    print(f"      {json.dumps(e, ensure_ascii=False)[:150]}")
            if plumb:
                print(f"    plumbing: {len(plumb)} items")
                for p in plumb[:3]:
                    print(f"      {json.dumps(p, ensure_ascii=False)[:150]}")
            if fixtures:
                print(f"    fixtures: {len(fixtures)} items")
                for f in fixtures[:3]:
                    print(f"      {json.dumps(f, ensure_ascii=False)[:150]}")
            if notes:
                print(f"    notes: {[n[:60] for n in notes[:3]]}")

    # Also check budget_output takeoff types
    bo = os.path.join(base, disc, "budget_output.json")
    d = json.load(open(bo, "r", encoding="utf-8"))
    takeoffs = d.get("takeoffs", [])
    item_types = {}
    for t in takeoffs:
        it = t.get("item_type", "?")
        item_types[it] = item_types.get(it, 0) + 1
    print(f"\n  Takeoff item_type distribution: {item_types}")

    lines = d.get("lines", [])
    line_types = {}
    for l in lines:
        meta = l.get("metadata", {})
        it = meta.get("item_type", "?")
        line_types[it] = line_types.get(it, 0) + 1
    print(f"  Budget line item_type distribution: {line_types}")
