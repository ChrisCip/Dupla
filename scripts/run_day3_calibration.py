"""Day 3 calibration: compare runs with discipline-filtered metrics."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from compare_budget import analyze_budget_pair

real = Path(r"data\PRES.xlsx").resolve()

runs = {
    "baseline_arq (004858, skip-aps, no NASAS)": {
        "path": Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260424_004858_residencial_gebsa_iv\arquitectura\presupuesto_arquitectura.xlsx"),
        "discipline": "arquitectura",
    },
    "enhanced_arq (005555, skip-aps, day2-prep+NASAS)": {
        "path": Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260424_005555_residencial_gebsa_iv\arquitectura\presupuesto_arquitectura.xlsx"),
        "discipline": "arquitectura",
    },
    "new_arq (213342, APS-fail, PRES+NASAS training)": {
        "path": Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260424_213342_residencial_gebsa_iv\arquitectura\presupuesto_arquitectura.xlsx"),
        "discipline": "arquitectura",
    },
    "baseline_est (224329, with APS)": {
        "path": Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260420_224329_residencial_gebsa_iv\estructura\presupuesto_estructura.xlsx"),
        "discipline": "estructura",
    },
    "enhanced_est (005301, skip-aps)": {
        "path": Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260424_005301_residencial_gebsa_iv\estructura\presupuesto_estructura.xlsx"),
        "discipline": "estructura",
    },
    "new_est (223129, skip-aps, PRES+NASAS)": {
        "path": Path(r"C:\Users\jimif\Downloads\DUPLA GEBSA\output\20260424_223129_residencial_gebsa_iv\estructura\presupuesto_estructura.xlsx"),
        "discipline": "estructura",
    },
}

print("=" * 90)
print("DAY 3 CALIBRATION: Discipline-Filtered Metrics")
print("=" * 90)

results = {}
for label, info in runs.items():
    p = info["path"]
    disc = info["discipline"]
    if not p.exists():
        print(f"\n[SKIP] {label}: {p}")
        continue
    
    print(f"\n{'=' * 70}")
    print(f"RUN: {label}")
    print(f"{'=' * 70}")
    
    stats = analyze_budget_pair(p, real, discipline_filter=disc)
    results[label] = stats
    
    gen_n = len(stats["generated_partidas"])
    real_n = len(stats["real_partidas"])
    filt_n = stats.get("filtered_real_count", real_n)
    
    print(f"  Generated partidas: {gen_n}")
    print(f"  Real partidas (all): {real_n}")
    print(f"  Real partidas ({disc}): {filt_n}")
    print(f"  Theoretical coverage ({disc}): {stats.get('filtered_coverage_theoretical', 0):.1f}%")
    print()
    print(f"  --- UNFILTERED (vs all {real_n} PRES) ---")
    print(f"    Semantic avg: {stats['semantic_avg_best_similarity']:.2f}%")
    print(f"    Semantic >=60%: {stats['semantic_match_rate_60']:.2f}%")
    print(f"    Mapped coverage: {stats['mapped_coverage_pres_code']:.2f}%")
    print(f"    Mapped count: {stats['mapped_count']}")
    print(f"    Mapped qty accuracy: {stats['mapped_qty_accuracy']:.2f}%")
    
    fs = stats.get("filtered_semantic", {})
    fm = stats.get("filtered_mapped", {})
    if fs:
        print(f"\n  --- FILTERED (vs {filt_n} {disc} PRES) ---")
        print(f"    Semantic avg: {fs.get('semantic_avg_best_similarity', 0):.2f}%")
        print(f"    Semantic >=60%: {fs.get('semantic_match_rate_60', 0):.2f}%")
        print(f"    Mapped coverage: {fm.get('mapped_coverage_pres_code', 0):.2f}%")
        print(f"    Mapped count: {fm.get('mapped_count', 0)}")
        print(f"    Mapped qty accuracy: {fm.get('mapped_qty_accuracy', 0):.2f}%")
    
    # Show top mapped pairs from filtered
    top = fm.get("mapped_top_pairs", stats.get("mapped_top_pairs", []))[:8]
    if top:
        print(f"\n  --- TOP MAPPED PAIRS ---")
        for pair in top:
            print(f"    {pair['score']:.0f}% | PRES {pair['real_code']}: {pair['real_summary'][:55]}")
            print(f"         GEN  {pair['generated_code']}: {pair['generated_summary'][:55]}")

print("\n\n" + "=" * 90)
print("COMPARISON TABLE")
print("=" * 90)
print(f"{'Run':<55} {'Gen':>4} {'Filt':>5} {'Sem%':>6} {'Map#':>5} {'MapCov':>7} {'QtyAcc':>7}")
print("-" * 90)
for label, stats in results.items():
    gen_n = len(stats["generated_partidas"])
    filt_n = stats.get("filtered_real_count", len(stats["real_partidas"]))
    fm = stats.get("filtered_mapped", {})
    fs = stats.get("filtered_semantic", {})
    sem = fs.get("semantic_avg_best_similarity", stats["semantic_avg_best_similarity"])
    mc = fm.get("mapped_count", stats["mapped_count"])
    mcov = fm.get("mapped_coverage_pres_code", stats["mapped_coverage_pres_code"])
    mqty = fm.get("mapped_qty_accuracy", stats["mapped_qty_accuracy"])
    print(f"  {label:<53} {gen_n:>4} {filt_n:>5} {sem:>5.1f}% {mc:>5} {mcov:>6.1f}% {mqty:>6.1f}%")
