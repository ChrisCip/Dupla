"""
Pipeline: Analisis completo COM + GPT-4o para presupuesto.

Estrategia:
- Usa los datos COM ya extraidos (dwg_deep_analysis.txt) 
- Envia los datos COMPLETOS a GPT-4o para generar presupuesto por partidas
- Si hay PDFs exportados manualmente, los incluye en el analisis visual
"""

import sys, os, json, base64, re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, r"c:\Users\chris\Documents\Dupla")

from dotenv import load_dotenv
load_dotenv(r"c:\Users\chris\Documents\Dupla\.env")

from openai import OpenAI

OUTPUT_DIR = Path(r"c:\Users\chris\Documents\Dupla\vision_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# PASO 1: Leer datos COM completos
# ============================================================
print("=" * 70)
print("PIPELINE: PRESUPUESTO POR PARTIDAS CON GPT-4o")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

com_data = open(r"c:\Users\chris\Documents\Dupla\dwg_deep_analysis.txt",
                "r", encoding="utf-8").read()
print(f"\n[1/3] Datos COM cargados ({len(com_data)} chars)")

# ============================================================
# PASO 2: Enviar datos completos a GPT-4o
# ============================================================
print("\n[2/3] Enviando a GPT-4o para presupuesto completo...")
print("  (esto puede tomar 20-40 segundos)")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

prompt = f"""Eres un ingeniero presupuestista senior con 20 anios de experiencia.

Analiza estos datos extraidos NATIVAMENTE de un archivo DWG que contiene los planos
de un proyecto de edificacion llamado "GIUALCA I". 

TODAS las cantidades son MEDICIONES REALES del CAD en METROS.

={("=" * 70)}
DATOS COMPLETOS DEL CAD (28,568 entidades analizadas):
={("=" * 70)}
{com_data}

INSTRUCCIONES:
1. Genera un presupuesto COMPLETO organizado en CAPITULOS y PARTIDAS
2. Usa UNICAMENTE las cantidades del CAD - no inventes numeros
3. Interpreta correctamente las capas NCS:
   - A-WALL = muros (longitud total = metros lineales de muro)
   - A-WALL-PATT = hatch/relleno de muros (area = m2 de muro en planta)
   - A-DOOR = lineas de puertas, A-DOOR-FRAM = marcos
   - A-DOOR-GLAZ = vidrio en puertas
   - A-GLAZ = vidrios/ventanas (longitud = perimetro de ventanas)
   - A-FLOR = pisos, A-FLOR-HRAL = barandas/herrajes, A-FLOR-PATT = patron de piso
   - A-FLOR-LEVL = niveles (area de plataformas)
   - S-COLS = columnas (hatches = seccion, 56m2 total)
   - S-BEAM = vigas (29m longitud)
   - S-STRS = escaleras (513m de lineas)
   - E-ELEC-FIXT = puntos electricos (5,102 entidades)
   - P-SANR-FIXT = piezas sanitarias
   - I-FURN = mobiliario
   - C-PRKG = estacionamientos
   - 00-MEDICION = areas medidas (3,426 m2 en polylines cerradas)
4. Estima CANTIDADES DE PUERTAS analizando: 
   A-DOOR tiene 770 entidades (lineas+arcos de representacion de puertas)
   A-DOOR-FRAM tiene 1,472 lineas de marcos
   Cada puerta tipica tiene ~6-10 lineas de marco -> estima ~150-200 puertas
5. Estima COLUMNAS: S-COLS tiene 383 lineas + 2 hatches de 56m2
6. Para MUROS: A-WALL tiene 3,493 lineas totalizando 2,044m
7. Los hatches de A-WALL-PATT (18 m2) representan el area de muro en planta
8. Incluye partidas para TODAS las disciplinas encontradas

Responde SOLO en JSON con esta estructura (sin texto adicional):
{{
  "project": "GIUALCA I",
  "date": "{datetime.now().strftime('%Y-%m-%d')}",
  "units": "Metros (areas en m2, longitudes en m)",
  "chapters": [
    {{
      "code": "01",
      "name": "NOMBRE DEL CAPITULO",
      "items": [
        {{
          "code": "01.01",
          "description": "Descripcion completa de la partida",
          "unit": "m2/m/ml/ud/kg/m3/gl",
          "quantity": 0.00,
          "cad_layer": "A-WALL",
          "measurement_type": "longitud/area/conteo/estimado",
          "notes": "como se obtuvo la cantidad"
        }}
      ]
    }}
  ],
  "summary": {{
    "total_chapters": 0,
    "total_items": 0,
    "total_wall_length_m": 2044,
    "total_floor_area_m2": 0,
    "estimated_doors": 0,
    "estimated_columns": 0,
    "total_measured_area_m2": 3426,
    "observations": "observaciones del presupuestista"
  }}
}}"""

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": (
                "Eres un ingeniero presupuestista senior. "
                "Responde SIEMPRE en formato JSON valido, sin texto adicional. "
                "Usa las cantidades EXACTAS del CAD."
            ),
        },
        {"role": "user", "content": prompt},
    ],
    max_tokens=4096,
    temperature=0.1,
)

result_text = response.choices[0].message.content
tokens = response.usage.total_tokens
cost = tokens * 0.000005  # ~$5/1M tokens para GPT-4o
print(f"  Respuesta: {len(result_text)} chars")
print(f"  Tokens: {tokens} (~${cost:.4f} USD)")

# Guardar raw
raw_path = OUTPUT_DIR / "gpt4o_raw.txt"
raw_path.write_text(result_text, encoding="utf-8")

# Parsear JSON
json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", result_text, re.DOTALL)
if json_match:
    budget = json.loads(json_match.group(1))
else:
    try:
        budget = json.loads(result_text)
    except json.JSONDecodeError:
        # Buscar primer { ... }
        start = result_text.find("{")
        if start >= 0:
            depth = 0
            for i in range(start, len(result_text)):
                if result_text[i] == "{": depth += 1
                elif result_text[i] == "}": 
                    depth -= 1
                    if depth == 0:
                        budget = json.loads(result_text[start:i+1])
                        break
        else:
            budget = {"error": "No JSON found", "raw": result_text}

# Guardar JSON
json_path = OUTPUT_DIR / "budget.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(budget, f, ensure_ascii=False, indent=2)
print(f"  JSON: {json_path}")

# ============================================================
# PASO 3: Generar reporte legible
# ============================================================
print("\n[3/3] Generando reporte de presupuesto...")

lines = []
lines.append("=" * 90)
lines.append(f"PRESUPUESTO POR PARTIDAS")
lines.append(f"Proyecto: {budget.get('project', 'GIUALCA I')}")
lines.append(f"Fecha: {budget.get('date', datetime.now().strftime('%Y-%m-%d'))}")
lines.append(f"Unidades: {budget.get('units', 'Metros')}")
lines.append(f"Metodo: Datos nativos CAD + interpretacion GPT-4o")
lines.append("=" * 90)

chapters = budget.get("chapters", [])
total_items = 0

for chapter in chapters:
    code = chapter.get("code", "")
    name = chapter.get("name", "")
    items = chapter.get("items", [])
    
    lines.append(f"\n{'_' * 90}")
    lines.append(f"  {code}. {name.upper()}")
    lines.append(f"{'_' * 90}")
    lines.append("")
    lines.append(
        f"  {'Cod':<10}{'Descripcion':<40}{'Ud':<6}"
        f"{'Cantidad':>12}  {'Capa CAD':<15}  {'Fuente'}"
    )
    lines.append(f"  {'-'*10}{'-'*40}{'-'*6}{'-'*12}  {'-'*15}  {'-'*20}")
    
    for item in items:
        total_items += 1
        desc = item.get("description", "")[:38]
        lines.append(
            f"  {item.get('code',''):<10}"
            f"{desc:<40}"
            f"{item.get('unit',''):<6}"
            f"{item.get('quantity',0):>12.2f}  "
            f"{item.get('cad_layer','')[:15]:<15}  "
            f"{item.get('measurement_type','')}"
        )
        notes = item.get("notes", "")
        if notes:
            lines.append(f"{'':>12}>> {notes[:75]}")

# Resumen
summary = budget.get("summary", {})
lines.append(f"\n{'=' * 90}")
lines.append("RESUMEN GENERAL")
lines.append(f"{'=' * 90}")
lines.append(f"  Total capitulos: {len(chapters)}")
lines.append(f"  Total partidas:  {total_items}")

if summary:
    for k, v in summary.items():
        if v and k != "observations":
            k_display = k.replace("_", " ").title()
            lines.append(f"  {k_display}: {v}")
    obs = summary.get("observations", "")
    if obs:
        lines.append(f"\n  Observaciones del presupuestista:")
        lines.append(f"  {obs}")

lines.append(f"\n{'=' * 90}")
lines.append("FIN DEL PRESUPUESTO")
lines.append(f"{'=' * 90}")

report = "\n".join(lines)

report_path = OUTPUT_DIR / "PRESUPUESTO_GIUALCA.txt"
report_path.write_text(report, encoding="utf-8")

print(f"\n{'=' * 70}")
print("COMPLETADO!")
print(f"  Presupuesto:  {report_path}")
print(f"  JSON datos:   {json_path}")
print(f"  Tokens:       {tokens} (~${cost:.4f} USD)")
print(f"{'=' * 70}")
