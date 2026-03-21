"""
Módulo de lectura y análisis de archivos DXF.
Usa ezdxf para extraer capas, entidades, layouts, y metadatos.
"""

import ezdxf
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace, Paperspace
from pathlib import Path
from typing import Optional

from .models import (
    CADFile, FileFormat, LayerInfo, EntityInfo, LayoutInfo,
    BoundingBox, UnitSystem,
)
from .config import classify_layer, INSUNITS_MAP


def parse_dxf(file_path: Path) -> CADFile:
    """
    Lee y analiza un archivo DXF completo.
    
    Args:
        file_path: Ruta al archivo DXF
    
    Returns:
        CADFile con todos los datos extraídos
    """
    print(f"[PARSER] Leyendo archivo: {file_path.name}")
    
    doc = ezdxf.readfile(str(file_path))
    
    cad_file = CADFile(
        path=file_path,
        format=FileFormat.DXF,
        file_size=file_path.stat().st_size,
    )
    
    # Extraer metadatos del header
    _extract_header_info(doc, cad_file)
    
    # Extraer capas
    cad_file.layers = _extract_layers(doc)
    
    # Extraer layouts
    cad_file.layouts = _extract_layouts(doc)
    
    # Extraer entidades (del modelspace)
    cad_file.entities = _extract_entities(doc.modelspace())
    
    # Clasificar disciplinas encontradas
    disciplines = set()
    for layer in cad_file.layers:
        layer.discipline = classify_layer(layer.name)
        if layer.discipline.name != "UNKNOWN":
            disciplines.add(layer.discipline)
    cad_file.disciplines_found = list(disciplines)
    
    # Actualizar conteo de entidades por capa
    entity_counts: dict[str, int] = {}
    for ent in cad_file.entities:
        entity_counts[ent.layer] = entity_counts.get(ent.layer, 0) + 1
    for layer in cad_file.layers:
        layer.entity_count = entity_counts.get(layer.name, 0)
    
    print(f"[PARSER] Completado: {len(cad_file.layers)} capas, "
          f"{len(cad_file.entities)} entidades, "
          f"{len(cad_file.layouts)} layouts")
    
    return cad_file


def parse_dxf_from_doc(doc: Drawing, source_path: Path) -> CADFile:
    """Parsea desde un documento ezdxf ya cargado."""
    cad_file = CADFile(path=source_path, format=FileFormat.DXF)
    _extract_header_info(doc, cad_file)
    cad_file.layers = _extract_layers(doc)
    cad_file.layouts = _extract_layouts(doc)
    cad_file.entities = _extract_entities(doc.modelspace())
    
    for layer in cad_file.layers:
        layer.discipline = classify_layer(layer.name)
    
    return cad_file


def _extract_header_info(doc: Drawing, cad_file: CADFile) -> None:
    """Extrae información del header del DXF."""
    cad_file.dxf_version = doc.dxfversion
    
    # Unidades de inserción ($INSUNITS)
    try:
        insunits = doc.header.get("$INSUNITS", 0)
        cad_file.units = INSUNITS_MAP.get(insunits, UnitSystem.UNITLESS)
    except Exception:
        cad_file.units = UnitSystem.UNITLESS
    
    # Sistema de medida ($MEASUREMENT): 0=imperial, 1=metric
    try:
        cad_file.measurement = doc.header.get("$MEASUREMENT", 0)
    except Exception:
        cad_file.measurement = 0


def _extract_layers(doc: Drawing) -> list[LayerInfo]:
    """Extrae información de todas las capas."""
    layers = []
    
    for layer in doc.layers:
        layer_info = LayerInfo(
            name=layer.dxf.name,
            color=layer.dxf.color if hasattr(layer.dxf, 'color') else 7,
            linetype=layer.dxf.linetype if hasattr(layer.dxf, 'linetype') else "Continuous",
            is_on=layer.is_on(),
            is_frozen=layer.is_frozen(),
            is_locked=layer.is_locked(),
        )
        layers.append(layer_info)
    
    return layers


def _extract_layouts(doc: Drawing) -> list[LayoutInfo]:
    """Extrae información de todos los layouts (model space + paper spaces)."""
    layouts = []
    
    for layout in doc.layouts:
        layout_info = LayoutInfo(
            name=layout.name,
            is_model_space=(layout.name == "Model"),
            entity_count=len(list(layout)),
        )
        
        # Intentar obtener dimensiones del papel
        if not layout_info.is_model_space:
            try:
                layout_info.paper_width = layout.dxf.paper_width if hasattr(layout.dxf, 'paper_width') else 0.0
                layout_info.paper_height = layout.dxf.paper_height if hasattr(layout.dxf, 'paper_height') else 0.0
            except Exception:
                pass
        
        # Tab order
        try:
            layout_info.tab_order = layout.dxf.taborder if hasattr(layout.dxf, 'taborder') else 0
        except Exception:
            pass
        
        layouts.append(layout_info)
    
    # Ordenar por tab order
    layouts.sort(key=lambda l: (not l.is_model_space, l.tab_order))
    
    return layouts


def _extract_entities(msp: Modelspace) -> list[EntityInfo]:
    """Extrae información resumida de todas las entidades del modelo."""
    entities = []
    
    for entity in msp:
        entity_info = EntityInfo(
            dxf_type=entity.dxftype(),
            layer=entity.dxf.layer if hasattr(entity.dxf, 'layer') else "0",
            handle=entity.dxf.handle if hasattr(entity.dxf, 'handle') else "",
            color=entity.dxf.color if hasattr(entity.dxf, 'color') else 256,
        )
        
        # Intentar calcular bounding box
        try:
            bbox = _get_entity_bbox(entity)
            if bbox:
                entity_info.bbox = bbox
        except Exception:
            pass
        
        # Intentar obtener área para entidades cerradas
        try:
            if hasattr(entity, 'is_closed') and entity.is_closed:
                entity_info.is_closed = True
            if entity.dxftype() == "LWPOLYLINE" and hasattr(entity, 'is_closed'):
                entity_info.is_closed = entity.is_closed
            if entity.dxftype() == "CIRCLE":
                entity_info.is_closed = True
                import math
                entity_info.area = math.pi * entity.dxf.radius ** 2
            if entity.dxftype() == "HATCH":
                entity_info.is_closed = True
        except Exception:
            pass
        
        entities.append(entity_info)
    
    return entities


def _get_entity_bbox(entity) -> Optional[BoundingBox]:
    """Calcula el bounding box de una entidad DXF."""
    try:
        from ezdxf import bbox as ezdxf_bbox
        cache = ezdxf_bbox.Cache()
        box = ezdxf_bbox.extents([entity], cache=cache)
        if box.has_data:
            return BoundingBox(
                min_x=box.extmin[0],
                min_y=box.extmin[1],
                min_z=box.extmin[2] if len(box.extmin) > 2 else 0.0,
                max_x=box.extmax[0],
                max_y=box.extmax[1],
                max_z=box.extmax[2] if len(box.extmax) > 2 else 0.0,
            )
    except Exception:
        pass
    
    # Fallback para tipos comunes
    try:
        dxf_type = entity.dxftype()
        
        if dxf_type == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            return BoundingBox(
                min_x=min(start.x, end.x),
                min_y=min(start.y, end.y),
                min_z=min(start.z, end.z) if hasattr(start, 'z') else 0.0,
                max_x=max(start.x, end.x),
                max_y=max(start.y, end.y),
                max_z=max(start.z, end.z) if hasattr(start, 'z') else 0.0,
            )
        
        elif dxf_type == "CIRCLE":
            c = entity.dxf.center
            r = entity.dxf.radius
            return BoundingBox(
                min_x=c.x - r, min_y=c.y - r, min_z=c.z if hasattr(c, 'z') else 0.0,
                max_x=c.x + r, max_y=c.y + r, max_z=c.z if hasattr(c, 'z') else 0.0,
            )
        
        elif dxf_type == "POINT":
            loc = entity.dxf.location
            return BoundingBox(
                min_x=loc.x, min_y=loc.y, min_z=loc.z if hasattr(loc, 'z') else 0.0,
                max_x=loc.x, max_y=loc.y, max_z=loc.z if hasattr(loc, 'z') else 0.0,
            )
    except Exception:
        pass
    
    return None


def generate_parse_report(cad_file: CADFile) -> str:
    """Genera un reporte detallado del archivo parseado."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"REPORTE DE ANÁLISIS: {cad_file.filename}")
    lines.append("=" * 80)
    lines.append("")
    
    # Info general
    lines.append("INFORMACIÓN GENERAL")
    lines.append("-" * 40)
    lines.append(f"  Archivo:       {cad_file.path}")
    lines.append(f"  Formato:       {cad_file.format.value.upper()}")
    lines.append(f"  Versión DXF:   {cad_file.dxf_version}")
    lines.append(f"  Unidades:      {cad_file.units.name} (${cad_file.units.value})")
    lines.append(f"  Medición:      {'Métrico' if cad_file.measurement == 1 else 'Imperial'}")
    lines.append(f"  Total capas:   {cad_file.total_layers}")
    lines.append(f"  Total entidades: {cad_file.total_entities}")
    lines.append(f"  Total layouts: {len(cad_file.layouts)}")
    lines.append("")
    
    # Capas por disciplina
    lines.append("CAPAS POR DISCIPLINA")
    lines.append("-" * 40)
    
    by_discipline: dict[str, list[LayerInfo]] = {}
    for layer in cad_file.layers:
        key = f"{layer.discipline.value}"
        by_discipline.setdefault(key, []).append(layer)
    
    for disc, layers in sorted(by_discipline.items()):
        total_ents = sum(l.entity_count for l in layers)
        lines.append(f"\n  [{disc}] ({len(layers)} capas, {total_ents} entidades)")
        for layer in sorted(layers, key=lambda l: l.name):
            status = "ON " if layer.is_visible else "OFF"
            lines.append(f"    {status} | {layer.name:<30} | Color: {layer.color:>3} | "
                        f"Entidades: {layer.entity_count}")
    lines.append("")
    
    # Layouts
    lines.append("LAYOUTS")
    lines.append("-" * 40)
    for layout in cad_file.layouts:
        ltype = "MODEL" if layout.is_model_space else "PAPER"
        lines.append(f"  [{ltype}] {layout.name:<30} | {layout.entity_count} entidades")
    lines.append("")
    
    # Tipos de entidades
    lines.append("TIPOS DE ENTIDADES")
    lines.append("-" * 40)
    type_counts: dict[str, int] = {}
    for ent in cad_file.entities:
        type_counts[ent.dxf_type] = type_counts.get(ent.dxf_type, 0) + 1
    for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {etype:<25} {count:>6}")
    lines.append("")
    
    # Disciplinas encontradas
    lines.append("DISCIPLINAS ENCONTRADAS")
    lines.append("-" * 40)
    for disc in cad_file.disciplines_found:
        lines.append(f"  [{disc.name}] {disc.value}")
    lines.append("")
    
    lines.append("=" * 80)
    
    return "\n".join(lines)
