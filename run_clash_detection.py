"""
Clash Detection Hibrido: COM (bounding box) + Vision (GPT-4o).

1. COM: Lee entidades del DWG via COM, agrupa por disciplina,
   detecta intersecciones de bounding boxes entre disciplinas.
2. Vision: Envia planos clave a GPT-4o preguntando por conflictos
   visibles entre disciplinas.
3. Consolida ambos resultados en un reporte unificado.
"""

import win32com.client
import sys, os, json, base64, time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, r"c:\Users\chris\Documents\Dupla")

from dotenv import load_dotenv
load_dotenv(r"c:\Users\chris\Documents\Dupla\.env")

from openai import OpenAI
from cad_automation.config import classify_layer
from cad_automation.models import BoundingBox, ClashSeverity

OUTPUT_DIR = Path(r"c:\Users\chris\Documents\Dupla\vision_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("CLASH DETECTION HIBRIDO (COM + GPT-4o VISION)")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ============================================================
# PASO 1: CLASH POR COM (Bounding Box)
# ============================================================
print("\n[1/3] Clash detection por COM (bounding box)...")
print("  Conectando a Civil 3D...")

acad = win32com.client.GetActiveObject("AutoCAD.Application")
doc = acad.ActiveDocument
msp = doc.ModelSpace
total = msp.Count
print(f"  Documento: {doc.Name}")
print(f"  Entidades: {total}")

# Recopilar entidades con bbox, agrupadas por disciplina
entities_by_disc = defaultdict(list)
start = time.time()

print(f"  Leyendo bounding boxes ({total} entidades)...")

for i in range(total):
    if i % 5000 == 0 and i > 0:
        elapsed = time.time() - start
        pct = i / total * 100
        print(f"    [{pct:.0f}%] {i}/{total} | {elapsed:.0f}s")
    
    try:
        ent = msp.Item(i)
        layer = ent.Layer
        disc = classify_layer(layer)
        
        # Solo entidades con bbox valido
        try:
            min_pt, max_pt = ent.GetBoundingBox()
            bbox = BoundingBox(
                min_x=min_pt[0], min_y=min_pt[1],
                min_z=min_pt[2] if len(min_pt) > 2 else 0,
                max_x=max_pt[0], max_y=max_pt[1],
                max_z=max_pt[2] if len(max_pt) > 2 else 0,
            )
            
            # Solo si el bbox tiene tamano razonable (no puntos)
            if bbox.area_2d > 0.001:  # > 0.001 m2
                entities_by_disc[disc.name].append({
                    "handle": ent.Handle,
                    "type": ent.ObjectName.replace("AcDb", ""),
                    "layer": layer,
                    "discipline": disc.name,
                    "disc_value": disc.value,
                    "bbox": bbox,
                })
        except Exception:
            pass
    except Exception:
        pass

elapsed = time.time() - start
print(f"  Completado en {elapsed:.0f}s")

for d, ents in sorted(entities_by_disc.items()):
    print(f"    {d}: {len(ents)} entidades con bbox")

# Detectar clashes entre pares de disciplinas
print("\n  Detectando intersecciones entre disciplinas...")
clashes = []
disciplines = list(entities_by_disc.keys())

# Solo comparar pares relevantes
relevant_pairs = [
    ("A", "S"),   # Arquitectura vs Estructura
    ("A", "E"),   # Arquitectura vs Electrico
    ("A", "P"),   # Arquitectura vs Plomeria
    ("S", "E"),   # Estructura vs Electrico
    ("S", "P"),   # Estructura vs Plomeria
    ("E", "P"),   # Electrico vs Plomeria
    ("A", "I"),   # Arquitectura vs Interiorismo
    ("S", "I"),   # Estructura vs Interiorismo
]

for disc_a, disc_b in relevant_pairs:
    if disc_a not in entities_by_disc or disc_b not in entities_by_disc:
        continue
    
    ents_a = entities_by_disc[disc_a]
    ents_b = entities_by_disc[disc_b]
    pair_clashes = 0
    
    for ea in ents_a:
        for eb in ents_b:
            ba = ea["bbox"]
            bb = eb["bbox"]
            
            if ba.intersects(bb):
                # Calcular overlap
                overlap_x = max(0, min(ba.max_x, bb.max_x) - max(ba.min_x, bb.min_x))
                overlap_y = max(0, min(ba.max_y, bb.max_y) - max(ba.min_y, bb.min_y))
                overlap_area = overlap_x * overlap_y
                
                min_area = min(ba.area_2d, bb.area_2d)
                ratio = overlap_area / min_area if min_area > 0 else 0
                
                # Solo reportar clashes significativos
                if ratio > 0.05:
                    if ratio > 0.5:
                        severity = "CRITICO"
                    elif ratio > 0.2:
                        severity = "MAYOR"
                    elif ratio > 0.1:
                        severity = "MENOR"
                    else:
                        severity = "INFO"
                    
                    # Punto de interseccion
                    ix = (max(ba.min_x, bb.min_x) + min(ba.max_x, bb.max_x)) / 2
                    iy = (max(ba.min_y, bb.min_y) + min(ba.max_y, bb.max_y)) / 2
                    
                    clashes.append({
                        "severity": severity,
                        "disc_a": disc_a,
                        "layer_a": ea["layer"],
                        "type_a": ea["type"],
                        "disc_b": disc_b,
                        "layer_b": eb["layer"],
                        "type_b": eb["type"],
                        "overlap_area": overlap_area,
                        "overlap_ratio": ratio,
                        "coord": f"({ix:.1f}, {iy:.1f})",
                        "source": "COM",
                    })
                    pair_clashes += 1
    
    if pair_clashes > 0:
        print(f"    {disc_a} vs {disc_b}: {pair_clashes} clashes")

# Ordenar por severidad
sev_order = {"CRITICO": 0, "MAYOR": 1, "MENOR": 2, "INFO": 3}
clashes.sort(key=lambda c: sev_order.get(c["severity"], 9))

print(f"\n  Total clashes COM: {len(clashes)}")
critical = sum(1 for c in clashes if c["severity"] == "CRITICO")
major = sum(1 for c in clashes if c["severity"] == "MAYOR")
minor = sum(1 for c in clashes if c["severity"] == "MENOR")
info = sum(1 for c in clashes if c["severity"] == "INFO")
print(f"  CRITICO: {critical} | MAYOR: {major} | MENOR: {minor} | INFO: {info}")

# ============================================================
# PASO 2: CLASH VISUAL CON GPT-4o
# ============================================================
print("\n[2/3] Clash detection visual con GPT-4o...")

# Usar las imagenes ya renderizadas (paginas del PDF)
pages_dir = OUTPUT_DIR / "pages"
page_files = sorted(pages_dir.glob("*.png"))[:5]  # Top 5 plantas

if not page_files:
    print("  No hay imagenes renderizadas. Saltando analisis visual.")
    vision_clashes = []
else:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Preparar resumen de clashes COM para contexto
    com_summary = f"Se detectaron {len(clashes)} clashes por bounding box:\n"
    com_summary += f"CRITICO:{critical} MAYOR:{major} MENOR:{minor} INFO:{info}\n"
    for c in clashes[:20]:
        com_summary += (f"  {c['severity']} {c['disc_a']}/{c['layer_a']} vs "
                       f"{c['disc_b']}/{c['layer_b']} en {c['coord']}\n")
    
    CLASH_PROMPT = f"""Analiza este plano arquitectonico buscando CONFLICTOS (clashes) entre disciplinas.

CONTEXTO: El analisis automatico por bounding box encontro estos clashes:
{com_summary}

Busca visualmente:
1. COLUMNAS que atraviesen MUROS de forma incorrecta
2. PUERTAS o VENTANAS bloqueadas por COLUMNAS o VIGAS
3. ESCALERAS que interfieran con elementos estructurales
4. INSTALACIONES (electrica/sanitaria) que crucen elementos estructurales
5. ESPACIOS mal dimensionados o con conflictos geometricos
6. Elementos de una disciplina mal ubicados en la capa de otra

Responde en JSON:
{{
  "visual_clashes": [
    {{
      "severity": "CRITICO/MAYOR/MENOR/INFO",
      "description": "descripcion del conflicto",
      "disciplines_involved": ["A", "S"],
      "location": "ubicacion en el plano",
      "recommendation": "como resolver"
    }}
  ],
  "observations": "observaciones generales sobre coordinacion de disciplinas",
  "coordination_score": 0
}}"""
    
    vision_clashes = []
    for img_path in page_files:
        print(f"  Analizando {img_path.name}...")
        
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un coordinador BIM experto en deteccion de "
                            "interferencias entre disciplinas. Responde en JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": CLASH_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    },
                ],
                max_tokens=2048,
                temperature=0.1,
            )
            
            raw = response.choices[0].message.content
            
            import re
            json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                try:
                    result = json.loads(raw)
                except json.JSONDecodeError:
                    start_idx = raw.find("{")
                    if start_idx >= 0:
                        depth = 0
                        for idx in range(start_idx, len(raw)):
                            if raw[idx] == "{": depth += 1
                            elif raw[idx] == "}":
                                depth -= 1
                                if depth == 0:
                                    result = json.loads(raw[start_idx:idx+1])
                                    break
                    else:
                        result = {"raw": raw}
            
            vc = result.get("visual_clashes", [])
            vision_clashes.extend(vc)
            score = result.get("coordination_score", "?")
            print(f"    {len(vc)} clashes visuales | Score: {score}/10")
            
        except Exception as e:
            print(f"    [ERROR] {e}")

    print(f"\n  Total clashes visuales: {len(vision_clashes)}")

# ============================================================
# PASO 3: REPORTE CONSOLIDADO
# ============================================================
print("\n[3/3] Generando reporte consolidado...")

lines = []
lines.append("=" * 90)
lines.append("REPORTE DE CLASH DETECTION - TORRE GIUALCA I")
lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append(f"Metodo: COM (bounding box) + GPT-4o Vision")
lines.append("=" * 90)

# Resumen
lines.append(f"\n  Clashes COM (geometricos):  {len(clashes)}")
lines.append(f"  Clashes Vision (visuales):  {len(vision_clashes)}")
lines.append(f"  {'─' * 40}")
lines.append(f"  CRITICO: {critical}")
lines.append(f"  MAYOR:   {major}")
lines.append(f"  MENOR:   {minor}")
lines.append(f"  INFO:    {info}")

# Clashes COM
lines.append(f"\n{'_' * 90}")
lines.append("  CLASHES GEOMETRICOS (COM - Bounding Box)")
lines.append(f"{'_' * 90}")

if clashes:
    lines.append(f"\n  {'#':>4} {'Sev':<10} {'Disc.A':<6} {'Capa A':<20} "
                 f"{'Disc.B':<6} {'Capa B':<20} {'Coord':<18} {'Overlap'}")
    lines.append(f"  {'-'*4} {'-'*10} {'-'*6} {'-'*20} "
                 f"{'-'*6} {'-'*20} {'-'*18} {'-'*10}")
    
    for i, c in enumerate(clashes[:100], 1):
        lines.append(
            f"  {i:>4} {c['severity']:<10} "
            f"{c['disc_a']:<6} {c['layer_a'][:20]:<20} "
            f"{c['disc_b']:<6} {c['layer_b'][:20]:<20} "
            f"{c['coord']:<18} {c['overlap_ratio']:.1%}"
        )
    
    if len(clashes) > 100:
        lines.append(f"\n  ... y {len(clashes) - 100} clashes mas")
    
    # Resumen por par de disciplinas
    lines.append(f"\n  Resumen por par de disciplinas:")
    pair_counts = defaultdict(int)
    for c in clashes:
        pair = f"{c['disc_a']} vs {c['disc_b']}"
        pair_counts[pair] += 1
    for pair, count in sorted(pair_counts.items(), key=lambda x: -x[1]):
        lines.append(f"    {pair:<15} {count:>5} clashes")
else:
    lines.append("  No se detectaron clashes geometricos.")

# Clashes Vision
lines.append(f"\n{'_' * 90}")
lines.append("  CLASHES VISUALES (GPT-4o Vision)")
lines.append(f"{'_' * 90}")

if vision_clashes:
    for i, vc in enumerate(vision_clashes, 1):
        sev = vc.get("severity", "?")
        desc = vc.get("description", "")
        discs = ", ".join(vc.get("disciplines_involved", []))
        loc = vc.get("location", "")
        rec = vc.get("recommendation", "")
        
        lines.append(f"\n  [{sev}] Clash #{i}")
        lines.append(f"    Disciplinas: {discs}")
        lines.append(f"    Descripcion: {desc}")
        if loc:
            lines.append(f"    Ubicacion: {loc}")
        if rec:
            lines.append(f"    Recomendacion: {rec}")
else:
    lines.append("  No se detectaron clashes visuales.")

lines.append(f"\n{'=' * 90}")
lines.append("FIN DEL REPORTE DE CLASHES")
lines.append(f"{'=' * 90}")

report = "\n".join(lines)
report_path = OUTPUT_DIR / "CLASH_REPORT_GIUALCA.txt"
report_path.write_text(report, encoding="utf-8")

# Guardar JSON
json_data = {"com_clashes": clashes[:200], "vision_clashes": vision_clashes}
# Serializar BoundingBox
for c in json_data["com_clashes"]:
    if "bbox" in c:
        del c["bbox"]
json_path = OUTPUT_DIR / "clashes.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)

print(f"\n{'=' * 70}")
print("COMPLETADO!")
print(f"  Reporte: {report_path}")
print(f"  JSON:    {json_path}")
print(f"  Clashes COM:    {len(clashes)}")
print(f"  Clashes Vision: {len(vision_clashes)}")
print(f"{'=' * 70}")
