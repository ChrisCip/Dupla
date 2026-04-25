"""Analyze APS CAD facts to understand what data we have."""
import json
from pathlib import Path

paths = {
    "arquitectura": Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260421_232518_residencial_gebsa_iv\arquitectura\cad_facts.json"),
    "estructura": Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260420_224329_residencial_gebsa_iv\estructura\cad_facts.json"),
}

for disc, p in paths.items():
    if not p.exists():
        print(f"[SKIP] {disc}: not found")
        continue
    data = json.loads(p.read_text(encoding="utf-8"))
    print("=" * 70)
    print(f"APS CAD FACTS: {disc}")
    print("=" * 70)
    print(f"  Total objects: {data.get('total_objects', 0)}")
    hints = data.get("inventory_hints", {})
    cad = data.get("cad_facts", {})
    print(f"  Layers: {len(hints.get('layer_names', []))}")
    print(f"  Level markers: {len(hints.get('level_markers', []))}")
    print(f"  Block frequency entries: {len(hints.get('block_frequency', []))}")
    print(f"  Texts: {len(cad.get('texts', []))}")
    print(f"  Dimensions: {len(cad.get('dimensions', []))}")
    print(f"  Hatches: {len(cad.get('hatches', []))}")
    print(f"  Blocks: {len(cad.get('blocks', []))}")
    print(f"  Geometry hints: {len(cad.get('geometry_hints', []))}")
    print()

    print("  -- Layers --")
    for ln in sorted(hints.get("layer_names", []))[:25]:
        layer_info = cad.get("layers", {}).get(ln, {})
        count = layer_info.get("object_count", 0)
        types = layer_info.get("entity_types", {})
        top_types = sorted(types.items(), key=lambda x: x[1], reverse=True)[:3]
        type_str = ", ".join(f"{t}:{c}" for t, c in top_types)
        print(f"    {ln}: {count} objects [{type_str}]")

    print()
    print("  -- Block frequency --")
    for bf in hints.get("block_frequency", [])[:15]:
        print(f"    {bf['block_name']}: x{bf['count']}")

    print()
    print("  -- Level markers --")
    for lm in hints.get("level_markers", [])[:10]:
        print(f"    {lm.get('content', '')[:80]}")

    print()
    print("  -- Sample texts (structural/relevant) --")
    structural_keywords = ["c-", "c1", "v-", "v1", "zapata", "losa", "hormig", "muro", 
                           "puerta", "ventana", "bloque", "b-6", "b-8", "columna", "viga",
                           "piso", "nivel", "npt", "panete"]
    relevant_texts = []
    for t in cad.get("texts", []):
        content = (t.get("content") or "").strip().lower()
        if any(kw in content for kw in structural_keywords):
            relevant_texts.append(t)
    for t in relevant_texts[:20]:
        print(f"    [{t.get('layer', '?')}] {t.get('content', '')[:80]}")
    print(f"  Total relevant texts: {len(relevant_texts)} / {len(cad.get('texts', []))}")
    print()
