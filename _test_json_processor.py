"""
Test del módulo processors/json_processor.py
Cubre:
  1. get_discipline(): mapeo de capas AIA, capas españolas y fallbacks
  2. process_autodesk_json(): con el archivo real del proyecto
     - Estructura de salida (keys obligatorias)
     - Conteo de objetos vs datos reales (16221 en 2D View)
     - Extracción de textos, dimensiones y block references
     - Resumen de disciplinas
  3. Edge case: archivo con lista plana de objetos
"""
import sys
import json
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from processors.json_processor import get_discipline, process_autodesk_json

SEP = "=" * 62

def header(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

def check(label, passed, detail=""):
    icon = "PASS" if passed else "FAIL"
    line = f"  [{icon}]  {label}"
    if detail:
        line += f"  →  {detail}"
    print(line)
    return passed

results = []

# ════════════════════════════════════════════════════════════════
# TEST 1 – get_discipline(): mapeo de capas
# ════════════════════════════════════════════════════════════════
header("TEST 1 – get_discipline()")

cases = [
    ("A-WALL",          "Muros y Divisiones"),
    ("A-WALL-INT",      "Muros y Divisiones"),   # prefijo parcial
    ("S-COLS",          "Hormigón Armado"),
    ("S-BEAM-X1",       "Hormigón Armado"),
    ("A-DOOR",          "Puertas"),
    ("A-GLAZ",          "Ventanas"),
    ("A-WIND",          "Ventanas"),
    ("E-LITE",          "Instalación Eléctrica"),
    ("MEDICION",        "Misceláneos"),           # keyword fallback
    ("PUERTA",          "Misceláneos"),           # nombre español → misceláneos
    ("",                "Misceláneos"),           # vacío
    (None,              "Misceláneos"),           # None
    ("XYZUNKNOWN",      "Misceláneos"),           # capa desconocida
]

t1_pass = True
for layer, expected in cases:
    got = get_discipline(layer)
    p = check(f"get_discipline({layer!r})", got == expected,
              f"esperado={expected!r}  obtenido={got!r}")
    t1_pass = t1_pass and p

results.append(("Test 1 – get_discipline()", t1_pass))

# ════════════════════════════════════════════════════════════════
# TEST 2 – process_autodesk_json() con el archivo REAL del proyecto
# ════════════════════════════════════════════════════════════════
header("TEST 2 – process_autodesk_json() con DWG real (2D View, 16221 obj)")

JSON_REAL = Path("api_results/resultado_2-_PLANTAS_ARQUITECTONICAS.json")

if not JSON_REAL.exists():
    print(f"  [SKIP] Archivo no encontrado: {JSON_REAL}")
    results.append(("Test 2 – archivo real", None))
else:
    out = process_autodesk_json(str(JSON_REAL))

    # ── 2a: estructura de salida obligatoria ──────────────────────────
    required_keys = ["project", "total_objects", "layer_summary",
                     "usable_data", "discipline_summary", "gaps_for_vision_ai"]
    p2a = all(k in out for k in required_keys)
    check("Estructura de salida (todas las claves presentes)", p2a,
          f"claves={list(out.keys())}")

    # ── 2b: conteo de objetos (2D + 3D = 16221 + 11056 = 27277) ─────
    total = out["total_objects"]
    p2b = total == 27277
    check("total_objects == 27277 (todas las vistas)", p2b, f"obtenido={total}")

    # ── 2c: capas clave del DWG presentes en layer_summary ───────────
    expected_layers = ["A-WALL", "DIM", "PUERTA", "CRISTAL", "puertas"]
    missing = [l for l in expected_layers if l not in out["layer_summary"]]
    p2c = len(missing) == 0
    check("Capas esperadas en layer_summary", p2c,
          f"faltantes={missing}" if missing else "todas presentes")

    # ── 2d: usable_data tiene al menos textos y dimensiones ──────────
    ud = out["usable_data"]
    p2d_text = len(ud.get("texts", [])) > 0
    p2d_dim  = len(ud.get("dimensions", [])) > 0
    p2d_block = len(ud.get("block_references", [])) > 0
    check("usable_data.texts no vacío",           p2d_text,  f"{len(ud.get('texts',[]))} textos")
    check("usable_data.dimensions no vacío",      p2d_dim,   f"{len(ud.get('dimensions',[]))} dimensiones")
    check("usable_data.block_references no vacío",p2d_block, f"{len(ud.get('block_references',[]))} bloques")

    # ── 2d.1: verificar que dimensiones estén en SI (m) ─────────────
    dims = ud.get("dimensions", [])
    dims_have_si = all(
        isinstance(d.get("measurement"), (int, float)) and d.get("measurement_unit") == "m"
        for d in dims[:100]  # muestra para no penalizar rendimiento
    ) if dims else False
    check("dimensions convertidas a SI (measurement numérico en m)", dims_have_si)

    # ── 2e: discipline_summary no vacío y contiene disciplinas AEC ───
    ds = out["discipline_summary"]
    p2e = len(ds) > 0
    check("discipline_summary no vacío", p2e, f"{len(ds)} disciplinas: {list(ds.keys())[:4]}...")

    # ── 2f: A-WALL mapeado a "Muros y Divisiones" ────────────────────
    awall = out["layer_summary"].get("A-WALL", {})
    p2f = awall.get("discipline") == "Muros y Divisiones"
    check("A-WALL → disciplina 'Muros y Divisiones'", p2f,
          f"discipline={awall.get('discipline')}")

    # ── 2g: gaps_for_vision_ai es lista con contenido ─────────────────
    gaps = out["gaps_for_vision_ai"]
    p2g = isinstance(gaps, list) and len(gaps) > 0
    check("gaps_for_vision_ai es lista con contenido", p2g, f"{len(gaps)} gaps")

    # muestra resumen de datos extraídos
    print(f"\n  --- Resumen de datos extraídos del DWG ---")
    print(f"  Capas detectadas:   {len(out['layer_summary'])}")
    print(f"  Textos:             {len(ud.get('texts', []))}")
    print(f"  Dimensiones:        {len(ud.get('dimensions', []))}")
    print(f"  Block references:   {len(ud.get('block_references', []))}")
    print(f"  Hatches con área:   {len(ud.get('hatches_with_area', []))}")
    if ud.get("dimensions"):
        sample = ud["dimensions"][:3]
        print(f"  Muestra dimensiones: {[d['measurement'] for d in sample]}")
    if ud.get("texts"):
        sample_texts = [t["text"] for t in ud["texts"] if t["text"] != "(sin contenido visible)"][:3]
        print(f"  Muestra textos:      {sample_texts}")

    t2_pass = all([p2a, p2b, p2c, p2d_text, p2d_dim, p2d_block, dims_have_si, p2e, p2f, p2g])
    results.append(("Test 2 – archivo real", t2_pass))

# ════════════════════════════════════════════════════════════════
# TEST 3 – Edge case: JSON con lista plana de objetos
# ════════════════════════════════════════════════════════════════
header("TEST 3 – Edge case: lista plana de objetos")

flat_data = [
    {
        "name": "Hatch [A1B2C3]",
        "properties": {
            "General": {"Name ": "Hatch", "Layer": "A-FIN", "Handle": "abc1"},
            "Geometry": {"Area": "12.5"}
        }
    },
    {
        "name": "Text [D4E5F6]",
        "properties": {
            "General": {"Name ": "Text", "Layer": "textos", "Handle": "abc2"},
            "Text": {"Contents": "NPT +0.00", "Style": "Standard"}
        }
    },
    {
        "name": "Rotated Dimension [G7H8]",
        "properties": {
            "General": {"Name ": "Rotated Dimension", "Layer": "DIM", "Handle": "abc3"},
            "Text": {"Measurement": "3.24"}
        }
    },
    {
        "name": "Block Reference [I9J0]",
        "properties": {
            "General": {"Name ": "Block Reference", "Layer": "PUERTA", "Handle": "abc4"}
        }
    }
]

with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                 delete=False, encoding="utf-8") as tmp:
    json.dump(flat_data, tmp, ensure_ascii=False)
    tmp_path = tmp.name

try:
    out3 = process_autodesk_json(tmp_path)
    p3a = out3["total_objects"] == 4
    check("total_objects == 4", p3a, f"obtenido={out3['total_objects']}")

    hatches = out3["usable_data"]["hatches_with_area"]
    p3b = len(hatches) == 1 and float(hatches[0]["area"]) == 12.5
    check("Hatch extraído con area=12.5", p3b,
          f"hatches={hatches}")

    texts = out3["usable_data"]["texts"]
    p3c = any(t["text"] == "NPT +0.00" for t in texts)
    check("Text 'NPT +0.00' extraído", p3c)

    dims = out3["usable_data"]["dimensions"]
    p3d = len(dims) == 1 and str(dims[0]["measurement"]) == "3.24"
    check("Dimensión 3.24 extraída", p3d, f"dims={dims}")

    blocks = out3["usable_data"]["block_references"]
    p3e = any("Block Reference" in b["block_name"] or b["layer"] == "PUERTA" for b in blocks)
    check("Block Reference en capa PUERTA detectado", p3e)

    t3_pass = all([p3a, p3b, p3c, p3d, p3e])
    results.append(("Test 3 – edge case lista plana", t3_pass))
finally:
    os.unlink(tmp_path)

# ════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ════════════════════════════════════════════════════════════════
header("RESUMEN FINAL")
all_pass = True
for name, passed in results:
    if passed is None:
        print(f"  [SKIP]  {name}")
    else:
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}]  {name}")
        if not passed:
            all_pass = False

print()
if all([p for _, p in results if p is not None]):
    print("  TODOS LOS TESTS PASARON")
else:
    print("  HAY TESTS FALLIDOS")
