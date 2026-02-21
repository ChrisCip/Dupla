"""
Analizador Visual con GPT-4o.

Envia PDFs/imagenes renderizados del DWG a GPT-4o Vision para:
- Identificar elementos constructivos
- Clasificar por tipo (muro, puerta, ventana, columna, etc.)
- Estimar dimensiones y materiales visualmente
- Detectar anomalias (elementos mal clasificados por capa)
- Generar descripciones para presupuesto
"""

import os
import base64
import json
from pathlib import Path
from typing import Optional
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


# ============================================================================
# PROMPTS ESPECIALIZADOS POR DISCIPLINA
# ============================================================================

SYSTEM_PROMPT = """Eres un ingeniero experto en analisis de planos CAD para presupuestos de construccion.
Tu trabajo es analizar imagenes de planos arquitectonicos, estructurales, electricos, etc.
y generar un inventario detallado de elementos constructivos con sus propiedades medibles.

IMPORTANTE:
- Responde SIEMPRE en formato JSON estructurado
- Estima dimensiones en metros basandote en las cotas visibles o la escala del plano
- Si no puedes medir algo exactamente, indica que es una estimacion
- Clasifica cada elemento con su partida presupuestaria correspondiente
- Incluye unidad de medida (m, m2, m3, ud, ml, kg) para cada partida"""

ANALYSIS_PROMPT = """Analiza este plano CAD en detalle. Es un plano de la disciplina: {discipline}

Datos extraidos automaticamente del archivo CAD (COM):
{com_data}

Con base en lo que VES en la imagen y los datos del CAD, genera un JSON con esta estructura:

{{
  "layout_name": "nombre del layout/plano",
  "discipline": "{discipline}",
  "scale": "escala detectada o estimada",
  "elements": [
    {{
      "id": "numero secuencial",
      "type": "tipo de elemento (muro, puerta, ventana, columna, viga, etc.)",
      "layer": "capa CAD probable",
      "description": "descripcion detallada para presupuesto",
      "quantity": 1,
      "unit": "ud/m/m2/m3/ml/kg",
      "dimensions": {{
        "length_m": 0.0,
        "width_m": 0.0,
        "height_m": 0.0,
        "area_m2": 0.0,
        "volume_m3": 0.0
      }},
      "material": "material estimado",
      "budget_category": "partida presupuestaria",
      "confidence": "alta/media/baja",
      "notes": "observaciones"
    }}
  ],
  "anomalies": [
    {{
      "description": "descripcion de la anomalia",
      "location": "ubicacion en el plano",
      "severity": "alta/media/baja"
    }}
  ],
  "summary": {{
    "total_elements": 0,
    "wall_length_m": 0.0,
    "floor_area_m2": 0.0,
    "doors_count": 0,
    "windows_count": 0,
    "columns_count": 0,
    "observations": "observaciones generales"
  }}
}}"""

BUDGET_PROMPT = """Analiza este plano CAD y genera las PARTIDAS PRESUPUESTARIAS.

Datos del archivo CAD:
{com_data}

Para cada elemento visible en el plano, genera una partida con:
- Codigo de partida (ej: 05.01, 05.02)
- Descripcion de la partida
- Unidad de medida (m, m2, m3, ud, ml, kg, gl)
- Cantidad estimada
- Observaciones

Responde en JSON:
{{
  "budget_items": [
    {{
      "code": "01.01",
      "chapter": "nombre del capitulo",
      "description": "descripcion de la partida",
      "unit": "m2",
      "quantity": 0.0,
      "source": "com|visual|estimated",
      "layer": "capa CAD",
      "notes": ""
    }}
  ],
  "chapters": [
    {{
      "code": "01",
      "name": "MOVIMIENTO DE TIERRAS",
      "item_count": 0
    }}
  ]
}}"""


# ============================================================================
# FUNCIONES DE ANALISIS
# ============================================================================

def analyze_pdf(
    pdf_path: Path,
    discipline: str = "General",
    com_data: str = "",
    prompt_type: str = "analysis",
) -> dict:
    """
    Envia un PDF a GPT-4o Vision para analisis.
    
    Args:
        pdf_path: Ruta al PDF del layout
        discipline: Disciplina del plano (A, S, E, P, etc.)
        com_data: Datos extraidos del COM como texto
        prompt_type: "analysis" o "budget"
    
    Returns:
        dict con los resultados del analisis
    """
    client = get_client()
    pdf_path = Path(pdf_path).resolve()
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
    
    print(f"[VISION] Analizando: {pdf_path.name} ({discipline})")
    
    # Codificar PDF a base64
    pdf_b64 = encode_image(pdf_path)
    
    # Seleccionar prompt
    if prompt_type == "budget":
        user_prompt = BUDGET_PROMPT.format(com_data=com_data)
    else:
        user_prompt = ANALYSIS_PROMPT.format(
            discipline=discipline, com_data=com_data
        )
    
    # Llamada a GPT-4o
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
                            "url": f"data:application/pdf;base64,{pdf_b64}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=4096,
        temperature=0.1,  # Bajo para respuestas mas consistentes
    )
    
    raw_text = response.choices[0].message.content
    print(f"[VISION] Respuesta recibida ({len(raw_text)} chars)")
    
    # Parsear JSON de la respuesta
    result = _extract_json(raw_text)
    result["_raw_response"] = raw_text
    result["_model"] = "gpt-4o"
    result["_pdf_file"] = str(pdf_path)
    result["_timestamp"] = datetime.now().isoformat()
    
    return result


def analyze_image(
    image_path: Path,
    discipline: str = "General",
    com_data: str = "",
) -> dict:
    """Analiza una imagen PNG/JPG con GPT-4o."""
    client = get_client()
    image_path = Path(image_path).resolve()
    
    img_b64 = encode_image(image_path)
    ext = image_path.suffix.lower().replace(".", "")
    mime = f"image/{ext}" if ext in ("png", "jpg", "jpeg", "gif", "webp") else "image/png"
    
    user_prompt = ANALYSIS_PROMPT.format(
        discipline=discipline, com_data=com_data
    )
    
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
    result = _extract_json(raw_text)
    result["_raw_response"] = raw_text
    result["_model"] = "gpt-4o"
    result["_image_file"] = str(image_path)
    
    return result


def analyze_multiple(
    file_paths: list[Path],
    discipline: str = "General",
    com_data: str = "",
    prompt_type: str = "analysis",
) -> list[dict]:
    """Analiza multiples PDFs/imagenes secuencialmente."""
    results = []
    for i, path in enumerate(file_paths, 1):
        print(f"\n[VISION] [{i}/{len(file_paths)}] {path.name}")
        try:
            if path.suffix.lower() == ".pdf":
                result = analyze_pdf(path, discipline, com_data, prompt_type)
            else:
                result = analyze_image(path, discipline, com_data)
            results.append(result)
        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({"error": str(e), "file": str(path)})
    return results


# ============================================================================
# UTILIDADES
# ============================================================================

def _extract_json(text: str) -> dict:
    """Extrae JSON de la respuesta del LLM (puede estar envuelto en markdown)."""
    # Intentar parsear directamente
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Buscar bloque JSON en markdown ```json ... ```
    import re
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Buscar primer { ... } valido
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
    
    # No se pudo parsear - devolver texto raw
    return {"raw_text": text, "parse_error": True}


def save_vision_results(results: list[dict], output_path: Path) -> Path:
    """Guarda resultados del analisis visual en JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"[VISION] Resultados guardados: {output_path}")
    return output_path


def generate_vision_report(results: list[dict]) -> str:
    """Genera reporte legible de los resultados del analisis visual."""
    lines = []
    lines.append("=" * 80)
    lines.append("REPORTE DE ANALISIS VISUAL (GPT-4o)")
    lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    
    for i, result in enumerate(results, 1):
        if "error" in result:
            lines.append(f"\n--- Layout {i}: ERROR ---")
            lines.append(f"  {result['error']}")
            continue
        
        layout = result.get("layout_name", f"Layout {i}")
        disc = result.get("discipline", "N/A")
        
        lines.append(f"\n--- {layout} [{disc}] ---")
        
        # Elementos
        elements = result.get("elements", [])
        if elements:
            lines.append(f"  Elementos identificados: {len(elements)}")
            lines.append(f"  {'Tipo':<20} {'Cant':<6} {'Ud':<6} {'Descripcion'}")
            lines.append(f"  {'-'*20} {'-'*6} {'-'*6} {'-'*40}")
            for elem in elements:
                lines.append(
                    f"  {elem.get('type','?'):<20} "
                    f"{elem.get('quantity',0):<6} "
                    f"{elem.get('unit','?'):<6} "
                    f"{elem.get('description','')[:40]}"
                )
        
        # Anomalias
        anomalies = result.get("anomalies", [])
        if anomalies:
            lines.append(f"\n  ANOMALIAS DETECTADAS: {len(anomalies)}")
            for a in anomalies:
                lines.append(f"    [{a.get('severity','?')}] {a.get('description','')}")
        
        # Resumen
        summary = result.get("summary", {})
        if summary:
            lines.append(f"\n  Resumen:")
            for k, v in summary.items():
                if v:
                    lines.append(f"    {k}: {v}")
    
    lines.append("\n" + "=" * 80)
    return "\n".join(lines)
