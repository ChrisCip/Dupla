"""Quick comparison of baseline vs enhanced runs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from compare_budget import analyze_budget_pair

baseline_arq = Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260424_004858_residencial_gebsa_iv\arquitectura\presupuesto_arquitectura.xlsx")
enhanced_arq = Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260424_005555_residencial_gebsa_iv\arquitectura\presupuesto_arquitectura.xlsx")
real = Path(r"data\PRES.xlsx").resolve()

# Also check if we have estructura runs
estructura_enhanced = Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260424_005301_residencial_gebsa_iv\estructura\presupuesto_estructura.xlsx")
estructura_baseline_old = Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260420_224329_residencial_gebsa_iv\estructura\presupuesto_estructura.xlsx")

def print_metrics(label, stats):
    print(f"  generated_partidas: {len(stats['generated_partidas'])}")
    print(f"  real_partidas: {len(stats['real_partidas'])}")
    print(f"  coverage: {stats['coverage']:.4f}%")
    print(f"  coverage_exact: {stats['coverage_exact']:.4f}%")
    print(f"  qty_accuracy: {stats['qty_accuracy']:.4f}%")
    print(f"  semantic_avg_best_similarity: {stats['semantic_avg_best_similarity']:.4f}%")
    print(f"  semantic_match_rate_60: {stats['semantic_match_rate_60']:.4f}%")
    print(f"  semantic_match_rate_70: {stats['semantic_match_rate_70']:.4f}%")
    print(f"  mapped_coverage_pres_code: {stats['mapped_coverage_pres_code']:.4f}%")
    print(f"  mapped_qty_accuracy: {stats['mapped_qty_accuracy']:.4f}%")
    print(f"  mapped_price_accuracy: {stats['mapped_price_accuracy']:.4f}%")
    print(f"  mapped_count: {stats['mapped_count']}")
    print()
    for pair in stats.get("mapped_top_pairs", [])[:5]:
        rc = pair["real_code"]
        gc = pair["generated_code"]
        sc = pair["score"]
        rs = pair["real_summary"][:55]
        gs = pair["generated_summary"][:55]
        print(f"  MAP: {rc} <- {gc} | {sc:.1f}% | R:{rs}")
        print(f"       G:{gs}")

print("=" * 70)
print("=== ARQUITECTURA BASELINE ===")
print("=" * 70)
b = analyze_budget_pair(baseline_arq, real)
print_metrics("baseline", b)

print()
print("=" * 70)
print("=== ARQUITECTURA ENHANCED ===")
print("=" * 70)
e = analyze_budget_pair(enhanced_arq, real)
print_metrics("enhanced", e)

print()
print("=" * 70)
print("=== DELTAS (enhanced - baseline) ===")
print("=" * 70)
print(f"  coverage: {e['coverage'] - b['coverage']:+.4f}%")
print(f"  semantic_avg: {e['semantic_avg_best_similarity'] - b['semantic_avg_best_similarity']:+.4f}%")
print(f"  semantic_rate_60: {e['semantic_match_rate_60'] - b['semantic_match_rate_60']:+.4f}%")
print(f"  mapped_coverage: {e['mapped_coverage_pres_code'] - b['mapped_coverage_pres_code']:+.4f}%")
print(f"  mapped_qty: {e['mapped_qty_accuracy'] - b['mapped_qty_accuracy']:+.4f}%")
print(f"  mapped_count: {e['mapped_count'] - b['mapped_count']}")

# Estructura if available
for est_path, est_label in [
    (estructura_enhanced, "ESTRUCTURA ENHANCED"),
    (estructura_baseline_old, "ESTRUCTURA BASELINE (old)")
]:
    if est_path.exists():
        print()
        print("=" * 70)
        print(f"=== {est_label} ===")
        print("=" * 70)
        s = analyze_budget_pair(est_path, real)
        print_metrics(est_label, s)
    else:
        print(f"\n[SKIP] {est_label} not found: {est_path}")
