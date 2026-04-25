"""Debug: show what generated vs real descriptions look like side-by-side."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from compare_budget import (
    _load_budget_rows, _is_partida, _safe_str, _normalize,
    _candidate_mapping_score, _row_family_tags, _filter_partidas_by_discipline,
)

real_path = Path(r"data\PRES.xlsx").resolve()
gen_path = Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260424_213342_residencial_gebsa_iv\arquitectura\presupuesto_arquitectura.xlsx")

real_rows = _load_budget_rows(real_path)
gen_rows = _load_budget_rows(gen_path)

gen_partidas = [r for r in gen_rows if _is_partida(r)]
real_partidas = [r for r in real_rows if _is_partida(r)]
filtered_real = _filter_partidas_by_discipline(real_partidas, "arquitectura", real_rows)

print(f"Generated partidas: {len(gen_partidas)}")
print(f"Real partidas (all): {len(real_partidas)}")
print(f"Real partidas (arq): {len(filtered_real)}")
print()

# Show all generated partidas
print("=" * 80)
print("GENERATED PARTIDAS")
print("=" * 80)
for g in gen_partidas:
    fam = _row_family_tags(g)
    print(f"  [{g['code']:>10}] [{g['unit']:>4}] {g['summary'][:70]} | tags: {fam}")

# Show top 20 filtered real partidas
print()
print("=" * 80)
print("SAMPLE REAL PRES (arquitectura-filtered)")
print("=" * 80)
for r in filtered_real[:30]:
    fam = _row_family_tags(r)
    print(f"  [{r['code']:>10}] [{r['unit']:>4}] {r['summary'][:70]} | tags: {fam}")

# Now do pairwise scoring - top match for each generated partida
print()
print("=" * 80)
print("BEST MATCHES (generated -> real, using mapping score)")
print("=" * 80)
for g in gen_partidas[:20]:
    best_score = 0.0
    best_real = None
    for r in filtered_real:
        score = _candidate_mapping_score(g, r)
        if score > best_score:
            best_score = score
            best_real = r
    if best_real:
        print(f"\n  SCORE: {best_score*100:.1f}%")
        print(f"    GEN:  [{g['code']:>10}] [{g['unit']:>4}] {g['summary'][:80]}")
        print(f"    REAL: [{best_real['code']:>10}] [{best_real['unit']:>4}] {best_real['summary'][:80]}")
    else:
        print(f"\n  NO MATCH for: {g['summary'][:80]}")
