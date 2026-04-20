import json, os

base = r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\output\20260418_162929_residencial_gebsa_iv"

for disc in ["electrico", "sanitario", "estructura", "arquitectura"]:
    print(f"\n{'='*60}\n  {disc.upper()}\n{'='*60}")

    cf = os.path.join(base, disc, "cad_facts.json")
    if os.path.exists(cf):
        d = json.load(open(cf, "r", encoding="utf-8"))
        if isinstance(d, dict):
            print(f"  cad_facts keys: {list(d.keys())}")
            ents = d.get("entities", d.get("objects", []))
            if isinstance(ents, list):
                print(f"  entities count: {len(ents)}")
                for e in ents[:3]:
                    print(f"    sample: {str(e)[:120]}")
            layers = d.get("layers", d.get("layer_map", {}))
            if isinstance(layers, (dict, list)):
                lcount = len(layers)
                print(f"  layers: {lcount}")
                if isinstance(layers, dict):
                    for k in list(layers.keys())[:10]:
                        print(f"    {k}: {layers[k]}")
                elif isinstance(layers, list):
                    for l in layers[:10]:
                        print(f"    {l}")
        elif isinstance(d, list):
            print(f"  cad_facts is list with {len(d)} items")
    else:
        print("  NO cad_facts.json")

    vi = os.path.join(base, disc, "vision_inventory.json")
    if os.path.exists(vi):
        d = json.load(open(vi, "r", encoding="utf-8"))
        if isinstance(d, list):
            print(f"  vision_inventory: {len(d)} levels")
            for lvl in d[:5]:
                if isinstance(lvl, dict):
                    items = lvl.get("items", lvl.get("elements", []))
                    err = lvl.get("error", lvl.get("vision_error", None))
                    name = lvl.get("level_name", lvl.get("name", "?"))
                    ic = len(items) if isinstance(items, list) else "N/A"
                    print(f"    level={name} items={ic} error={err}")
                    if isinstance(items, list):
                        for it in items[:2]:
                            print(f"      {str(it)[:120]}")
        elif isinstance(d, dict):
            print(f"  vision_inventory keys: {list(d.keys())}")
    else:
        print("  NO vision_inventory.json")

    qr = os.path.join(base, disc, "quality_report.json")
    if os.path.exists(qr):
        d = json.load(open(qr, "r", encoding="utf-8"))
        print(f"  quality_report: status={d.get('status','?')} issues={len(d.get('issues',[]))}")

    bo = os.path.join(base, disc, "budget_output.json")
    if os.path.exists(bo):
        d = json.load(open(bo, "r", encoding="utf-8"))
        lines = d.get("lines", [])
        chapters = d.get("chapters", [])
        print(f"  budget: {len(lines)} lines, {len(chapters)} chapters")
