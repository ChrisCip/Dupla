import json
import os
import re
from collections import defaultdict
from typing import Any, Dict

FEET_TO_M = 0.3048
INCH_TO_M = 0.0254
SQFT_TO_M2 = 0.09290304

# Mapping AIA to the 21 real budget disciplines of Dupla
AIA_TO_DISCIPLINE = {
    "A-WALL": "Muros y Divisiones",
    "S-COLS": "Hormigón Armado",
    "S-BEAM": "Hormigón Armado",
    "S-FNDN": "Hormigón Armado",
    "S-SLAB": "Hormigón Armado",
    "A-FLOR": "Terminación de Pisos",
    "A-DOOR": "Puertas",
    "A-GLAZ": "Ventanas",
    "A-WIND": "Ventanas",
    "A-ROOF": "Terminación de Superficies",
    "A-CLNG": "Terminación de Superficies",
    "A-FIN": "Revestimientos",
    "A-STRS": "Terminación de Escaleras",
    "P-SANR": "Aparatos Sanitarios",
    "P-PIPE": "Sistema de Agua Potable",
    "P-DWV": "Drenaje de Aguas Negras",
    "E-POWR": "Instalación Eléctrica",
    "E-LITE": "Instalación Eléctrica",
    "E-FDR": "Alimentadores Eléctricos",
    "E-GENR": "Sistema de Generación",
    "M-FIRE": "Sistema Contra Incendios",
    "F-PROT": "Sistema Contra Incendios",
    "C-TOPO": "Movimiento de Tierra",
    "A-PNT": "Pintura",
    "A-EQPM-KITCH": "Cocina"
}

def get_discipline(layer_name):
    if not layer_name:
        return "Misceláneos"
    layer_name = str(layer_name).upper()
    
    # Check prefixes
    for prefix, disc in AIA_TO_DISCIPLINE.items():
        if layer_name.startswith(prefix):
            return disc
            
    # Fallbacks based on common terms
    if "MEDICION" in layer_name:
        return "Misceláneos"  # Capa utility
    
    return "Misceláneos"


def _extract_first_number(value: Any):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    txt = str(value).strip().replace(",", "")
    match = re.search(r"[-+]?\d*\.?\d+", txt)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _length_to_meters(value: Any):
    num = _extract_first_number(value)
    if num is None:
        return None

    src = str(value).lower() if value is not None else ""
    if "feet" in src or "foot" in src or " ft" in src or src.endswith("ft"):
        return round(num * FEET_TO_M, 4)
    if "inch" in src or " in" in src or src.endswith("in"):
        return round(num * INCH_TO_M, 4)
    if "mm" in src:
        return round(num / 1000.0, 4)
    if "cm" in src:
        return round(num / 100.0, 4)
    # Default: asumir metros cuando no se especifica unidad.
    return round(num, 4)


def _area_to_m2(value: Any, source_key: str = ""):
    num = _extract_first_number(value)
    if num is None:
        return None

    src = f"{str(value).lower()} {str(source_key).lower()}"
    if (
        "sq ft" in src
        or "square feet" in src
        or "ft2" in src
        or "ft^2" in src
        or "(sq ft)" in src
    ):
        return round(num * SQFT_TO_M2, 4)
    # Default: asumir m2 cuando no se especifica unidad.
    return round(num, 4)

def process_autodesk_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    collection = []
    if isinstance(data, dict):
        if "views" in data:
            for view in data.get("views", []):
                collection.extend(view.get("objects", []))
        elif "data" in data and "collection" in data["data"]:
            collection = data["data"]["collection"]
    elif isinstance(data, list):
        collection = data
        
    layer_summary_out = {}
    usable_data_hatches = []
    usable_data_texts = []
    usable_data_dims = []
    usable_data_blocks = []
    discipline_summary_out: Any = defaultdict(lambda: {"layers": set(), "what_json_gives": "", "what_needs_vision": ""})
    
    layer_counts: Any = defaultdict(lambda: {"object_count": 0, "types": defaultdict(int), "discipline": "", "budget_relevant": False, "notes": ""})
    
    for obj in collection:
        name = str(obj.get("name", ""))
        props = obj.get("properties", {})
        
        # 1. Obteniendo el Layer
        layer = None
        for category, cat_props in props.items():
            if isinstance(cat_props, dict):
                for k, v in cat_props.items():
                    if "layer" in k.lower():
                        layer = v
                        break
            if layer: break
            
        if not layer:
            layer = "UNKNOWN"
            
        # 2. Obteniendo el Type real desde properties > General > "Name "
        #    El campo "Name " (con espacio al final) contiene el tipo real del objeto
        #    Eg: "Hatch", "Block Reference", "Rotated Dimension", "Text", "MText", "Line"
        general = props.get("General", {})
        entity_type_raw = None
        for key in general:
            if key.strip().lower() == "name":
                entity_type_raw = str(general[key]).strip()
                break
        
        # Mapear el tipo real a categorías usables
        obj_type = "Entity"
        if entity_type_raw:
            etr_lower = entity_type_raw.lower()
            if etr_lower == "line":
                obj_type = "Line"
            elif etr_lower == "polyline" or etr_lower == "lwpolyline":
                obj_type = "Polyline"
            elif etr_lower == "hatch":
                obj_type = "Hatch"
            elif etr_lower == "text":
                obj_type = "Text"
            elif etr_lower == "mtext":
                obj_type = "MText"
            elif "dimension" in etr_lower:
                # Cubre "Rotated Dimension", "Aligned Dimension", etc.
                obj_type = "Dimension"
            elif etr_lower == "block reference":
                obj_type = "Block Reference"
            elif etr_lower == "arc":
                obj_type = "Arc"
            elif etr_lower == "circle":
                obj_type = "Circle"
            elif etr_lower == "spline":
                obj_type = "Spline"
            elif etr_lower == "solid":
                obj_type = "Solid"
            else:
                obj_type = entity_type_raw  # Guardar tipo original si no matchea
        else:
            # Fallback: intentar detectar desde obj["name"] (caso legacy)
            name_lower = name.lower()
            if "line" in name_lower and "polyline" not in name_lower:
                obj_type = "Line"
            elif "polyline" in name_lower:
                obj_type = "Polyline"
            elif "hatch" in name_lower:
                obj_type = "Hatch"
            elif "text" in name_lower and "mtext" not in name_lower:
                obj_type = "Text"
            elif "mtext" in name_lower:
                obj_type = "MText"
            elif "dimension" in name_lower:
                obj_type = "Dimension"
            elif "block reference" in name_lower or "insert" in name_lower:
                obj_type = "Block Reference"
            
        # 3. Contando métricas
        layer_summary = layer_counts[layer]
        layer_summary["object_count"] += 1
        layer_summary["types"][obj_type] += 1
        disc = get_discipline(layer)
        layer_summary["discipline"] = disc
        
        # 4. Extrayendo data útil (usable_data)
        if obj_type == "Hatch":
            area_raw = None
            area_key = ""
            geometry = props.get("Geometry", {})
            if "Area" in geometry:
                area_raw = geometry["Area"]
                area_key = "Area"
            elif "Area (sq ft)" in geometry:
                area_raw = geometry["Area (sq ft)"]
                area_key = "Area (sq ft)"

            area_m2 = _area_to_m2(area_raw, area_key)
            if area_m2 is not None:
                pattern_info = props.get("Pattern", {})
                usable_data_hatches.append({
                    "layer": layer,
                    "area": area_m2,
                    "area_raw": area_raw,
                    "area_unit": "m2",
                    "pattern_name": pattern_info.get("Pattern name", ""),
                    "fill_type": pattern_info.get("Fill type", "")
                })
                layer_summary["budget_relevant"] = True
                
        elif obj_type in ["Text", "MText"]:
            text_val = ""
            # El contenido del texto está en properties > Text > Contents
            text_section = props.get("Text", {})
            if "Contents" in text_section:
                text_val = text_section["Contents"]
            
            # Fallback: buscar en todas las categorías
            if not text_val:
                for p_dict in props.values():
                    if isinstance(p_dict, dict):
                        if "Contents" in p_dict:
                            text_val = p_dict["Contents"]
                            break
                        elif "Value" in p_dict:
                            text_val = p_dict["Value"]
                            break
            
            usable_data_texts.append({
                "layer": layer,
                "type": obj_type,
                "text": text_val if text_val else "(sin contenido visible)",
                "style": text_section.get("Style", "")
            })
            if text_val:
                layer_summary["budget_relevant"] = True
                
        elif obj_type == "Dimension":
            # No filtrar por layer — extraer de CUALQUIER layer
            measurement = None
            dim_type = entity_type_raw if entity_type_raw else "Dimension"
            text_section = props.get("Text", {})
            if "Measurement" in text_section:
                measurement = text_section["Measurement"]
            
            # Fallback
            if measurement is None:
                for p_dict in props.values():
                    if isinstance(p_dict, dict):
                        if "Measurement" in p_dict:
                            measurement = p_dict["Measurement"]
                            break
                        elif "Measurement Value" in p_dict:
                            measurement = p_dict["Measurement Value"]
                            break
            
            if measurement is not None:
                measurement_m = _length_to_meters(measurement)
                usable_data_dims.append({
                    "layer": layer,
                    "measurement": measurement_m if measurement_m is not None else measurement,
                    "measurement_raw": measurement,
                    "measurement_unit": "m" if measurement_m is not None else "",
                    "dim_type": dim_type,
                    "dim_style": props.get("Misc", {}).get("Dim style", "")
                })
                layer_summary["budget_relevant"] = True
                
        elif obj_type == "Block Reference":
            # El nombre del bloque está en obj["name"], limpiar el sufijo hex [XXXXXX]
            block_name = re.sub(r'\s*\[[0-9A-Fa-f]+\]\s*$', '', name).strip()
            usable_data_blocks.append({
                "layer": layer,
                "block_name": block_name,
                "handle": general.get("Handle", "")
            })
            layer_summary["budget_relevant"] = True

    # 5. Generar notas analíticas honestas y formatear resultados
    for l, ls in layer_counts.items():
        lines = ls["types"].get("Line", 0)
        polylines = ls["types"].get("Polyline", 0)
        
        if (lines + polylines) > 0 and (lines + polylines) > ls["object_count"] * 0.7:
            ls["notes"] = f"{lines + polylines} segmentos (Lines/Polylines) — NO es longitud del elemento. Inútil para sumar metros constructivos."
            if not ls["budget_relevant"]:
                ls["budget_relevant"] = False
        elif ls["types"].get("Hatch", 0) > 0 and ls["budget_relevant"]:
            ls["notes"] = "Hatches con área detectada. Útil directamente para cálculo de superficies/volúmenes."
        elif ls["types"].get("Block Reference", 0) > 0:
            ls["notes"] = "Block References nativos. Podría servir para conteo si un bloque = un elemento constructivo real."
        elif l == "00-MEDICION":
            ls["notes"] = "Layer de control. Contiene proyecciones de medidas reales extraíbles del measurement property."
        else:
            ls["notes"] = "Información gráfica dispersa mayormente visual, debe pasar por Vision AI para semántica."
            
        layer_summary_out[l] = {
            "object_count": ls["object_count"],
            "types": dict(ls["types"]),
            "discipline": ls["discipline"],
            "budget_relevant": ls["budget_relevant"],
            "notes": ls["notes"]
        }
        
        # Mapping Discipline Summary
        disc_str = str(ls.get("discipline", "Misceláneos"))
        disc_sum = discipline_summary_out[disc_str]
        disc_sum["layers"].add(l)
        
        if ls["discipline"] == "Hormigón Armado":
            disc_sum["what_json_gives"] = "Áreas de sección vía Hatches en columnas o zapatas."
            disc_sum["what_needs_vision"] = "Ubicación 3D, alturas de piso a piso, vigas, longitudes de colado."
        elif ls["discipline"] == "Muros y Divisiones":
            disc_sum["what_json_gives"] = "Solo miles de líneas paralelas que componen el dibujo del muro."
            disc_sum["what_needs_vision"] = "Largo constructivo real (metros lineales de muro) e identificar tipo de block."
        elif ls["discipline"] in ["Puertas", "Ventanas", "Aparatos Sanitarios"]:
            disc_sum["what_json_gives"] = "Algunos Textos u ocasionalmente Block References útiles."
            disc_sum["what_needs_vision"] = "Conteo certero para evitar sumar líneas de símbolo en vez de elementos."
        else:
            if not disc_sum["what_json_gives"]:
                disc_sum["what_json_gives"] = "Anotaciones de texto y fragmentos CAD."
                disc_sum["what_needs_vision"] = "Identificación en plano de planta (Visual Analysis)."

    # Convert sets to lists para que sea serializable
    final_discipline_summary = {}
    for disc_k, disc_v in discipline_summary_out.items():
        final_discipline_summary[disc_k] = {
            "layers": list(disc_v["layers"]),
            "what_json_gives": str(disc_v.get("what_json_gives", "")),
            "what_needs_vision": str(disc_v.get("what_needs_vision", ""))
        }
        
    return {
        "project": os.path.basename(json_path),
        "total_objects": len(collection),
        "layer_summary": layer_summary_out,
        "usable_data": {
            "hatches_with_area": usable_data_hatches,
            "texts": usable_data_texts,
            "dimensions": usable_data_dims,
            "block_references": usable_data_blocks
        },
        "discipline_summary": final_discipline_summary,
        "gaps_for_vision_ai": [
            "Conteo real de puertas (JSON solo tiene líneas del símbolo)",
            "Dimensiones de muros (largo real, no segmentos)",
            "Alturas de entrepiso",
            "Especificaciones de materiales no anotadas en texto"
        ]
    }

if __name__ == "__main__":
    import sys
    # Prueba del script con el JSON que tenemos en la raíz del proyecto
    json_file = "../resultados_model_derivative.json" if os.path.exists("../resultados_model_derivative.json") else "resultados_model_derivative.json"
    if os.path.exists(json_file):
        print(f"Analizando {json_file}...")
        res = process_autodesk_json(json_file)
        
        out_file = "resumen_procesado.json"
        with open(out_file, "w", encoding="utf-8") as out:
            json.dump(res, out, indent=2, ensure_ascii=False)
            
        print(f"✅ Análisis completado. Se procesaron {res['total_objects']} objetos.")
        print(f"Resultados guardados en: {out_file}")
    else:
        print(f"❌ Error: No se encontró el archivo {json_file}")
