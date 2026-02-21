"""
Módulo de análisis: cálculo de áreas, detección de clashes,
y preparación para volumetría.
"""

import math
from pathlib import Path
from datetime import datetime
from typing import Optional
from collections import defaultdict

import ezdxf

from .models import (
    CADFile, EntityInfo, BoundingBox, LayerInfo,
    DisciplineCode, ClashResult, ClashSeverity,
    AreaResult, AnalysisSummary,
)
from .config import classify_layer


# ============================================================================
# CÁLCULO DE ÁREAS
# ============================================================================

def calculate_areas(file_path: Path) -> list[AreaResult]:
    """
    Calcula áreas de todas las entidades cerradas en un archivo DXF.
    
    Soporta:
    - LWPOLYLINE cerradas (polilíneas ligeras)
    - POLYLINE cerradas
    - CIRCLE
    - ELLIPSE
    - HATCH
    
    Returns:
        Lista de AreaResult con las áreas calculadas
    """
    print(f"\n[ÁREAS] Calculando áreas: {file_path.name}")
    
    doc = ezdxf.readfile(str(file_path))
    msp = doc.modelspace()
    
    results: list[AreaResult] = []
    
    for entity in msp:
        dxf_type = entity.dxftype()
        layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else "0"
        handle = entity.dxf.handle if hasattr(entity.dxf, 'handle') else ""
        discipline = classify_layer(layer)
        
        area = 0.0
        perimeter = 0.0
        description = ""
        
        try:
            if dxf_type == "LWPOLYLINE":
                if entity.is_closed:
                    area = _lwpolyline_area(entity)
                    perimeter = _lwpolyline_perimeter(entity)
                    description = f"Polilínea cerrada ({len(list(entity.get_points('xy')))} vértices)"
            
            elif dxf_type == "CIRCLE":
                r = entity.dxf.radius
                area = math.pi * r ** 2
                perimeter = 2 * math.pi * r
                description = f"Círculo (r={r:.2f})"
            
            elif dxf_type == "ELLIPSE":
                # Área de elipse: π * a * b
                # Donde a = semi major axis ratio, b = computed
                try:
                    major = entity.dxf.major_axis
                    a = math.sqrt(major.x**2 + major.y**2)
                    b = a * entity.dxf.ratio
                    area = math.pi * a * b
                    perimeter = math.pi * (3 * (a + b) - math.sqrt((3*a + b) * (a + 3*b)))
                    description = f"Elipse (a={a:.2f}, b={b:.2f})"
                except Exception:
                    pass
            
            elif dxf_type == "HATCH":
                try:
                    # ezdxf puede calcular el área de los paths del hatch
                    paths = entity.paths
                    for path in paths:
                        if hasattr(path, 'vertices'):
                            area += abs(_polygon_area(
                                [(v[0], v[1]) for v in path.vertices]
                            ))
                    description = f"Hatch ({len(paths)} paths)"
                except Exception:
                    pass
            
            elif dxf_type == "SOLID" or dxf_type == "3DFACE":
                try:
                    # Los SOLID/3DFACE tienen 3 o 4 vértices
                    points = []
                    for attr in ['vtx0', 'vtx1', 'vtx2', 'vtx3']:
                        if hasattr(entity.dxf, attr):
                            p = getattr(entity.dxf, attr)
                            points.append((p.x, p.y))
                    if len(points) >= 3:
                        area = abs(_polygon_area(points))
                        description = f"{dxf_type} ({len(points)} vértices)"
                except Exception:
                    pass
        
        except Exception as e:
            print(f"  [WARN] Error calculando área de {dxf_type} en capa {layer}: {e}")
            continue
        
        if area > 0:
            results.append(AreaResult(
                entity_handle=handle,
                entity_type=dxf_type,
                layer=layer,
                discipline=discipline,
                area=area,
                perimeter=perimeter,
                description=description,
            ))
    
    print(f"[ÁREAS] {len(results)} entidades con área calculada.")
    return results


def _lwpolyline_area(entity) -> float:
    """Calcula el área de una LWPOLYLINE cerrada usando la fórmula del Shoelace."""
    points = list(entity.get_points('xy'))
    return abs(_polygon_area(points))


def _lwpolyline_perimeter(entity) -> float:
    """Calcula el perímetro de una LWPOLYLINE."""
    points = list(entity.get_points('xy'))
    perimeter = 0.0
    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        perimeter += math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    return perimeter


def _polygon_area(points: list[tuple[float, float]]) -> float:
    """Calcula el área de un polígono usando la fórmula del Shoelace."""
    n = len(points)
    if n < 3:
        return 0.0
    
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    
    return abs(area) / 2.0


# ============================================================================
# CLASH DETECTION (BOUNDING BOX BASED)
# ============================================================================

def detect_clashes(
    file_path: Path,
    tolerance: float = 0.0,
    min_severity: ClashSeverity = ClashSeverity.INFO,
) -> list[ClashResult]:
    """
    Detecta clashes entre entidades de diferentes disciplinas.
    
    Método: Intersección de bounding boxes (2D/3D).
    Para clash detection más preciso se recomienda usar IFC + ifcopenshell.
    
    Args:
        file_path: Ruta al archivo DXF
        tolerance: Distancia de tolerancia para clashes de proximidad
        min_severity: Severidad mínima para reportar
    
    Returns:
        Lista de ClashResult con los clashes encontrados
    """
    print(f"\n[CLASHES] Analizando: {file_path.name}")
    
    doc = ezdxf.readfile(str(file_path))
    msp = doc.modelspace()
    
    # Recopilar entidades con bounding box, agrupadas por disciplina
    entities_by_disc: dict[DisciplineCode, list[dict]] = defaultdict(list)
    
    for entity in msp:
        layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else "0"
        discipline = classify_layer(layer)
        
        bbox = _get_entity_bbox_quick(entity)
        if bbox is None:
            continue
        
        entities_by_disc[discipline].append({
            "handle": entity.dxf.handle if hasattr(entity.dxf, 'handle') else "",
            "type": entity.dxftype(),
            "layer": layer,
            "discipline": discipline,
            "bbox": bbox,
        })
    
    disciplines = list(entities_by_disc.keys())
    print(f"[CLASHES] Disciplinas con geometría: "
          f"{', '.join(d.name for d in disciplines)}")
    
    # Comparar entidades entre pares de disciplinas
    clashes: list[ClashResult] = []
    
    for i in range(len(disciplines)):
        for j in range(i + 1, len(disciplines)):
            disc_a = disciplines[i]
            disc_b = disciplines[j]
            
            entities_a = entities_by_disc[disc_a]
            entities_b = entities_by_disc[disc_b]
            
            for ent_a in entities_a:
                for ent_b in entities_b:
                    bbox_a: BoundingBox = ent_a["bbox"]
                    bbox_b: BoundingBox = ent_b["bbox"]
                    
                    # Expandir bboxes por tolerancia
                    if tolerance > 0:
                        bbox_a_expanded = BoundingBox(
                            bbox_a.min_x - tolerance, bbox_a.min_y - tolerance,
                            bbox_a.min_z - tolerance, bbox_a.max_x + tolerance,
                            bbox_a.max_y + tolerance, bbox_a.max_z + tolerance,
                        )
                    else:
                        bbox_a_expanded = bbox_a
                    
                    if bbox_a_expanded.intersects(bbox_b):
                        # Calcular volumen de intersección
                        int_vol = bbox_a.intersection_volume(bbox_b)
                        
                        # Determinar severidad
                        severity = _classify_clash_severity(
                            bbox_a, bbox_b, int_vol, tolerance
                        )
                        
                        if _severity_value(severity) < _severity_value(min_severity):
                            continue
                        
                        # Punto de intersección (centro de la zona de overlap)
                        ix = (max(bbox_a.min_x, bbox_b.min_x) +
                              min(bbox_a.max_x, bbox_b.max_x)) / 2
                        iy = (max(bbox_a.min_y, bbox_b.min_y) +
                              min(bbox_a.max_y, bbox_b.max_y)) / 2
                        iz = (max(bbox_a.min_z, bbox_b.min_z) +
                              min(bbox_a.max_z, bbox_b.max_z)) / 2
                        
                        clash = ClashResult(
                            entity_a_handle=ent_a["handle"],
                            entity_a_layer=ent_a["layer"],
                            entity_a_type=ent_a["type"],
                            discipline_a=disc_a,
                            entity_b_handle=ent_b["handle"],
                            entity_b_layer=ent_b["layer"],
                            entity_b_type=ent_b["type"],
                            discipline_b=disc_b,
                            severity=severity,
                            intersection_point=(ix, iy, iz),
                            intersection_volume=int_vol,
                            description=(
                                f"{disc_a.value} ({ent_a['layer']}) "
                                f"<-> {disc_b.value} ({ent_b['layer']})"
                            ),
                        )
                        clashes.append(clash)
    
    # Ordenar por severidad (más críticos primero)
    clashes.sort(key=lambda c: _severity_value(c.severity), reverse=True)
    
    print(f"[CLASHES] {len(clashes)} clashes detectados.")
    if clashes:
        critical = sum(1 for c in clashes if c.severity == ClashSeverity.CRITICAL)
        major = sum(1 for c in clashes if c.severity == ClashSeverity.MAJOR)
        minor = sum(1 for c in clashes if c.severity == ClashSeverity.MINOR)
        info = sum(1 for c in clashes if c.severity == ClashSeverity.INFO)
        print(f"  CRITICO: {critical} | MAYOR: {major} | "
              f"MENOR: {minor} | INFO: {info}")
    
    return clashes


def _get_entity_bbox_quick(entity) -> Optional[BoundingBox]:
    """Obtiene bounding box de una entidad de forma rápida."""
    try:
        dxf_type = entity.dxftype()
        
        if dxf_type == "LINE":
            s = entity.dxf.start
            e = entity.dxf.end
            return BoundingBox(
                min(s.x, e.x), min(s.y, e.y),
                min(getattr(s, 'z', 0), getattr(e, 'z', 0)),
                max(s.x, e.x), max(s.y, e.y),
                max(getattr(s, 'z', 0), getattr(e, 'z', 0)),
            )
        
        elif dxf_type == "CIRCLE":
            c = entity.dxf.center
            r = entity.dxf.radius
            return BoundingBox(
                c.x - r, c.y - r, getattr(c, 'z', 0),
                c.x + r, c.y + r, getattr(c, 'z', 0),
            )
        
        elif dxf_type == "LWPOLYLINE":
            points = list(entity.get_points('xy'))
            if points:
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                return BoundingBox(
                    min(xs), min(ys), 0, max(xs), max(ys), 0
                )
        
        elif dxf_type == "INSERT":
            p = entity.dxf.insert
            return BoundingBox(
                p.x, p.y, getattr(p, 'z', 0),
                p.x, p.y, getattr(p, 'z', 0),
            )
        
        elif dxf_type == "ARC":
            c = entity.dxf.center
            r = entity.dxf.radius
            return BoundingBox(
                c.x - r, c.y - r, getattr(c, 'z', 0),
                c.x + r, c.y + r, getattr(c, 'z', 0),
            )
    except Exception:
        pass
    
    return None


def _classify_clash_severity(
    bbox_a: BoundingBox,
    bbox_b: BoundingBox,
    intersection_volume: float,
    tolerance: float
) -> ClashSeverity:
    """Clasifica la severidad de un clash basándose en el volumen de intersección."""
    # Para 2D, usamos área de intersección
    area_a = bbox_a.area_2d
    area_b = bbox_b.area_2d
    min_area = min(area_a, area_b) if min(area_a, area_b) > 0 else 1.0
    
    # Calcular overlap relativo
    overlap_x = max(0, min(bbox_a.max_x, bbox_b.max_x) - max(bbox_a.min_x, bbox_b.min_x))
    overlap_y = max(0, min(bbox_a.max_y, bbox_b.max_y) - max(bbox_a.min_y, bbox_b.min_y))
    overlap_area = overlap_x * overlap_y
    overlap_ratio = overlap_area / min_area if min_area > 0 else 0
    
    if overlap_ratio > 0.5:
        return ClashSeverity.CRITICAL
    elif overlap_ratio > 0.2:
        return ClashSeverity.MAJOR
    elif overlap_ratio > 0.05:
        return ClashSeverity.MINOR
    else:
        return ClashSeverity.INFO


def _severity_value(severity: ClashSeverity) -> int:
    """Valor numérico de severidad para ordenamiento."""
    return {
        ClashSeverity.CRITICAL: 4,
        ClashSeverity.MAJOR: 3,
        ClashSeverity.MINOR: 2,
        ClashSeverity.INFO: 1,
    }.get(severity, 0)


# ============================================================================
# REPORTE DE ANÁLISIS
# ============================================================================

def generate_analysis_report(
    file_path: Path,
    areas: list[AreaResult],
    clashes: list[ClashResult],
) -> str:
    """Genera reporte completo de análisis en formato texto."""
    lines = []
    lines.append("=" * 80)
    lines.append("REPORTE DE ANÁLISIS CAD")
    lines.append(f"Archivo: {file_path.name}")
    lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    
    # ── SECCIÓN DE ÁREAS ──
    lines.append("")
    lines.append("+" + "="*62 + "+")
    lines.append("|" + "              CALCULO DE AREAS                            " + "|")
    lines.append("+" + "="*62 + "+")
    lines.append("")
    
    if areas:
        # Resumen por disciplina
        area_by_disc: dict[str, float] = defaultdict(float)
        count_by_disc: dict[str, int] = defaultdict(int)
        for a in areas:
            key = f"[{a.discipline.name}] {a.discipline.value}"
            area_by_disc[key] += a.area
            count_by_disc[key] += 1
        
        lines.append("  Resumen por disciplina:")
        lines.append(f"  {'Disciplina':<35} {'Entidades':>10} {'Área Total':>15}")
        lines.append(f"  {'-'*35} {'-'*10} {'-'*15}")
        for disc, total_area in sorted(area_by_disc.items()):
            count = count_by_disc[disc]
            lines.append(f"  {disc:<35} {count:>10} {total_area:>15.2f}")
        
        total = sum(a.area for a in areas)
        lines.append(f"  {'':─<35} {'':─>10} {'':─>15}")
        lines.append(f"  {'TOTAL':<35} {len(areas):>10} {total:>15.2f}")
        lines.append("")
        
        # Detalle por entidad (top 50 más grandes)
        lines.append("  Detalle (entidades más grandes, top 50):")
        lines.append(f"  {'Handle':<12} {'Tipo':<15} {'Capa':<25} {'Área':>12} {'Perímetro':>12}")
        lines.append(f"  {'-'*12} {'-'*15} {'-'*25} {'-'*12} {'-'*12}")
        
        sorted_areas = sorted(areas, key=lambda a: a.area, reverse=True)[:50]
        for a in sorted_areas:
            lines.append(
                f"  {a.entity_handle:<12} {a.entity_type:<15} "
                f"{a.layer:<25} {a.area:>12.2f} {a.perimeter:>12.2f}"
            )
    else:
        lines.append("  No se encontraron entidades con área calculable.")
    
    # ── SECCIÓN DE CLASHES ──
    lines.append("")
    lines.append("+" + "="*62 + "+")
    lines.append("|" + "              DETECCION DE CLASHES                         " + "|")
    lines.append("+" + "="*62 + "+")
    lines.append("")
    
    if clashes:
        # Resumen de severidades
        by_severity: dict[str, int] = defaultdict(int)
        for c in clashes:
            by_severity[c.severity.value] += 1
        
        lines.append("  Resumen de severidad:")
        for sev, count in sorted(by_severity.items()):
            bar = "#" * min(count, 50)
            lines.append(f"    {sev:<15} {count:>5} {bar}")
        lines.append("")
        
        # Resumen por par de disciplinas
        by_pair: dict[str, int] = defaultdict(int)
        for c in clashes:
            pair = f"{c.discipline_a.name} <-> {c.discipline_b.name}"
            by_pair[pair] += 1
        
        lines.append("  Clashes por par de disciplinas:")
        for pair, count in sorted(by_pair.items(), key=lambda x: -x[1]):
            lines.append(f"    {pair:<30} {count:>5} clashes")
        lines.append("")
        
        # Detalle de clashes (top 100)
        lines.append("  Detalle (top 100 por severidad):")
        lines.append(f"  {'#':>4} {'Severidad':<12} {'Disc.A':<8} {'Capa A':<20} "
                     f"{'Disc.B':<8} {'Capa B':<20} {'Coordenada'}")
        lines.append(f"  {'-'*4} {'-'*12} {'-'*8} {'-'*20} "
                     f"{'-'*8} {'-'*20} {'-'*30}")
        
        for idx, c in enumerate(clashes[:100], 1):
            coord = f"({c.intersection_point[0]:.1f}, {c.intersection_point[1]:.1f}, {c.intersection_point[2]:.1f})"
            lines.append(
                f"  {idx:>4} {c.severity.value:<12} "
                f"{c.discipline_a.name:<8} {c.entity_a_layer:<20} "
                f"{c.discipline_b.name:<8} {c.entity_b_layer:<20} "
                f"{coord}"
            )
    else:
        lines.append("  No se detectaron clashes entre disciplinas.")
    
    lines.append("")
    lines.append("=" * 80)
    lines.append("FIN DEL REPORTE")
    lines.append("=" * 80)
    
    return "\n".join(lines)


# ============================================================================
# FUNCIONES PUENTE PARA DATOS EN MEMORIA (DWG COM PATH)
# ============================================================================

def _calculate_areas_from_entities(cad_file: CADFile) -> list[AreaResult]:
    """
    Calcula areas usando datos ya extraidos del COM.
    Las entidades del COM ya tienen .area y .length prellenados.
    """
    results = []
    for ent in cad_file.entities:
        if getattr(ent, 'area', None) and ent.area > 0:
            results.append(AreaResult(
                entity_handle=ent.handle,
                entity_type=ent.dxf_type,
                layer=ent.layer,
                discipline=classify_layer(ent.layer),
                area=ent.area,
                perimeter=getattr(ent, 'length', 0.0) or 0.0,
                description=f"{ent.dxf_type} en {ent.layer}",
            ))
    return results


def _detect_clashes_from_entities(cad_file: CADFile) -> list[ClashResult]:
    """
    Detecta clashes usando datos ya extraidos del COM.
    Las entidades del COM ya tienen .bbox prellenado.
    """
    entities_by_disc: dict[DisciplineCode, list] = defaultdict(list)
    
    for ent in cad_file.entities:
        if ent.bbox is None:
            continue
        disc = classify_layer(ent.layer)
        entities_by_disc[disc].append({
            "handle": ent.handle,
            "type": ent.dxf_type,
            "layer": ent.layer,
            "discipline": disc,
            "bbox": ent.bbox,
        })
    
    disciplines = list(entities_by_disc.keys())
    clashes: list[ClashResult] = []
    
    for i in range(len(disciplines)):
        for j in range(i + 1, len(disciplines)):
            disc_a = disciplines[i]
            disc_b = disciplines[j]
            
            for ent_a in entities_by_disc[disc_a]:
                for ent_b in entities_by_disc[disc_b]:
                    bbox_a = ent_a["bbox"]
                    bbox_b = ent_b["bbox"]
                    
                    if bbox_a.intersects(bbox_b):
                        int_vol = bbox_a.intersection_volume(bbox_b)
                        severity = _classify_clash_severity(bbox_a, bbox_b, int_vol, 0.0)
                        
                        ix = (max(bbox_a.min_x, bbox_b.min_x) +
                              min(bbox_a.max_x, bbox_b.max_x)) / 2
                        iy = (max(bbox_a.min_y, bbox_b.min_y) +
                              min(bbox_a.max_y, bbox_b.max_y)) / 2
                        iz = (max(bbox_a.min_z, bbox_b.min_z) +
                              min(bbox_a.max_z, bbox_b.max_z)) / 2
                        
                        clashes.append(ClashResult(
                            entity_a_handle=ent_a["handle"],
                            entity_a_layer=ent_a["layer"],
                            entity_a_type=ent_a["type"],
                            discipline_a=disc_a,
                            entity_b_handle=ent_b["handle"],
                            entity_b_layer=ent_b["layer"],
                            entity_b_type=ent_b["type"],
                            discipline_b=disc_b,
                            severity=severity,
                            intersection_point=(ix, iy, iz),
                            intersection_volume=int_vol,
                            description=(
                                f"{disc_a.value} ({ent_a['layer']}) "
                                f"<-> {disc_b.value} ({ent_b['layer']})"
                            ),
                        ))
    
    clashes.sort(key=lambda c: _severity_value(c.severity), reverse=True)
    return clashes


# Alias for the DWG COM pipeline
generate_analysis_report_from_data = generate_analysis_report
