import json, os

base = r"C:\Users\chris\Downloads\DUPLA PDF GEBSA\output\20260418_162929_residencial_gebsa_iv"

for disc in ["electrico", "sanitario", "arquitectura", "estructura"]:
    print(f"\n{'='*40} {disc.upper()} {'='*40}")

    # Deep look at vision_inventory structure
    vi = os.path.join(base, disc, "vision_inventory.json")
    if os.path.exists(vi):
        d = json.load(open(vi, "r", encoding="utf-8"))
        if isinstance(d, list) and len(d) > 0:
            sample = d[0]
            print(f"  vision_inventory[0] keys: {list(sample.keys()) if isinstance(sample, dict) else type(sample)}")
            print(f"  vision_inventory[0]: {json.dumps(sample, ensure_ascii=False, default=str)[:500]}")
    
    # Deep look at budget_output structure  
    bo = os.path.join(base, disc, "budget_output.json")
    if os.path.exists(bo):
        d = json.load(open(bo, "r", encoding="utf-8"))
        print(f"  budget keys: {list(d.keys())}")
        lines = d.get("lines", [])
        if lines:
            print(f"  first line keys: {list(lines[0].keys())}")
            print(f"  first line: {json.dumps(lines[0], ensure_ascii=False, default=str)[:400]}")
        
        # Check where the data comes from
        sem = d.get("semantic_building")
        if sem:
            print(f"  semantic_building present, type={type(sem).__name__}")
        qr = d.get("quality_report") 
        if qr:
            print(f"  quality_report in budget, status={qr.get('status')}")
        
        # inventory?
        inv = d.get("inventory", d.get("hybrid_inventory"))
        if inv:
            print(f"  inventory present, type={type(inv).__name__}, len={len(inv) if isinstance(inv, list) else 'N/A'}")

    # Check cad_facts deeper 
    cf = os.path.join(base, disc, "cad_facts.json")
    if os.path.exists(cf):
        d = json.load(open(cf, "r", encoding="utf-8"))
        total = d.get("total_objects", 0)
        cad = d.get("cad_facts", {})
        print(f"  total_objects: {total}")
        if isinstance(cad, dict):
            print(f"  cad_facts inner keys: {list(cad.keys())}")
            for k, v in list(cad.items())[:5]:
                if isinstance(v, list):
                    print(f"    {k}: list({len(v)})")
                    if v:
                        print(f"      sample: {str(v[0])[:150]}")
                elif isinstance(v, dict):
                    print(f"    {k}: dict({len(v)} keys)")
                else:
                    print(f"    {k}: {str(v)[:100]}")
