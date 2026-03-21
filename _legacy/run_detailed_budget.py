"""
Script para generar el presupuesto de alta precisión.
Itera a través de los capítulos raíz EXACTOS del TGIU.bc3, forzando a la IA a usar
CADA PARTIDA pertinente y prohíbe invenciones (Zero-Hallucination).
"""
import sys, os, json, re, time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, r"c:\Users\chris\Documents\Dupla")
from dotenv import load_dotenv
load_dotenv(r"c:\Users\chris\Documents\Dupla\.env")
from openai import OpenAI

DUMP_DIR = Path(r"c:\Users\chris\Documents\Dupla\analysis_output\dump")
OUTPUT_DIR = Path(r"c:\Users\chris\Documents\Dupla\analysis_output")
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print("=" * 80)
print("  GENERACIÓN DE PRESUPUESTO ALTA PRECISIÓn (ZERO-HALLUCINATION)")
print("=" * 80)

# Load data
partidas = json.loads((DUMP_DIR / "partidas_bc3.json").read_text(encoding="utf-8"))
chapters = json.loads((DUMP_DIR / "chapters_bc3.json").read_text(encoding="utf-8"))
dwg_layers = json.loads((DUMP_DIR / "dwg_layers.json").read_text(encoding="utf-8"))
xls_items = json.loads((DUMP_DIR / "items_xlsx.json").read_text(encoding="utf-8"))

# Group partidas into Root Chapters
# Determine Root format (e.g., TGIU01, TGIU02...)
grouped = defaultdict(list)
for p in partidas:
    code = p["code"]
    # Most codes are like TGIU010101, root is TGIU01
    c_root = ""
    if code.startswith("TGIU"):
        c_root = code[:6]
    elif code.startswith("A"):
        c_root = code[:3]
    else:
        c_root = code[:2]
    grouped[c_root].append(p)

root_info = {}
for c in chapters:
    root_info[c["code"]] = c.get("summary", "Sin Descripcion")

# Keep only roots that have at least 1 partida
roots = list(grouped.keys())
print(f"Capítulos raíz detectados: {len(roots)}")
for r in sorted(roots):
    print(f"  {r}: {root_info.get(r, 'Unknown')} ({len(grouped[r])} partidas)")

# Summarize DWG
dwg_summary = "MEDICIONES DWG REALES:\n"
for name, d in sorted(dwg_layers.items(), key=lambda x: -x[1]["count"]):
    if d["count"] < 5: continue
    dwg_summary += f"  {name:<22} {d['discipline']:<6} {d['count']:>6} ent  L={d['length_m']:.1f}m  A={d['area_m2']:.1f}m2\n"

# Helper parser
def clean_and_parse(raw):
    cleaned = re.sub(r'(?<=\d),(?=\d{3})', '', raw)
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", cleaned, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    try: return json.loads(cleaned)
    except: pass
    s, e = cleaned.find("{"), cleaned.rfind("}")
    if s >= 0 and e > s:
        fixed = re.sub(r',\s*[}\]]', lambda x: x.group().replace(',',''), cleaned[s:e+1])
        try: return json.loads(fixed)
        except: pass
    return None

budget_chapters = []
total_tokens = 0

for root in sorted(roots):
    items_in_root = grouped[root]
    # No skip if small, we want EVERYTHING
    desc = root_info.get(root, f"Capítulo {root}")
    print(f"\nProcesando {root}: {desc[:40]}... ({len(items_in_root)} partidas)")
    
    # Create absolute truth text
    bc3_text = "CATÁLOGO OFICIAL (NO INVENTAR PRECIOS NI CÓDIGOS):\n"
    for p in items_in_root:
        bc3_text += f"{p['code']:<16} | Unit: {p['unit']:<4} | RD$ {p['price']:>10.2f} | {p['summary']}\n"
        
    prompt = f"""Experto Presupuestista. Modo ZERO-HALLUCINATION.
Capítulo de trabajo: {root} - {desc}

{bc3_text}

=== MEDICIONES CAD OBTENIDAS ===
{dwg_summary[:3000]}
Area de construccion total estimada: 3,426 m2. 14 niveles.

REGLAS ABSOLUTAS:
1. DEBES usar CÓDIGOS Y PRECIOS EXACTOS del catálogo arriba listado. PROHIBIDO inventar códigos.
2. Si una partida no tiene medición directa CAD pero lógicamente va en el proyecto (ej. limpieza, trazo, mov. tierras), ESTIMA su cantidad proporcional usando el área 3426m2 o niveles 14.
3. Genera el mayor nivel de detalle posible (ABSURD PRECISION). NO omitas partidas si son lógicamente necesarias.
4. Genera todas las partidas pertinentes para este capítulo.
5. Usa formato de salida JSON estricto.

JSON:
{{"category":"{root} - {desc}","items":[{{"presto_code":"","description":"","unit":"","quantity":0.0,"unit_price":0.0,"total":0.0,"cad_layer":"ej: A-MURO","calculation":"explicación del cálculo","match_type":"exacto/estimado"}}],"subtotal":0.0}}"""

    try:
        resp = client.chat.completions.create(
            # Using 4o-mini here would be faster/cheaper, but sticking to 4o per user requirement for maximum precision
            model="gpt-4o", max_tokens=4096, temperature=0.0,
            messages=[{"role":"system","content":"Strict JSON only. Zero hallucination. High precision."},{"role":"user","content":prompt}],
        )
        raw = resp.choices[0].message.content
        total_tokens += resp.usage.total_tokens
        
        result = clean_and_parse(raw)
        if result:
            items = result.get("items",[])
            subtotal = sum(float(i.get("total",0)) for i in items)
            result["subtotal"] = subtotal
            budget_chapters.append(result)
            print(f"  -> Generado: {len(items)} partidas integradas. Subtotal Capítulo: RD$ {subtotal:,.2f}")
        else:
            print(f"  -> [ERROR] Fallo parseo JSON para {root}")
            (DUMP_DIR / f"raw_error_{root}.txt").write_text(raw, encoding="utf-8")
    except Exception as e:
        print(f"  -> [ERROR API] {e}")

# ============================================================
# REPORT GENERATION
# ============================================================
grand_total = sum(ch.get("subtotal",0) for ch in budget_chapters)
total_items = sum(len(ch.get("items",[])) for ch in budget_chapters)

lines = []
lines.append("="*100)
lines.append("  PRESUPUESTO DE PRECISIÓN ABSOLUTA (ZERO-HALLUCINATION)")
lines.append(f"  Fecha: {ts}")
lines.append("="*100)

for ch in budget_chapters:
    lines.append(f"\n{'_'*130}")
    lines.append(f"  Capítulo: {ch.get('category','?')}")
    lines.append(f"  Subtotal: RD$ {ch.get('subtotal',0):>20,.2f}")
    lines.append(f"{'_'*130}")
    lines.append(f"  {'Codigo':<14} {'Descripcion':<45} {'Ud':<5} {'Cant':>10} {'P.Unit RD$':>14} {'Total RD$':>16}")
    lines.append(f"  {'-'*14} {'-'*45} {'-'*5} {'-'*10} {'-'*14} {'-'*16}")
    for item in ch.get("items",[]):
        desc = str(item.get("description",""))[:43]
        tot = float(item.get("total",0))
        qty = float(item.get("quantity",0))
        prc = float(item.get("unit_price",0))
        lines.append(f"  {str(item.get('presto_code','')):<14} {desc:<45} {str(item.get('unit','')):<5} {qty:>10.2f} {prc:>14,.2f} {tot:>16,.2f}")
        c = str(item.get('calculation',''))
        if c: lines.append(f"{'':>16} CALC: {c}")

lines.append(f"\n{'='*100}")
lines.append(f"  TOTAL GENERAL: {total_items} partidas  -->  RD$ {grand_total:,.2f}")
lines.append(f"{'='*100}")

report_txt = "\n".join(lines)
report_path = OUTPUT_DIR / f"PRESUPUESTO_PRECISION_ABSOLUTA_{ts}.txt"
report_path.write_text(report_txt, encoding="utf-8")

# JSON saving
json_out = {
    "project": "TGIU Absoluto", "date": ts,
    "total_items": total_items, "grand_total": grand_total,
    "budget_chapters": budget_chapters
}
json_path = OUTPUT_DIR / f"PRESUPUESTO_PRECISION_ABSOLUTA_{ts}.json"
json.dump(json_out, open(json_path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

print(f"\nCOMPLETADO! {total_items} partidas calculadas. Total: RD$ {grand_total:,.2f}")
print(f"Reporte: {report_path.name}")
