"""
Test unitario de run_cross_validation()
Cubre 4 escenarios:
  1. DWG real del proyecto (capas en español, sin A-DOOR/A-GLAZ → sin checks)
  2. Capas AEC estándar con ratio OK
  3. Capas AEC estándar con ratio en WARNING
  4. Edge case: result sin disciplinas
"""
import sys
import json
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents.vision_agent import run_cross_validation

# ── helpers ──────────────────────────────────────────────────────────────────
SEP = "=" * 60

def header(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

def show(label, val):
    print(f"  {label:<45} {val}")

# ─── datos base de GPT-4o (simulados con 12 puertas y 8 ventanas) ─────────
result_gpt = {
    "disciplines": {
        "ALB": {
            "items": [
                {"description": "Puerta interior", "unit": "ud", "quantity_per_floor": 12},
                {"description": "Ventana corredera", "unit": "ud", "quantity_per_floor": 8},
                {"description": "Muro de bloque", "unit": "m2", "quantity_per_floor": 200},
            ]
        }
    }
}

# ════════════════════════════════════════════════════════════════
# TEST 1: datos del DWG real (capas en español → sin A-DOOR/A-GLAZ)
# ════════════════════════════════════════════════════════════════
header("TEST 1 – Datos DWG real (capas en español, sin A-DOOR/A-GLAZ)")

json_path = Path("api_results/resultado_2-_PLANTAS_ARQUITECTONICAS.json")
with open(json_path, encoding="utf-8") as f:
    raw = json.load(f)

views = raw.get("views", [])
v2d = next((v for v in views if v.get("role") == "2d"), views[0])
layer_counts = Counter()
for o in v2d.get("objects", []):
    layer = o.get("properties", {}).get("General", {}).get("Layer", "UNKNOWN")
    layer_counts[layer] += 1

# mostrar capas relevantes encontradas
relevant = {k: v for k, v in layer_counts.items()
            if any(w in k.lower() for w in ("door", "glaz", "puerta", "ventana", "cristal"))}
print(f"  Capas relevantes en el DWG: {relevant}")

json_summary_real = {
    "layer_summary": {
        layer: {"object_count": count}
        for layer, count in layer_counts.items()
    }
}

out1 = run_cross_validation(dict(result_gpt), json_summary_real)
checks1 = out1["validation"]["json_cross_checks"]
print(f"  Checks generados: {len(checks1)}")
for c in checks1:
    show(c["check"], f"status={c['status']}  vision={c['vision']}  ({c['message']})")
# Con el mapeo español→AEC se esperan checks para PUERTA→A-DOOR y/o CRISTAL→A-GLAZ
pass1 = len(checks1) > 0
print(f"  → {'CORRECTO – capas españolas mapeadas a A-DOOR/A-GLAZ correctamente' if pass1 else 'ERROR: no se generaron checks con capas españolas'}")

# ════════════════════════════════════════════════════════════════
# TEST 2: capas AEC estándar, ratio dentro del rango → status 'ok'
#         12 puertas × 40 líneas = 480 (rango 20-100 → ok)
#         8 ventanas × 80 líneas = 640 (rango 15-150 → ok)
# ════════════════════════════════════════════════════════════════
header("TEST 2 – Capas AEC estándar, ratio OK")

json_summary_aec = {
    "layer_summary": {
        "A-DOOR": {"object_count": 480},
        "A-GLAZ": {"object_count": 640},
    }
}

out2 = run_cross_validation(dict(result_gpt), json_summary_aec)
checks2 = out2["validation"]["json_cross_checks"]
print(f"  Checks generados: {len(checks2)}")
for c in checks2:
    show(c["check"], f"status={c['status']}  vision={c['vision']}  ({c['message']})")
pass2 = len(checks2) == 2 and all(c["status"] == "ok" for c in checks2)
print(f"  → {'CORRECTO' if pass2 else 'FALLO'}")

# ════════════════════════════════════════════════════════════════
# TEST 3: ratio FUERA de rango → status 'warning'
#         12 puertas × 200 líneas = 2400 (>100 → warning)
#         8 ventanas × 5 líneas  =   40 (<15 → warning)
# ════════════════════════════════════════════════════════════════
header("TEST 3 – Capas AEC estándar, ratio WARNING")

json_summary_warn = {
    "layer_summary": {
        "A-DOOR": {"object_count": 2400},
        "A-GLAZ": {"object_count": 40},
    }
}

out3 = run_cross_validation(dict(result_gpt), json_summary_warn)
checks3 = out3["validation"]["json_cross_checks"]
print(f"  Checks generados: {len(checks3)}")
for c in checks3:
    show(c["check"], f"status={c['status']}  vision={c['vision']}  ({c['message']})")
pass3 = len(checks3) == 2 and all(c["status"] == "warning" for c in checks3)
print(f"  → {'CORRECTO' if pass3 else 'FALLO'}")

# ════════════════════════════════════════════════════════════════
# TEST 4: edge case – result sin disciplinas
# ════════════════════════════════════════════════════════════════
header("TEST 4 – Edge case: result sin disciplinas")

out4 = run_cross_validation({"disciplines": {}}, json_summary_aec)
checks4 = out4["validation"]["json_cross_checks"]
print(f"  Checks generados: {len(checks4)}")
pass4 = len(checks4) == 0
print(f"  → {'CORRECTO – sin items no hay conteo' if pass4 else 'ERROR inesperado'}")

# ════════════════════════════════════════════════════════════════
# RESUMEN
# ════════════════════════════════════════════════════════════════
header("RESUMEN")
tests = [
    ("Test 1 – DWG real: capas españolas generan checks (mapeo AEC)", pass1),
    ("Test 2 – Ratio OK (2 checks, status=ok)",                       pass2),
    ("Test 3 – Ratio WARNING (2 checks, status=warning)",             pass3),
    ("Test 4 – Edge case vacío (sin checks)",                         pass4),
]
all_pass = True
for name, passed in tests:
    icon = "PASS" if passed else "FAIL"
    print(f"  [{icon}]  {name}")
    if not passed:
        all_pass = False

print()
if all_pass:
    print("  TODOS LOS TESTS PASARON")
else:
    print("  HAY TESTS FALLIDOS")

# Nota sobre el DWG real
header("NOTA: Mapeo de capas español → AEC aplicado")
print("  El DWG usa nombres en español:")
for layer, count in sorted(relevant.items(), key=lambda x: -x[1]):
    print(f"    {layer:<20} {count} objetos")
print()
print("  run_cross_validation() ahora mapea automáticamente:")
print("    PUERTA + puertas  → A-DOOR")
print("    CRISTAL + PERT-VENT + ventana → A-GLAZ")
