"""Analyze PRES breakdown by discipline to understand realistic coverage targets."""
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from knowledge.training_data import extract_training_pairs

pres = Path(r"data\PRES.xlsx").resolve()
nasas = Path(r"data\Prelimary Budget NASAS 9-2, 17-02-2026.xlsx").resolve()

for src in [pres, nasas]:
    if not src.exists():
        print(f"[SKIP] {src.name}: not found")
        continue
    pairs = extract_training_pairs(src)
    
    # Group by discipline (from context)
    disc_counts = Counter()
    disc_types = {}
    for p in pairs:
        _, _, disc = p.input_context.partition("|")
        disc = disc.strip() or "General"
        disc_counts[disc] += 1
        disc_types.setdefault(disc, Counter())[p.input_item_type] += 1
    
    print("=" * 70)
    print(f"SOURCE: {src.name} ({len(pairs)} total pairs)")
    print("=" * 70)
    
    for disc, count in disc_counts.most_common():
        types = disc_types[disc]
        top_types = ", ".join(f"{t}:{c}" for t, c in types.most_common(5))
        print(f"  {disc}: {count} partidas [{top_types}]")
    
    # Also show item_type distribution
    print()
    type_counts = Counter(p.input_item_type for p in pairs)
    print("  Item types:")
    for t, c in type_counts.most_common():
        print(f"    {t}: {c}")
    print()
