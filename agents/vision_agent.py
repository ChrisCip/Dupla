"""
Vision Agent especializado para la Torre Giualca I.

Combina análisis visual con GPT-4o y validación cruzada computada en Python
usando los datos extraídos del modelo CAD (resumen_procesado.json).
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Cargar API key desde .env
load_dotenv(Path(__file__).parent.parent / ".env")

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

def get_client() -> "OpenAI":
    """Crea cliente OpenAI con la key del .env."""
    if not HAS_OPENAI:
        raise ImportError("openai no instalado. Ejecuta: pip install openai")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY no configurada.\n"
            "Agrega tu key en el archivo .env"
        )
    return OpenAI(api_key=api_key)

def encode_image(image_path: Path) -> str:
    """Codifica una imagen a base64 para enviar a GPT-4o."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _extract_json(text: str) -> dict:
    """Extrae JSON de la respuesta del LLM."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    import re
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start : i + 1])
                    except json.JSONDecodeError:
                        break
                        
    return {"raw_text": text, "parse_error": True}


# ============================================================================
# PROMPTS ESPECIALIZADOS
# ============================================================================

SYSTEM_PROMPT = """Eres un ingeniero experto en presupuestos de construcción (estándar Presto), especializado en análisis visual cuantitativo de planos arquitectónicos.
Tu tarea es contar ELEMENTOS VISUALMENTE y generar partidas usando EXACTAMENTE los nombres de disciplina permitidos.

REGLAS DE ORO:
1. RESPONDE ÚNICAMENTE CON UN JSON VÁLIDO. No añadas texto introductorio ni markdown fuera del bloque JSON.
2. DISCIPLINAS PERMITIDAS: DEBES agrupar todas tus partidas usando EXACTAMENTE estas keys (ignora las que no apliquen):
   - Hormigón Armado
   - Muros y Divisiones
   - Terminación de Superficies
   - Terminación de Pisos
   - Revestimientos
   - Terminación de Escaleras
   - Puertas
   - Ventanas
   - Pintura
   - Cocina
   - Misceláneos
   - Aparatos Sanitarios
   - Instalación Eléctrica
   - Sistema de Agua Potable
   - Sistema de Drenaje de Aguas Negras
   - Sistema Contra Incendios
3. Sigue EXACTAMENTE este schema JSON:
{
  "level": "Nombre del nivel analizado",
  "floor_height_m": 0.0,
  "apartments_count": 0,
  "confidence_score": 0.0,
  "disciplines": {
    "Nombre EXACTO de Disciplina": {
      "items": [
        {
          "description": "Descripción muy específica (ej. Puerta Madera Roble Principal)",
          "unit": "m2/p2/ud/m",
          "quantity_per_floor": 0.0,
          "calculation": "Explicación de cómo contaste o infiriste el valor",
          "confidence": "alta/media/baja",
          "source": "visual_count"
        }
      ]
    }
  }
}"""

PROMPT_PLANTAS = """Analiza la IMAGEN de este plano de PLANTA.
Nivel indicado: {level_name}

=== INSTRUCCIONES ESTRICTAS DE CONTEO Y DESCRIPCIÓN VISUAL ===

1. PUERTAS Y VENTANAS (Tipología y Medición):
   - Ventanas corredizas (líneas dobles en muros exteriores): clasificar como "Ventanas corredera aluminio". Calcula el Área en *p2* (estima dimensiones visuales).
   - Puertas principales (entrada a aptos, suelen ser más anchas): clasificar como "Puerta Madera Roble Principal". Unidad: *ud*.
   - Puertas interiores (habitaciones, baños): clasificar como "Puerta Madera Andiroba Interior". Unidad: *ud*.
   - Puertas de closet (plegables/corredizas): clasificar como "Puerta Madera Closet en Andiroba". Unidad: *p2*.
   - Puertas de aluminio (salida a balcones/servicio): "Puerta Comercial aluminio batiente". Unidad: *ud*.
   - Puerta general (escalera/ascensor): "Puerta Polimetálica blanca". Unidad: *ud*.

2. MUROS, PISOS Y SUPERFICIES (Unidad *m2*):
   - Muros gruesos (bloque 15cm) vs Muros divisorios delgados (bloque 10cm). Fórmula: `Largo x {altura_entrepiso} - Vanos`.
   - Terminación de Superficies (Pañete/Fraguache): estima área multiplicando el área total de muros x 2 (ambas caras).
   - Pintura: similar al pañete.
   - Pisos (Porcelanato/Cerámica): estima los *m2* visualmente basadas en el área de planta.

3. SISTEMAS OCULTOS E INFERENCIA:
   - APARATOS SANITARIOS (*ud*): Cuenta inodoros, lavamanos y duchas en cada baño. Fregaderos en cada cocina.
   - TUBERÍAS (*m*): Estima metros lineales de "Agua Potable" y "Drenaje" basándote en la distancia visual de los baños/cocinas al ducto o núcleo.
   - INSTALACIÓN ELÉCTRICA (*ud*): Infiera basado en habitaciones. Ej: si ves habitaciones, baños y sala, calcula ~6 tomacorrientes/luces por espacio principal.
   
=== REFERENCIA DE CALIBRACIÓN ===
Un piso tipo documentado de esta torre tiene aproximadamente:
- 5 apartamentos funcionales
- ~29 puertas individuales en total (no p2 de closet)
- ~7 baños (7 inodoros, 7 duchas, 7 lavamanos)
- ~669 m2 de muro de bloque 15cm y ~32 m2 bloque 10cm
- ~578 p2 de ventanas
- ~90 tomacorrientes y ~53 salidas de luz
Usa esto como ancla si tu conteo visual se desvía exageradamente.

=== DATOS DE APOYO DEL CAD (DIMENSIONES Y ÁREAS) ===
{json_data}
====================================================

Genera las partidas con DESCRIPCIONES DETALLADAS, UNIDADES CORRECTAS y en las DISCIPLINAS EXACTAS dictadas."""

PROMPT_ELEVACIONES = """Analiza este plano de ELEVACION/FACHADA.
Nivel indicado: {level_name}

=== INSTRUCCIONES ===
1. Confirma alturas de entrepiso leyendo visualmente las cotas NPT.
2. Cuenta las ventanas por fachada visibles (estima p2).
3. Identifica materiales exteriores y acabados (pañete, pintura, etc en m2). 
Usa las Disciplinas exactas ("Terminación de Superficies", "Ventanas", "Pintura").

=== DATOS DE APOYO ===
{json_data}
======================"""

PROMPT_SITIO = """Analiza este plano de SITIO/EMPLAZAMIENTO.
Nivel indicado: {level_name}

=== INSTRUCCIONES ===
1. Extrae área total del solar visualmente de las tablas o linderos.
2. Identifica circulaciones y parqueos.
Usa Disciplinas exactas ("Movimiento de Tierras", "Misceláneos").

=== DATOS DE APOYO ===
{json_data}
======================"""


# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def format_json_summary_for_prompt(json_summary: dict) -> str:
    """Extrae SÓLO información geométrica (dimensiones, áreas) para no ensuciar el conteo del LLM."""
    if not json_summary:
        return "No hay datos JSON disponibles."
    
    lines = []
    usable = json_summary.get('usable_data', {})
    
    # Dimensiones (00-MEDICION)
    dims = usable.get("dimensions", [])
    if dims:
        lines.append(f"Cotas reales extraídas del modelo (Layer 00-MEDICION) para usar como regla de escala:")
        for i, d in enumerate(dims[:15]): 
            lines.append(f"  - {d.get('measurement')}")
    
    # Áreas de Columnas (S-COLS)
    hatches = usable.get("hatches_with_area", [])
    if hatches:
        cols = [h for h in hatches if 'S-COLS' in h.get('layer', '')]
        if cols:
            lines.append(f"\nÁreas detectadas de columnas estructurales (m2):")
            lines.append(f"  {[c.get('area') for c in cols[:10]]}")
            
    # TABLA NPT HARDCODEADA COMO REFERENCIA
    lines.append("\nTabla de Alturas NPT de Referencia del Edificio:")
    lines.append("- Semi Sótano: -1.40 (altura libre: 1.40m)")
    lines.append("- Nivel 1: NPT 0.00 (altura: 3.05m)")
    lines.append("- Nivel 2: NPT 3.05 (altura: 2.55m)")
    lines.append("- Nivel 3: NPT 5.60 (altura: 4.70m)")
    lines.append("- Nivel 4-14: (altura típica: 3.24m)")
            
    return "\n".join(lines)


def run_cross_validation(result: dict, json_summary: dict) -> dict:
    """Python compara el conteo visual de GPT-4o contra las líneas del CAD."""
    validation = {
        "json_cross_checks": []
    }
    
    layers = json_summary.get("layer_summary", {})
    
    # Extraer cantidades visuales dictadas por GPT-4o
    vision_doors = 0
    vision_windows = 0
    
    disciplines_out = result.get("disciplines", {})
    
    # Búsqueda en todas las disciplinas iterando sobre items
    for disc_name, disc_data in disciplines_out.items():
        for item in disc_data.get("items", []):
            desc = item.get("description", "").lower()
            if item.get("unit") in ["ud", "un", "unidad", "unidades"]:
                if "puerta" in desc:
                    vision_doors += item.get("quantity_per_floor", 0)
                elif "ventana" in desc:
                    vision_windows += item.get("quantity_per_floor", 0)

    # Validar Puertas vs Líneas A-DOOR
    a_door_lines = layers.get("A-DOOR", {}).get("object_count", 0)
    if vision_doors > 0 and a_door_lines > 0:
        lines_per_door = a_door_lines / vision_doors
        status = "ok" if 20 <= lines_per_door <= 100 else "warning"
        msg = f"Ratio: {lines_per_door:.1f} líneas por puerta (ideal 30-70)"
        validation["json_cross_checks"].append({
            "check": "door_count_ratio",
            "vision": vision_doors,
            "json_estimate": f"{a_door_lines} líneas CAD",
            "status": status,
            "message": msg
        })

    # Validar Ventanas vs Líneas A-GLAZ
    a_glaz_lines = layers.get("A-GLAZ", {}).get("object_count", 0)
    if vision_windows > 0 and a_glaz_lines > 0:
        lines_per_window = a_glaz_lines / vision_windows
        status = "ok" if 15 <= lines_per_window <= 150 else "warning"
        msg = f"Ratio: {lines_per_window:.1f} líneas por ventana"
        validation["json_cross_checks"].append({
            "check": "window_count_ratio",
            "vision": vision_windows,
            "json_estimate": f"{a_glaz_lines} líneas CAD",
            "status": status,
            "message": msg
        })
        
    result["validation"] = validation
    return result


def analyze_plan(image_path: Path, json_summary: dict, level_name: str) -> dict:
    """Invoca la API de Visión usando el prompt adecuado y hace validación cruzada."""
    client = get_client()
    image_path = Path(image_path).resolve()
    
    if not image_path.exists():
        raise FileNotFoundError(f"Imagen no encontrada: {image_path}")

    # Determinar qué prompt usar
    name_lower = image_path.name.lower()
    if "01" in name_lower or "02" in name_lower or "sitio" in name_lower:
        base_prompt = PROMPT_SITIO
    elif "12" in name_lower or "13" in name_lower or "14" in name_lower or "elev" in name_lower:
        base_prompt = PROMPT_ELEVACIONES
    else:
        base_prompt = PROMPT_PLANTAS

    formatted_json = format_json_summary_for_prompt(json_summary)
    # inyectar a PROMPT_PLANTAS
    user_prompt = base_prompt.format(
        level_name=level_name, 
        json_data=formatted_json,
        altura_entrepiso="3.24m" # por simplificar la iteracion en el prompt actual
    )

    print(f"\n[VISION] Analizando: {image_path.name}")
    print(f"[VISION] Construyendo payload GPT-4o...")

    img_b64 = encode_image(image_path)
    ext = image_path.suffix.lower().replace(".", "")
    mime = f"image/{ext}" if ext in ("png", "jpg", "jpeg", "webp") else "image/png"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{img_b64}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=4096,
        temperature=0.1,
    )

    raw_text = response.choices[0].message.content
    print(f"[VISION] OK: Respuesta LLM recibida")
    
    result = _extract_json(raw_text)
    
    if not result.get("parse_error"):
        result = run_cross_validation(result, json_summary)
        
    result["_raw_response"] = raw_text
    result["_metadata"] = {
        "file": image_path.name,
        "timestamp": datetime.now().isoformat()
    }
    
    return result


def run_full_vision_analysis(pages_dir: str, json_summary: dict) -> list[dict]:
    """Itera sobre todas las páginas en el directorio y consolida los resultados."""
    pages_path = Path(pages_dir)
    images = sorted([p for p in pages_path.iterdir() if p.suffix.lower() in ('.png', '.jpg')])
    
    results = []
    for img in images:
        level_name = f"Nivel {img.name}" 
        try:
            res = analyze_plan(img, json_summary, level_name)
            results.append(res)
        except Exception as e:
            results.append({"error": str(e), "file": img.name})
            
    return results

if __name__ == "__main__":
    # Prueba del script con los nuevos settings
    json_path = Path("resumen_procesado.json") if Path("resumen_procesado.json").exists() else Path("../resumen_procesado.json")
    
    json_data = {}
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            
    test_image = Path("_legacy/vision_output/pages/page_08.png") if Path("_legacy/vision_output/pages/page_08.png").exists() else Path("../_legacy/vision_output/pages/page_08.png")
    
    if test_image.exists():
        res = analyze_plan(test_image, json_data, "NIVEL 5 APTOS N13.54 (N5-8)")
        out_path = Path("vision_test_result.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        print(f"\n[INFO] Ejecución completada. Revisa {out_path} para los resultados refinados.")
    else:
        print(f"Imagen de prueba no encontrada: {test_image}")
