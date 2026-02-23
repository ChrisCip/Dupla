"""
Presupuesto COMPLETO por partes: envia partidas BC3 agrupadas por capitulo
a GPT-4o junto con los datos del DWG correspondientes.

Cada capitulo = 1 llamada a GPT-4o = resultado mas detallado.
"""

import sys, os, json, re, time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, r"c:\Users\chris\Documents\Dupla")
from dotenv import load_dotenv
load_dotenv(r"c:\Users\chris\Documents\Dupla\.env")
from openai import OpenAI

OUTPUT_DIR = Path(r"c:\Users\chris\Documents\Dupla\vision_output")

print("=" * 70)
print("PRESUPUESTO DETALLADO POR CAPITULOS")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ============================================================
# 1. Cargar BC3 completo
# ============================================================
bc3 = json.loads(
    Path(r"c:\Users\chris\Documents\Dupla\presto_files\bc3_full_data.json")
    .read_text(encoding="utf-8")
)
partidas = bc3["partidas"]
chapters_raw = bc3["chapters"]
print(f"\n[BC3] {len(partidas)} partidas, {len(chapters_raw)} capitulos")

# ============================================================
# 2. Agrupar partidas por disciplina/tipo
# ============================================================
groups = {
    "01_MOVIMIENTO_TIERRAS": {
        "name": "Movimiento de Tierras y Cimentacion",
        "keywords": ["excav", "relleno", "caliche", "zapata", "cimenta", "desalojo",
                     "bote", "tierra", "compacta", "nivelac"],
        "cad_layers": "S-STRS (escaleras 513m), 00-MEDICION (3426 m2 area)",
        "partidas": [],
    },
    "02_ESTRUCTURA": {
        "name": "Estructura (Hormigon, Acero, Columnas, Vigas)",
        "keywords": ["hormig", "acero", "varilla", "columna", "viga", "losa",
                     "encofrado", "estrib", "malla", "fundicion", "armad",
                     "desencofr", "concreto"],
        "cad_layers": "S-COLS (columnas 383 ent, 56m2 hatches), S-BEAM (vigas 29m), S-STRS (escaleras 513m)",
        "partidas": [],
    },
    "03_MUROS": {
        "name": "Muros, Bloques, Panetes, Revestimientos",
        "keywords": ["muro", "bloque", "pañete", "panete", "repello", "fraguach",
                     "revesti", "fino", "grueso", "alban"],
        "cad_layers": "A-WALL (3493 ent, 2044m lineas), A-WALL-PATT (961 ent, 18m2 hatches)",
        "partidas": [],
    },
    "04_PISOS": {
        "name": "Pisos, Ceramica, Porcelanato, Zocalos",
        "keywords": ["piso", "ceramic", "porcelan", "zocalo", "rodapie", "baldosa",
                     "pulido", "nivelac"],
        "cad_layers": "A-FLOR (pisos), A-FLOR-PATT, A-FLOR-HRAL (barandas 1062m), A-FLOR-LEVL (11.8 m2)",
        "partidas": [],
    },
    "05_PUERTAS_VENTANAS": {
        "name": "Puertas, Ventanas, Vidrios, Herrajes",
        "keywords": ["puerta", "ventana", "vidrio", "herraje", "cerradura", "bisagra",
                     "marco", "llav", "alumin", "closet", "cristal"],
        "cad_layers": "A-DOOR (770 ent, ~160 puertas), A-DOOR-FRAM (1472 ent), A-DOOR-GLAZ (0.08m2), A-GLAZ (181m ventanas)",
        "partidas": [],
    },
    "06_INSTALACIONES_ELECTRICAS": {
        "name": "Instalaciones Electricas y Telecomunicaciones",
        "keywords": ["elect", "cable", "interruptor", "toma", "panel", "breaker",
                     "tuberia emt", "luminari", "lampar", "aliment", "acometida",
                     "centro de carga", "transformador", "tierra", "condulet"],
        "cad_layers": "E-ELEC-FIXT (5102 entidades - puntos electricos)",
        "partidas": [],
    },
    "07_INSTALACIONES_SANITARIAS": {
        "name": "Instalaciones Sanitarias, Plomeria, Agua, Gas",
        "keywords": ["sanitar", "inodoro", "lavamanos", "ducha", "bañera", "cisterna",
                     "bomba", "tuberia pvc", "tubo", "pvc", "llave", "valvula",
                     "trampa", "registro", "plomer", "agua", "desague", "drenaje"],
        "cad_layers": "P-SANR-FIXT (26 piezas sanitarias)",
        "partidas": [],
    },
    "08_PINTURA_ACABADOS": {
        "name": "Pintura y Acabados Finales",
        "keywords": ["pintur", "impermeab", "sellador", "barniz", "esmalte",
                     "latex", "acabado", "decorac"],
        "cad_layers": "A-WALL (2044m muros a pintar), A-ANNO-DIMS (dimensiones)",
        "partidas": [],
    },
    "09_EQUIPAMIENTO": {
        "name": "Mobiliario, Equipos, Miscelaneos",
        "keywords": ["mueble", "mobili", "equip", "ascensor", "elevador",
                     "estaciona", "andamio", "limpieza", "seguridad",
                     "fumig", "topograf"],
        "cad_layers": "I-FURN (8 ent mobiliario), C-PRKG (estacionamientos 7.4m)",
        "partidas": [],
    },
    "10_OTROS": {
        "name": "Gastos Indirectos, Desperdicios, Otros",
        "keywords": ["desperdicio", "indirect", "gastos", "supervis", "itbis",
                     "ayudante", "peon"],
        "cad_layers": "General",
        "partidas": [],
    },
}

# Classify each partida into a group
unclassified = []
for p in partidas:
    desc = (p.get("summary", "") + " " + p.get("code", "")).lower()
    assigned = False
    for gid, group in groups.items():
        for kw in group["keywords"]:
            if kw in desc:
                group["partidas"].append(p)
                assigned = True
                break
        if assigned:
            break
    if not assigned:
        unclassified.append(p)

# Add unclassified to "OTROS"
groups["10_OTROS"]["partidas"].extend(unclassified)

print("\nAgrupacion de partidas:")
for gid, group in groups.items():
    count = len(group["partidas"])
    if count > 0:
        print(f"  {gid}: {group['name']} -> {count} partidas")

# ============================================================
# 3. DWG data
# ============================================================
dwg_data = Path(r"c:\Users\chris\Documents\Dupla\dwg_deep_analysis.txt").read_text(encoding="utf-8")

# ============================================================
# 4. GPT-4o por capitulo
# ============================================================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def clean_json_numbers(text):
    return re.sub(r'(?<=\d),(?=\d{3})', '', text)

def parse_gpt_json(raw):
    cleaned = clean_json_numbers(raw)
    # Try code block
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    # Try direct
    try:
        return json.loads(cleaned)
    except:
        pass
    # Try extract
    s = cleaned.find("{")
    e = cleaned.rfind("}")
    if s >= 0 and e > s:
        fixed = cleaned[s:e+1]
        fixed = re.sub(r',\s*}', '}', fixed)
        fixed = re.sub(r',\s*]', ']', fixed)
        try:
            return json.loads(fixed)
        except:
            pass
    return None

all_chapters = []
total_tokens = 0

for gid, group in sorted(groups.items()):
    if not group["partidas"]:
        continue
    
    gname = group["name"]
    gpartidas = group["partidas"]
    cad_info = group["cad_layers"]
    
    print(f"\n[GPT-4o] {gid}: {gname} ({len(gpartidas)} partidas)...")
    
    # Build partida list for this group
    partida_list = ""
    for p in gpartidas:
        partida_list += f"{p['code']:<16} {p['unit']:<6} {p['price']:>12,.2f}  {p['summary'][:60]}\n"
    
    prompt = f"""Eres un presupuestista senior de construccion en Republica Dominicana.

CAPITULO: {gname}

PARTIDAS DISPONIBLES DEL CATALOGO PRESTO (precios en RD$):
{partida_list}

DATOS DEL PLANO CAD (proyecto TORRE GIUALCA I, edificio 14 niveles):
Capas relevantes: {cad_info}

Datos completos del CAD:
{dwg_data[:2000]}

Area construida total: 3,426 m2 (de capa 00-MEDICION)
Edificio: 14 niveles + Penthouse + Semi-sotano

INSTRUCCIONES:
1. Selecciona las partidas del catalogo que apliquen para este capitulo
2. Asigna cantidades basadas en las mediciones del CAD
3. Para items sin medicion directa, ESTIMA basandote en el area (3426 m2) y niveles (14+)
4. El precio unitario DEBE ser el del catalogo Presto
5. Incluye TODAS las partidas relevantes, no solo las principales

Responde SOLO en JSON:
{{
  "chapter_code": "{gid[:2]}",
  "chapter_name": "{gname}",
  "items": [
    {{
      "presto_code": "codigo",
      "description": "descripcion",
      "unit": "ud",
      "quantity": 0.00,
      "unit_price": 0.00,
      "total": 0.00,
      "cad_source": "capa CAD o estimacion",
      "match": "exacto/estimado/calculado"
    }}
  ],
  "subtotal": 0.00
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Presupuestista dominicano. Solo JSON."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=0.1,
        )
        
        raw = response.choices[0].message.content
        tokens = response.usage.total_tokens
        total_tokens += tokens
        
        result = parse_gpt_json(raw)
        if result:
            items = result.get("items", [])
            subtotal = sum(float(i.get("total", 0)) for i in items)
            result["subtotal"] = subtotal
            all_chapters.append(result)
            print(f"  {len(items)} partidas -> RD$ {subtotal:,.2f} ({tokens} tokens)")
        else:
            print(f"  [WARN] JSON parse failed")
            # Save raw for debug
            (OUTPUT_DIR / f"raw_{gid}.txt").write_text(raw, encoding="utf-8")
        
        time.sleep(1)  # Rate limit
        
    except Exception as e:
        print(f"  [ERROR] {e}")

# ============================================================
# 5. Consolidar y generar reporte final
# ============================================================
print(f"\n{'=' * 70}")
print("Generando reporte final consolidado...")

grand_total = sum(ch.get("subtotal", 0) for ch in all_chapters)
total_items = sum(len(ch.get("items", [])) for ch in all_chapters)
area = 3426
costo_m2 = grand_total / area if area > 0 else 0

# JSON completo
budget_final = {
    "project": "TORRE GIUALCA I",
    "location": "Santo Domingo, Republica Dominicana",
    "currency": "RD$",
    "bc3_source": "CTXI0000TRM.bc3",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "method": "BC3 Presto + DWG CAD + GPT-4o (por capitulos)",
    "chapters": all_chapters,
    "grand_total": grand_total,
    "summary": {
        "total_chapters": len(all_chapters),
        "total_items": total_items,
        "area_m2": area,
        "costo_por_m2": costo_m2,
        "total_tokens": total_tokens,
        "cost_usd": total_tokens * 0.000005,
    }
}

json_path = OUTPUT_DIR / "PRESUPUESTO_DETALLADO.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(budget_final, f, ensure_ascii=False, indent=2)

# Reporte texto
lines = []
lines.append("=" * 105)
lines.append(f"  PRESUPUESTO DETALLADO DE OBRA")
lines.append(f"  Proyecto: TORRE GIUALCA I")
lines.append(f"  Ubicacion: Santo Domingo, Republica Dominicana")
lines.append(f"  Moneda: RD$ (Pesos Dominicanos)")
lines.append(f"  Catalogo: CTXI0000TRM.bc3 (Presto 8.8)")
lines.append(f"  Fecha: {datetime.now().strftime('%Y-%m-%d')}")
lines.append(f"  Metodo: Precios Presto + Mediciones CAD + GPT-4o")
lines.append("=" * 105)

for ch in all_chapters:
    ch_code = ch.get("chapter_code", "")
    ch_name = ch.get("chapter_name", "")
    items = ch.get("items", [])
    subtotal = ch.get("subtotal", 0)
    
    lines.append(f"\n{'_' * 105}")
    lines.append(f"  CAP {ch_code}. {ch_name.upper()}")
    lines.append(f"  Subtotal: RD$ {subtotal:>18,.2f}")
    lines.append(f"{'_' * 105}")
    lines.append("")
    lines.append(
        f"  {'Cod Presto':<14} {'Descripcion':<38} {'Ud':<5}"
        f"{'Cant':>10} {'P.Unit RD$':>14} {'Total RD$':>16} {'Match'}"
    )
    lines.append(
        f"  {'-'*14} {'-'*38} {'-'*5}"
        f"{'-'*10} {'-'*14} {'-'*16} {'-'*10}"
    )
    
    for item in items:
        desc = str(item.get("description", ""))[:36]
        total = float(item.get("total", 0))
        qty = float(item.get("quantity", 0))
        price = float(item.get("unit_price", 0))
        lines.append(
            f"  {str(item.get('presto_code','')):<14} {desc:<38} "
            f"{str(item.get('unit','')):<5}"
            f"{qty:>10.2f} "
            f"{price:>14,.2f} "
            f"{total:>16,.2f} "
            f"{str(item.get('match',''))}"
        )

# Resumen general
lines.append(f"\n{'=' * 105}")
lines.append(f"  RESUMEN POR CAPITULOS")
lines.append(f"{'=' * 105}")
for ch in all_chapters:
    lines.append(
        f"  {ch.get('chapter_code',''):>4}. {ch.get('chapter_name',''):<50} "
        f"RD$ {ch.get('subtotal',0):>18,.2f}"
    )
lines.append(f"  {'':>4}  {'─'*50} {'─'*22}")
lines.append(f"  {'':>4}  {'TOTAL GENERAL':<50} RD$ {grand_total:>18,.2f}")
lines.append(f"\n  Area construida: {area:,.0f} m2")
lines.append(f"  Costo por m2:    RD$ {costo_m2:,.2f}")
lines.append(f"  Total partidas:  {total_items}")
lines.append(f"{'=' * 105}")

report = "\n".join(lines)
report_path = OUTPUT_DIR / "PRESUPUESTO_DETALLADO_GIUALCA.txt"
report_path.write_text(report, encoding="utf-8")

cost = total_tokens * 0.000005
print(f"\n{'=' * 70}")
print("PRESUPUESTO DETALLADO COMPLETADO!")
print(f"  Reporte:   {report_path}")
print(f"  JSON:      {json_path}")
print(f"  Capitulos: {len(all_chapters)}")
print(f"  Partidas:  {total_items}")
print(f"  Total:     RD$ {grand_total:,.2f}")
print(f"  Costo/m2:  RD$ {costo_m2:,.2f}")
print(f"  Tokens:    {total_tokens} (~${cost:.4f} USD)")
print(f"{'=' * 70}")
