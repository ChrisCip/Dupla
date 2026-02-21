"""
Módulo de normalización de unidades.
Detecta las unidades del archivo DXF y escala la geometría
para que todo esté en la misma métrica (por defecto: milímetros).
"""

import ezdxf
from ezdxf.document import Drawing
from ezdxf.math import Vec3
from pathlib import Path

from .models import UnitSystem
from .config import (
    get_conversion_factor, INSUNITS_MAP, TARGET_UNIT,
    get_output_dir,
)


def detect_units(file_path: Path) -> tuple[UnitSystem, int]:
    """
    Detecta las unidades de un archivo DXF.
    
    Returns:
        Tupla de (UnitSystem, measurement_flag)
        measurement_flag: 0=imperial, 1=metric
    """
    doc = ezdxf.readfile(str(file_path))
    
    insunits = doc.header.get("$INSUNITS", 0)
    measurement = doc.header.get("$MEASUREMENT", 0)
    
    unit = INSUNITS_MAP.get(insunits, UnitSystem.UNITLESS)
    
    return unit, measurement


def normalize_units(
    file_path: Path,
    target_unit: UnitSystem = TARGET_UNIT,
    output_dir: Path | None = None,
) -> Path | None:
    """
    Normaliza las unidades de un archivo DXF al sistema target.
    
    Proceso:
    1. Detecta unidades actuales ($INSUNITS)
    2. Calcula factor de conversión
    3. Escala todas las entidades del modelspace
    4. Actualiza variables de header
    5. Guarda el archivo normalizado
    
    Args:
        file_path: Ruta al archivo DXF
        target_unit: Unidad objetivo (default: MILLIMETERS)
        output_dir: Directorio de salida
    
    Returns:
        Ruta al archivo normalizado, o None si ya estaba en la unidad correcta
    """
    print(f"\n[UNIDADES] Procesando: {file_path.name}")
    
    doc = ezdxf.readfile(str(file_path))
    
    # Detectar unidades actuales
    insunits = doc.header.get("$INSUNITS", 0)
    current_unit = INSUNITS_MAP.get(insunits, UnitSystem.UNITLESS)
    
    print(f"[UNIDADES] Unidad actual: {current_unit.name} (INSUNITS={insunits})")
    print(f"[UNIDADES] Unidad objetivo: {target_unit.name}")
    
    # Calcular factor de conversión
    factor = get_conversion_factor(current_unit, target_unit)
    
    if abs(factor - 1.0) < 1e-10:
        print(f"[UNIDADES] El archivo ya está en {target_unit.name}. Sin cambios.")
        return None
    
    print(f"[UNIDADES] Factor de conversión: {factor}")
    
    # Escalar todas las entidades del modelspace
    msp = doc.modelspace()
    scaled_count = _scale_entities(msp, factor)
    
    # Escalar entidades en paper spaces también
    for layout in doc.layouts:
        if layout.name != "Model":
            scaled_count += _scale_entities(layout, factor)
    
    # Actualizar header
    doc.header["$INSUNITS"] = target_unit.value
    if target_unit in (UnitSystem.MILLIMETERS, UnitSystem.CENTIMETERS,
                       UnitSystem.METERS, UnitSystem.KILOMETERS):
        doc.header["$MEASUREMENT"] = 1  # Metric
    else:
        doc.header["$MEASUREMENT"] = 0  # Imperial
    
    # Guardar
    if output_dir is None:
        output_dir = get_output_dir(file_path, "normalized")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / f"{file_path.stem}_normalized.dxf"
    doc.saveas(str(output_path))
    
    print(f"[UNIDADES] Escaladas {scaled_count} entidades. "
          f"Guardado: {output_path.name}")
    
    return output_path


def _scale_entities(layout, factor: float) -> int:
    """
    Escala todas las entidades de un layout por el factor dado.
    
    Usa la transformación nativa de ezdxf cuando está disponible,
    con fallbacks manuales para tipos específicos.
    
    Returns:
        Número de entidades escaladas
    """
    count = 0
    origin = Vec3(0, 0, 0)
    
    for entity in layout:
        try:
            dxf_type = entity.dxftype()
            
            # Intentar usar transform de ezdxf
            if hasattr(entity, 'transform'):
                from ezdxf.math import Matrix44
                m = Matrix44.scale(factor, factor, factor)
                entity.transform(m)
                count += 1
                continue
            
            # Fallbacks manuales para tipos comunes
            if dxf_type == "LINE":
                entity.dxf.start = _scale_point(entity.dxf.start, factor)
                entity.dxf.end = _scale_point(entity.dxf.end, factor)
                count += 1
            
            elif dxf_type == "CIRCLE":
                entity.dxf.center = _scale_point(entity.dxf.center, factor)
                entity.dxf.radius *= factor
                count += 1
            
            elif dxf_type == "ARC":
                entity.dxf.center = _scale_point(entity.dxf.center, factor)
                entity.dxf.radius *= factor
                count += 1
            
            elif dxf_type == "POINT":
                entity.dxf.location = _scale_point(entity.dxf.location, factor)
                count += 1
            
            elif dxf_type == "INSERT":
                entity.dxf.insert = _scale_point(entity.dxf.insert, factor)
                if hasattr(entity.dxf, 'xscale'):
                    entity.dxf.xscale *= factor
                if hasattr(entity.dxf, 'yscale'):
                    entity.dxf.yscale *= factor
                if hasattr(entity.dxf, 'zscale'):
                    entity.dxf.zscale *= factor
                count += 1
            
            elif dxf_type in ("TEXT", "MTEXT"):
                if hasattr(entity.dxf, 'insert'):
                    entity.dxf.insert = _scale_point(entity.dxf.insert, factor)
                if hasattr(entity.dxf, 'height'):
                    entity.dxf.height *= factor
                count += 1
            
            elif dxf_type == "DIMENSION":
                # Las dimensiones son complejas, intentar escalar puntos
                for attr in ['defpoint', 'defpoint2', 'defpoint3',
                             'defpoint4', 'defpoint5', 'text_midpoint']:
                    if hasattr(entity.dxf, attr):
                        setattr(entity.dxf, attr,
                                _scale_point(getattr(entity.dxf, attr), factor))
                count += 1
            
            else:
                # Para otros tipos, intentar con bounding box scaling
                # No hacer nada si no sabemos cómo escalar
                pass
                
        except Exception as e:
            print(f"  [WARN] Error escalando {entity.dxftype()}: {e}")
    
    return count


def _scale_point(point, factor: float):
    """Escala un punto (Vec3 o tuple) por un factor."""
    if isinstance(point, Vec3):
        return Vec3(point.x * factor, point.y * factor, point.z * factor)
    elif isinstance(point, (tuple, list)):
        return tuple(v * factor for v in point)
    return point


def generate_units_report(
    file_path: Path,
    original_unit: UnitSystem,
    target_unit: UnitSystem,
    factor: float,
    entity_count: int
) -> str:
    """Genera reporte de normalización de unidades."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"REPORTE DE NORMALIZACIÓN DE UNIDADES")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"  Archivo:         {file_path.name}")
    lines.append(f"  Unidad original: {original_unit.name} ({original_unit.value})")
    lines.append(f"  Unidad destino:  {target_unit.name} ({target_unit.value})")
    lines.append(f"  Factor:          {factor}")
    lines.append(f"  Entidades:       {entity_count} escaladas")
    lines.append("")
    lines.append(f"  Ejemplo: 1.0 {original_unit.name} = {factor} {target_unit.name}")
    lines.append("")
    lines.append("=" * 80)
    return "\n".join(lines)
