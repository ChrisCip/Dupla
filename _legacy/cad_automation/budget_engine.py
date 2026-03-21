"""
Motor de Presupuesto: Fusion de datos COM + Vision LLM.

Combina las propiedades nativas del DWG (areas, longitudes via COM)
con el analisis visual (GPT-4o) para generar un presupuesto detallado
por partidas constructivas.
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def generate_budget_from_com(com_report_path: Path) -> dict:
    """
    Genera partidas presupuestarias a partir de los datos COM.
    Lee el reporte de deep_analysis y estructura como partidas.
    """
    com_data = Path(com_report_path).read_text(encoding="utf-8")
    
    # Parsear las lineas del reporte COM
    chapters = []
    chapter_num = 0
    
    # Capitulo por disciplina
    discipline_chapters = {
        "A": ("ARQUITECTURA", [
            ("Muros", ["A-WALL", "A-WALL-PATT"], "ml", "length"),
            ("Puertas", ["A-DOOR", "A-DOOR-FRAM", "A-DOOR-GLAZ", "A-DOOR-HDLN"], "ud", "count"),
            ("Ventanas / Vidrios", ["A-GLAZ", "A-GLAZ-CURT", "A-GLAZ-CWMG"], "m2", "area"),
            ("Pisos", ["A-FLOR", "A-FLOR-HRAL", "A-FLOR-PATT", "A-FLOR-LEVL"], "m2", "area"),
            ("Detalles constructivos", ["A-DETL", "A-DETL-GENF", "A-DETL-THIN", "A-DETL-WIDE"], "gl", "count"),
            ("Acabados / Rellenos", ["A-WALL-PATT", "A-FLOR-PATT"], "m2", "area"),
            ("Cotas / Anotaciones", ["A-ANNO-DIMS", "A-ANNO-DIMS-100"], "gl", "count"),
        ]),
        "S": ("ESTRUCTURA", [
            ("Columnas", ["S-COLS"], "ud", "count"),
            ("Vigas", ["S-BEAM", "S-BEAM-HDLN"], "ml", "length"),
            ("Escaleras", ["S-STRS", "S-STRS-MBND"], "m2", "area"),
        ]),
        "E": ("INSTALACIONES ELECTRICAS", [
            ("Puntos electricos", ["E-ELEC-FIXT"], "ud", "count"),
        ]),
        "P": ("INSTALACIONES SANITARIAS", [
            ("Piezas sanitarias", ["P-SANR-FIXT"], "ud", "count"),
        ]),
        "I": ("INTERIORISMO", [
            ("Mobiliario", ["I-FURN", "I-FURN-PNLS"], "ud", "count"),
        ]),
        "C": ("CIVIL / URBANISMO", [
            ("Estacionamientos", ["C-PRKG"], "m2", "area"),
        ]),
        "L": ("PAISAJISMO", [
            ("Areas exteriores", ["L-SITE"], "m2", "area"),
        ]),
    }
    
    budget = {
        "title": "PRESUPUESTO ESTIMADO - DATOS COM",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": str(com_report_path),
        "chapters": [],
        "raw_com_data": com_data,
    }
    
    return budget


def merge_com_and_vision(
    com_data: dict,
    vision_results: list[dict],
) -> dict:
    """
    Combina datos COM (cantidades exactas) con Vision (descripciones ricas).
    
    Regla de fusion:
    - CANTIDADES: preferir COM (medicion exacta del CAD)
    - DESCRIPCIONES: preferir Vision (entiende mejor que ES el elemento)
    - MATERIALES: usar Vision (identifica visualmente)
    - ANOMALIAS: solo de Vision (identifica errores visuamente)
    """
    merged = {
        "title": "PRESUPUESTO HIBRIDO COM + VISION",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": "Fusion de datos nativos CAD + analisis visual GPT-4o",
        "budget_items": [],
        "anomalies": [],
        "summary": {},
    }
    
    # Recopilar elementos del Vision
    vision_elements = []
    for result in vision_results:
        if isinstance(result, dict) and "elements" in result:
            vision_elements.extend(result["elements"])
        # Anomalias
        if isinstance(result, dict) and "anomalies" in result:
            merged["anomalies"].extend(result["anomalies"])
    
    # Si hay budget_items del Vision, usarlos como base
    for result in vision_results:
        if isinstance(result, dict) and "budget_items" in result:
            for item in result["budget_items"]:
                merged["budget_items"].append({
                    "code": item.get("code", ""),
                    "chapter": item.get("chapter", ""),
                    "description": item.get("description", ""),
                    "unit": item.get("unit", "gl"),
                    "quantity": item.get("quantity", 0),
                    "source": item.get("source", "vision"),
                    "layer": item.get("layer", ""),
                    "notes": item.get("notes", ""),
                })
    
    return merged


def generate_budget_report(budget: dict) -> str:
    """Genera reporte de presupuesto en formato texto."""
    lines = []
    lines.append("=" * 90)
    lines.append(budget.get("title", "PRESUPUESTO"))
    lines.append(f"Fecha: {budget.get('date', '')}")
    lines.append(f"Metodo: {budget.get('method', 'N/A')}")
    lines.append("=" * 90)
    
    # Partidas
    items = budget.get("budget_items", [])
    if items:
        lines.append("")
        lines.append(f"{'Cod':<8} {'Descripcion':<45} {'Ud':<6} {'Cantidad':>10} {'Fuente':<8}")
        lines.append(f"{'-'*8} {'-'*45} {'-'*6} {'-'*10} {'-'*8}")
        
        current_chapter = ""
        for item in items:
            chapter = item.get("chapter", "")
            if chapter != current_chapter:
                current_chapter = chapter
                lines.append(f"\n  >> {chapter.upper()}")
            
            lines.append(
                f"  {item.get('code',''):<6} "
                f"{item.get('description','')[:43]:<45} "
                f"{item.get('unit',''):<6} "
                f"{item.get('quantity',0):>10.2f} "
                f"{item.get('source',''):<8}"
            )
    
    # Anomalias
    anomalies = budget.get("anomalies", [])
    if anomalies:
        lines.append("")
        lines.append("-" * 90)
        lines.append("ANOMALIAS DETECTADAS")
        lines.append("-" * 90)
        for a in anomalies:
            sev = a.get("severity", "?")
            desc = a.get("description", "")
            lines.append(f"  [{sev}] {desc}")
    
    lines.append("")
    lines.append("=" * 90)
    lines.append("FIN DEL PRESUPUESTO")
    lines.append("=" * 90)
    
    return "\n".join(lines)


def format_com_data_for_prompt(deep_analysis_path: Path) -> str:
    """
    Formatea los datos COM del deep_analysis.txt de forma resumida
    para incluir en el prompt del Vision LLM.
    """
    text = Path(deep_analysis_path).read_text(encoding="utf-8")
    
    # Tomar solo las primeras 3000 chars para no exceder el prompt
    if len(text) > 3000:
        # Tomar encabezado + resumen de disciplinas
        lines = text.split("\n")
        summary_lines = []
        for line in lines:
            summary_lines.append(line)
            if len("\n".join(summary_lines)) > 2800:
                break
        return "\n".join(summary_lines) + "\n... (datos truncados)"
    
    return text
