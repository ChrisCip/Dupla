"""
PRESUPUESTO FINAL: BC3 completo (607 partidas) + DWG (28k ents) + GPT-4o.

1. Carga la estructura completa del BC3 (codigos, precios, unidades)
2. Carga las mediciones del DWG (deep_analysis)
3. GPT-4o recibe AMBAS fuentes y genera un presupuesto matcheando:
   - Codigos Presto con elementos CAD
   - Precios unitarios del PZH/BC3 con cantidades del CAD
"""

import sys, os, json, re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, r"c:\Users\chris\Documents\Dupla")
from dotenv import load_dotenv
load_dotenv(r"c:\Users\chris\Documents\Dupla\.env")
from openai import OpenAI

OUTPUT_DIR = Path(r"c:\Users\chris\Documents\Dupla\vision_output")

print("=" * 70)
print("PRESUPUESTO FINAL: BC3 + DWG + GPT-4o")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ============================================================
# Cargar datos BC3
# ============================================================
bc3_data = json.loads(
    Path(r"c:\Users\chris\Documents\Dupla\presto_files\bc3_full_data.json")
    .read_text(encoding="utf-8")
)

# Preparar resumen de BC3 para GPT-4o (limitado a tokens razonables)
partidas = bc3_data["partidas"]
chapters = bc3_data["chapters"]

print(f"\n[BC3] Partidas: {len(partidas)}, Capitulos: {len(chapters)}")

# Build structured summary for GPT-4o
bc3_text = "CATALOGO COMPLETO DE PARTIDAS PRESTO (BC3)\n"
bc3_text += "=" * 70 + "\n\n"

# Chapters
bc3_text += "CAPITULOS:\n"
for ch in chapters[:40]:
    bc3_text += f"  {ch['code']}: {ch['summary']}\n"

bc3_text += f"\nPARTIDAS ({len(partidas)} items):\n"
bc3_text += f"{'Codigo':<16} {'Ud':<6} {'Precio':>12}  {'Descripcion'}\n"
bc3_text += "-" * 80 + "\n"

# Send ALL partidas to GPT-4o
for p in partidas:
    bc3_text += f"{p['code']:<16} {p['unit']:<6} {p['price']:>12,.2f}  {p['summary'][:60]}\n"

# ============================================================
# Cargar datos DWG
# ============================================================
dwg_data = Path(r"c:\Users\chris\Documents\Dupla\dwg_deep_analysis.txt").read_text(encoding="utf-8")
print(f"[DWG] {len(dwg_data)} chars de datos")

# ============================================================
# GPT-4o: Matchear BC3 + DWG
# ============================================================
print(f"\n[GPT-4o] Generando presupuesto completo...")
print(f"  BC3: {len(bc3_text)} chars | DWG: {len(dwg_data)} chars")
print(f"  Esto puede tomar 30-60 segundos...")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

prompt = f"""Eres un presupuestista senior de construccion en Republica Dominicana.

TIENES DOS FUENTES DE DATOS COMPLETAS:

=== FUENTE 1: CATALOGO DE PRECIOS PRESTO (archivo BC3 - Presto 8.8) ===
Este es el catalogo COMPLETO con codigos, unidades y precios unitarios en RD$.
Usa estos codigos y precios EXACTAMENTE como estan:

{bc3_text[:12000]}

=== FUENTE 2: MEDICIONES DEL PLANO DWG (extraidas por COM de Civil 3D) ===
Entidades medidas directamente del archivo CAD del proyecto TORRE GIUALCA I:

{dwg_data}

=== INSTRUCCIONES ===

1. Para CADA capa del DWG, busca la partida Presto que mejor corresponda
2. Usa el PRECIO del catalogo Presto y la CANTIDAD del CAD
3. Organiza por CAPITULOS logicos de construccion
4. Asignaciones clave:
   - A-WALL (muros 2,044m) -> busca partidas de muros/panetes/bloques
   - A-DOOR (~160 puertas) -> busca partidas de puertas
   - A-GLAZ (ventanas 181m) -> busca partidas de ventanas/vidrios
   - S-COLS (columnas 56m2) -> busca partidas de columnas/acero/hormigon
   - S-BEAM (vigas 29m) -> busca partidas de vigas
   - S-STRS (escaleras 513m) -> busca partidas de escaleras
   - A-FLOR (pisos) -> busca partidas de pisos/ceramica
   - E-ELEC (5102 pts) -> busca partidas electricas
   - P-SANR (26 piezas) -> busca partidas sanitarias
   - 00-MEDICION (3,426 m2) -> area construida total
5. Calcula: TOTAL = precio_unitario * cantidad_CAD
6. Si hay varias partidas posibles para un elemento, incluye las principales
7. Incluye partidas de:
   - Hormigon (estructural)
   - Acero (refuerzo)
   - Bloques (muros)
   - Panete (acabados muros)
   - Pintura (acabados)
   - Instalaciones electricas
   - Instalaciones sanitarias
   - Puertas y ventanas

Responde SOLO en JSON (sin texto adicional):
{{
  "project": "TORRE GIUALCA I",
  "location": "Santo Domingo, Republica Dominicana",
  "currency": "RD$",
  "bc3_source": "CTXI0000TRM.bc3",
  "chapters": [
    {{
      "code": "01",
      "name": "NOMBRE DEL CAPITULO",
      "subtotal": 0.00,
      "items": [
        {{
          "presto_code": "codigo del BC3",
          "description": "descripcion de la partida",
          "unit": "ud/m/m2/m3/ml/pa/kg/gl",
          "quantity": 0.00,
          "unit_price": 0.00,
          "total": 0.00,
          "cad_source": "capa CAD o fuente de la cantidad",
          "match": "exacto/estimado/calculado"
        }}
      ]
    }}
  ],
  "grand_total": 0.00,
  "summary": {{
    "total_chapters": 0,
    "total_items": 0,
    "area_construida_m2": 3426,
    "costo_por_m2": 0.00,
    "observations": ""
  }}
}}"""

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": (
                "Eres un presupuestista senior dominicano. "
                "Genera presupuestos completos en JSON usando SOLO codigos "
                "y precios del catalogo Presto proporcionado. "
                "Precios en RD$ (pesos dominicanos)."
            ),
        },
        {"role": "user", "content": prompt},
    ],
    max_tokens=4096,
    temperature=0.1,
)

result_text = response.choices[0].message.content
tokens = response.usage.total_tokens
cost = tokens * 0.000005
print(f"  Tokens: {tokens} (~${cost:.4f} USD)")

# Save raw response FIRST
raw_path = OUTPUT_DIR / "gpt4o_budget_raw.txt"
raw_path.write_text(result_text, encoding="utf-8")
print(f"  Raw saved: {raw_path}")

# Clean: remove commas from numbers (GPT-4o uses 1,000.00 format)
def clean_json_numbers(text):
    """Remove commas from numbers like 1,000.00 -> 1000.00"""
    return re.sub(r'(?<=\d),(?=\d{3}(?:[.\d]|[,\d]{3}))', '', text)

cleaned_text = clean_json_numbers(result_text)

# Parse JSON - robust handling
budget = None

# Try 1: direct JSON
try:
    budget = json.loads(cleaned_text)
except json.JSONDecodeError:
    pass

# Try 2: JSON in code block
if budget is None:
    json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", cleaned_text, re.DOTALL)
    if json_match:
        try:
            budget = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

# Try 3: Find first { to last }
if budget is None:
    start = cleaned_text.find("{")
    end = cleaned_text.rfind("}")
    if start >= 0 and end > start:
        try:
            budget = json.loads(cleaned_text[start:end+1])
        except json.JSONDecodeError:
            # Try fixing common issues
            fixed = cleaned_text[start:end+1]
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            try:
                budget = json.loads(fixed)
            except json.JSONDecodeError as e:
                print(f"  [WARN] JSON parse failed: {e}")
                budget = {"error": str(e), "raw_length": len(cleaned_text)}

if budget is None:
    budget = {"error": "no JSON found", "raw_length": len(result_text)}

# Save JSON
json_path = OUTPUT_DIR / "PRESUPUESTO_FINAL.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(budget, f, ensure_ascii=False, indent=2)

# Generate readable report
lines = []
lines.append("=" * 100)
lines.append(f"  PRESUPUESTO DE OBRA - {budget.get('project', 'TORRE GIUALCA I')}")
lines.append(f"  Ubicacion: {budget.get('location', 'Santo Domingo, RD')}")
lines.append(f"  Moneda: {budget.get('currency', 'RD$')}")
lines.append(f"  Catalogo: {budget.get('bc3_source', 'CTXI0000TRM.bc3')}")
lines.append(f"  Fecha: {datetime.now().strftime('%Y-%m-%d')}")
lines.append(f"  Metodo: Precios Presto BC3 + Mediciones CAD DWG + GPT-4o")
lines.append("=" * 100)

grand_total = 0
total_items = 0

for chapter in budget.get("chapters", []):
    ch_code = chapter.get("code", "")
    ch_name = chapter.get("name", "")
    items = chapter.get("items", [])
    ch_total = sum(i.get("total", 0) for i in items)
    grand_total += ch_total
    
    lines.append(f"\n{'_' * 100}")
    lines.append(f"  {ch_code}. {ch_name.upper()}")
    lines.append(f"  Subtotal: RD$ {ch_total:>15,.2f}")
    lines.append(f"{'_' * 100}")
    lines.append("")
    lines.append(
        f"  {'Cod Presto':<14} {'Descripcion':<35} {'Ud':<5}"
        f"{'Cant':>10} {'P.Unit':>12} {'Total RD$':>16} {'Fuente CAD'}"
    )
    lines.append(f"  {'-'*14} {'-'*35} {'-'*5}{'-'*10} {'-'*12} {'-'*16} {'-'*15}")
    
    for item in items:
        total_items += 1
        desc = item.get("description", "")[:33]
        total = item.get("total", 0)
        lines.append(
            f"  {item.get('presto_code',''):<14} {desc:<35} "
            f"{item.get('unit',''):<5}"
            f"{item.get('quantity',0):>10.2f} "
            f"{item.get('unit_price',0):>12,.2f} "
            f"{total:>16,.2f} "
            f"{item.get('cad_source','')[:15]}"
        )

# Summary
lines.append(f"\n{'=' * 100}")
lines.append(f"  TOTAL GENERAL:  RD$ {grand_total:>18,.2f}")
lines.append(f"{'=' * 100}")

summary = budget.get("summary", {})
area = summary.get("area_construida_m2", 3426)
costo_m2 = grand_total / area if area > 0 else 0

lines.append(f"\n  Capitulos:        {len(budget.get('chapters', []))}")
lines.append(f"  Partidas:         {total_items}")
lines.append(f"  Area construida:  {area:,.0f} m2")
lines.append(f"  Costo por m2:     RD$ {costo_m2:,.2f}")
if summary.get("observations"):
    lines.append(f"\n  Observaciones: {summary['observations']}")

lines.append(f"\n{'=' * 100}")

report = "\n".join(lines)
report_path = OUTPUT_DIR / "PRESUPUESTO_FINAL_GIUALCA.txt"
report_path.write_text(report, encoding="utf-8")

print(f"\n{'=' * 70}")
print("PRESUPUESTO FINAL GENERADO!")
print(f"  Reporte:    {report_path}")
print(f"  JSON:       {json_path}")
print(f"  Total:      RD$ {grand_total:,.2f}")
print(f"  Costo/m2:   RD$ {costo_m2:,.2f}")
print(f"  Partidas:   {total_items}")
print(f"{'=' * 70}")
