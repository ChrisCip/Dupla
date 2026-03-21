"""
Analisis Visual + OCR de planos PDF con GPT-4o.

1. Convierte cada pagina del PDF a imagen (PNG alta resolucion)
2. Envia cada pagina a GPT-4o con prompt de OCR + medicion
3. Extrae: nomenclaturas, cotas, areas, elementos con dimensiones
4. Genera un objeto JSON estructurado con todas las mediciones
"""

import sys, os, json, base64
from pathlib import Path
from datetime import datetime

sys.path.insert(0, r"c:\Users\chris\Documents\Dupla")

from dotenv import load_dotenv
load_dotenv(r"c:\Users\chris\Documents\Dupla\.env")

from openai import OpenAI
import fitz  # PyMuPDF

PDF_PATH = Path(r"c:\Users\chris\Documents\Dupla\vision_output\pdfs\8- ACAD-PLANOS GIUALCA I - RV7 - EXP.039-025.dwg SOLO IMPRESION.pdf")
OUTPUT_DIR = Path(r"c:\Users\chris\Documents\Dupla\vision_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# PASO 1: Convertir PDF a imagenes
# ============================================================
print("=" * 70)
print("ANALISIS VISUAL + OCR CON GPT-4o")
print(f"PDF: {PDF_PATH.name}")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

print("\n[1/3] Convirtiendo PDF a imagenes...")
img_dir = OUTPUT_DIR / "pages"
img_dir.mkdir(parents=True, exist_ok=True)

doc = fitz.open(str(PDF_PATH))
total_pages = len(doc)
print(f"  Paginas: {total_pages}")

page_images = []
for i in range(total_pages):
    page = doc[i]
    # Render a 200 DPI (buena calidad para OCR)
    mat = fitz.Matrix(200/72, 200/72)
    pix = page.get_pixmap(matrix=mat)
    img_path = img_dir / f"page_{i+1:02d}.png"
    pix.save(str(img_path))
    size_kb = img_path.stat().st_size / 1024
    print(f"  [OK] Pagina {i+1}/{total_pages} -> {img_path.name} ({size_kb:.0f} KB)")
    page_images.append(img_path)

doc.close()
print(f"\n  {len(page_images)} imagenes generadas en {img_dir}")

# ============================================================
# PASO 2: Analizar cada pagina con GPT-4o
# ============================================================
print("\n[2/3] Analizando paginas con GPT-4o (OCR + Vision)...")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Leer datos COM para contexto
com_data = open(r"c:\Users\chris\Documents\Dupla\dwg_deep_analysis.txt",
                "r", encoding="utf-8").read()
# Resumen corto del COM para no exceder tokens
com_summary = com_data[:2000]

OCR_PROMPT = """Analiza este plano arquitectonico/constructivo con precision de ingeniero.

CONTEXTO DEL PROYECTO (datos del CAD):
{com_summary}

INSTRUCCIONES:
1. Lee TODAS las cotas, dimensiones y textos visibles en el plano (OCR)
2. Identifica CADA espacio/ambiente con su nombre y area si esta anotada
3. Identifica elementos constructivos: muros, puertas, ventanas, columnas, escaleras
4. Lee la escala del plano si esta visible
5. Lee el titulo/nombre del layout
6. Identifica nomenclaturas de ejes (A, B, C... / 1, 2, 3...)

Responde en JSON:

{{
  "page_number": {page_num},
  "layout_name": "nombre del layout si es visible",
  "scale": "escala detectada (ej: 1:100, 1:50)",
  "title_block": {{
    "project_name": "",
    "drawing_title": "",
    "revision": "",
    "date": ""
  }},
  "grid_axes": {{
    "horizontal": ["A", "B", "C"],
    "vertical": ["1", "2", "3"],
    "dimensions_between_axes_m": []
  }},
  "spaces": [
    {{
      "name": "nombre del espacio (ej: SALA, COCINA, DORMITORIO)",
      "area_m2": 0.0,
      "level": "nivel si visible (ej: PB, P1, P2)",
      "notes": ""
    }}
  ],
  "dimensions_found": [
    {{
      "value_m": 0.0,
      "description": "que mide esta cota (ej: ancho de muro, largo de pasillo)",
      "location": "donde esta en el plano"
    }}
  ],
  "elements": [
    {{
      "type": "muro/puerta/ventana/columna/escalera/viga/otro",
      "description": "descripcion detallada",
      "quantity": 1,
      "dimensions": {{
        "length_m": 0.0,
        "width_m": 0.0,
        "height_m": 0.0,
        "area_m2": 0.0
      }},
      "material": "material si visible",
      "location": "ubicacion en el plano"
    }}
  ],
  "texts_found": [
    "lista de todos los textos legibles en el plano"
  ],
  "observations": "observaciones generales sobre este plano"
}}"""

all_results = []

for idx, img_path in enumerate(page_images):
    page_num = idx + 1
    print(f"\n  [{page_num}/{total_pages}] Analizando {img_path.name}...")
    
    # Codificar imagen
    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    prompt = OCR_PROMPT.format(com_summary=com_summary, page_num=page_num)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un ingeniero experto en lectura de planos CAD. "
                        "Extraes TODAS las medidas, textos y nomenclaturas visibles. "
                        "Responde SOLO en JSON valido."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
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
            max_tokens=4096,
            temperature=0.1,
        )
        
        raw = response.choices[0].message.content
        tokens = response.usage.total_tokens
        
        # Parsear JSON
        import re
        json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                start = raw.find("{")
                if start >= 0:
                    depth = 0
                    for i in range(start, len(raw)):
                        if raw[i] == "{": depth += 1
                        elif raw[i] == "}":
                            depth -= 1
                            if depth == 0:
                                result = json.loads(raw[start:i+1])
                                break
                else:
                    result = {"raw": raw, "parse_error": True}
        
        result["_tokens"] = tokens
        result["_page_file"] = img_path.name
        all_results.append(result)
        
        spaces = len(result.get("spaces", []))
        dims = len(result.get("dimensions_found", []))
        elems = len(result.get("elements", []))
        texts = len(result.get("texts_found", []))
        print(f"    {tokens} tokens | {spaces} espacios | {dims} cotas | "
              f"{elems} elementos | {texts} textos")
        
    except Exception as e:
        print(f"    [ERROR] {e}")
        all_results.append({"error": str(e), "page": page_num})

# ============================================================
# PASO 3: Consolidar y generar reporte
# ============================================================
print(f"\n[3/3] Consolidando resultados...")

# Guardar JSON completo
json_path = OUTPUT_DIR / "vision_ocr_results.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

# Generar reporte texto
lines = []
lines.append("=" * 90)
lines.append("ANALISIS VISUAL + OCR - PROYECTO GIUALCA I")
lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append(f"Paginas analizadas: {len(all_results)}")
lines.append(f"Modelo: GPT-4o (high detail)")
lines.append("=" * 90)

# Consolidar todos los espacios
all_spaces = []
all_dimensions = []
all_elements = []
all_texts = []

for result in all_results:
    if "error" in result:
        continue
    
    page = result.get("page_number", "?")
    layout = result.get("layout_name", "?")
    scale = result.get("scale", "?")
    
    lines.append(f"\n{'_' * 90}")
    lines.append(f"  PAGINA {page}: {layout} (Escala: {scale})")
    lines.append(f"{'_' * 90}")
    
    # Title block
    tb = result.get("title_block", {})
    if tb:
        lines.append(f"  Proyecto: {tb.get('project_name', '')}")
        lines.append(f"  Plano: {tb.get('drawing_title', '')}")
    
    # Ejes
    grid = result.get("grid_axes", {})
    if grid:
        h = ", ".join(grid.get("horizontal", []))
        v = ", ".join(grid.get("vertical", []))
        if h or v:
            lines.append(f"  Ejes: H=[{h}]  V=[{v}]")
    
    # Espacios
    spaces = result.get("spaces", [])
    if spaces:
        lines.append(f"\n  ESPACIOS/AMBIENTES ({len(spaces)}):")
        lines.append(f"  {'Nombre':<30} {'Area m2':>10} {'Nivel':<10}")
        lines.append(f"  {'-'*30} {'-'*10} {'-'*10}")
        for sp in spaces:
            name = sp.get("name", "?")
            area = sp.get("area_m2", 0)
            level = sp.get("level", "")
            lines.append(f"  {name:<30} {area:>10.2f} {level:<10}")
            all_spaces.append(sp)
    
    # Cotas
    dims = result.get("dimensions_found", [])
    if dims:
        lines.append(f"\n  COTAS/DIMENSIONES ({len(dims)}):")
        for d in dims:
            val = d.get("value_m", 0)
            desc = d.get("description", "")
            lines.append(f"    {val:>8.2f} m  | {desc}")
            all_dimensions.append(d)
    
    # Elementos
    elems = result.get("elements", [])
    if elems:
        lines.append(f"\n  ELEMENTOS CONSTRUCTIVOS ({len(elems)}):")
        for el in elems:
            typ = el.get("type", "?")
            desc = el.get("description", "")[:40]
            qty = el.get("quantity", 1)
            dims_el = el.get("dimensions", {})
            dim_str = ""
            if dims_el.get("length_m"):
                dim_str += f"L={dims_el['length_m']}m "
            if dims_el.get("width_m"):
                dim_str += f"W={dims_el['width_m']}m "
            if dims_el.get("area_m2"):
                dim_str += f"A={dims_el['area_m2']}m2"
            lines.append(f"    {typ:<12} x{qty:<3} {desc:<40} {dim_str}")
            all_elements.append(el)
    
    # Textos
    texts = result.get("texts_found", [])
    all_texts.extend(texts)

# Resumen consolidado
lines.append(f"\n{'=' * 90}")
lines.append("RESUMEN CONSOLIDADO (TODAS LAS PAGINAS)")
lines.append(f"{'=' * 90}")
lines.append(f"  Total espacios: {len(all_spaces)}")
lines.append(f"  Total cotas: {len(all_dimensions)}")
lines.append(f"  Total elementos: {len(all_elements)}")
lines.append(f"  Total textos: {len(all_texts)}")

if all_spaces:
    total_area = sum(s.get("area_m2", 0) for s in all_spaces)
    lines.append(f"\n  Area total de espacios: {total_area:.2f} m2")
    lines.append(f"\n  {'Espacio':<30} {'Area m2':>10}")
    lines.append(f"  {'-'*30} {'-'*10}")
    for sp in sorted(all_spaces, key=lambda s: s.get("area_m2", 0), reverse=True):
        if sp.get("area_m2", 0) > 0:
            lines.append(f"  {sp.get('name','?'):<30} {sp.get('area_m2',0):>10.2f}")

lines.append(f"\n{'=' * 90}")
lines.append("FIN DEL ANALISIS VISUAL")
lines.append(f"{'=' * 90}")

report = "\n".join(lines)
report_path = OUTPUT_DIR / "ANALISIS_VISUAL_GIUALCA.txt"
report_path.write_text(report, encoding="utf-8")

total_tokens = sum(r.get("_tokens", 0) for r in all_results if "_tokens" in r)
cost = total_tokens * 0.000005

print(f"\n{'=' * 70}")
print("COMPLETADO!")
print(f"  Reporte:    {report_path}")
print(f"  JSON datos: {json_path}")
print(f"  Tokens:     {total_tokens} (~${cost:.4f} USD)")
print(f"  Espacios:   {len(all_spaces)}")
print(f"  Cotas:      {len(all_dimensions)}")
print(f"  Elementos:  {len(all_elements)}")
print(f"{'=' * 70}")
