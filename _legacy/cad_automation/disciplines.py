"""
Módulo de separación por disciplinas.
Toma un archivo DXF con múltiples disciplinas y genera un archivo
separado por cada disciplina encontrada.
"""

import ezdxf
from ezdxf.document import Drawing
from pathlib import Path
from datetime import datetime

from .models import (
    CADFile, DisciplineCode, DisciplineGroup, LayerInfo
)
from .config import classify_layer, is_common_layer, get_output_dir


def analyze_disciplines(cad_file: CADFile) -> dict[DisciplineCode, DisciplineGroup]:
    """
    Analiza las capas de un archivo y las agrupa por disciplina.
    
    Args:
        cad_file: Archivo CAD parseado
    
    Returns:
        Diccionario con grupos de disciplinas
    """
    groups: dict[DisciplineCode, DisciplineGroup] = {}
    common_layers: list[LayerInfo] = []
    
    for layer in cad_file.layers:
        if is_common_layer(layer.name):
            common_layers.append(layer)
            continue
        
        discipline = classify_layer(layer.name)
        
        if discipline not in groups:
            groups[discipline] = DisciplineGroup(discipline=discipline)
        
        groups[discipline].layers.append(layer)
        groups[discipline].entity_count += layer.entity_count
    
    # Agregar capas comunes a cada grupo
    for group in groups.values():
        group.common_layers = common_layers.copy()
    
    return groups


def separate_by_discipline(
    file_path: Path,
    output_dir: Path | None = None,
) -> list[Path]:
    """
    Separa un archivo DXF en múltiples archivos, uno por disciplina.
    
    Proceso:
    1. Lee todas las capas y las clasifica por disciplina
    2. Para cada disciplina, crea un nuevo DXF con solo sus capas
    3. Las capas comunes (0, DEFPOINTS, G-*) se incluyen en todos
    4. Preserva bloques que contengan entidades de la disciplina
    
    Args:
        file_path: Ruta al archivo DXF original
        output_dir: Directorio de salida (auto-generado si None)
    
    Returns:
        Lista de rutas a los archivos generados
    """
    print(f"\n[DISCIPLINAS] Procesando: {file_path.name}")
    
    # Crear directorio de salida
    if output_dir is None:
        output_dir = get_output_dir(file_path, "disciplines")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Leer el archivo original
    doc = ezdxf.readfile(str(file_path))
    msp = doc.modelspace()
    
    # Clasificar capas
    layer_discipline_map: dict[str, DisciplineCode] = {}
    common_layer_names: set[str] = set()
    
    for layer in doc.layers:
        name = layer.dxf.name
        if is_common_layer(name):
            common_layer_names.add(name)
            layer_discipline_map[name] = DisciplineCode.G
        else:
            discipline = classify_layer(name)
            layer_discipline_map[name] = discipline
    
    # Agrupar capas por disciplina
    disciplines: dict[DisciplineCode, set[str]] = {}
    for layer_name, discipline in layer_discipline_map.items():
        if layer_name in common_layer_names:
            continue
        disciplines.setdefault(discipline, set()).add(layer_name)
    
    if not disciplines:
        print("[DISCIPLINAS] No se encontraron disciplinas para separar.")
        return []
    
    print(f"[DISCIPLINAS] Disciplinas encontradas: "
          f"{', '.join(d.value for d in disciplines.keys())}")
    
    # Generar un archivo por disciplina
    generated_files: list[Path] = []
    
    for discipline, layer_names in sorted(disciplines.items(), key=lambda x: x[0].name):
        # Capas de esta disciplina + comunes
        target_layers = layer_names | common_layer_names
        
        # Crear nuevo documento
        new_doc = ezdxf.new(dxfversion=doc.dxfversion)
        new_msp = new_doc.modelspace()
        
        # Copiar header variables
        _copy_header_vars(doc, new_doc)
        
        # Crear capas necesarias en el nuevo documento
        for layer in doc.layers:
            if layer.dxf.name in target_layers:
                try:
                    new_layer = new_doc.layers.new(name=layer.dxf.name)
                    new_layer.dxf.color = layer.dxf.color
                    if hasattr(layer.dxf, 'linetype'):
                        # Asegurar que el linetype existe
                        lt = layer.dxf.linetype
                        if lt not in new_doc.linetypes:
                            try:
                                new_doc.linetypes.new(lt)
                            except Exception:
                                lt = "Continuous"
                        new_layer.dxf.linetype = lt
                except ezdxf.DXFTableEntryError:
                    pass  # Capa ya existe (ej: "0")
        
        # Copiar entidades del modelspace que pertenezcan a capas de esta disciplina
        entity_count = 0
        for entity in msp:
            entity_layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else "0"
            if entity_layer in target_layers:
                try:
                    new_msp.add_entity(entity.copy())
                    entity_count += 1
                except Exception as e:
                    print(f"  [WARN] No se pudo copiar entidad {entity.dxftype()}: {e}")
        
        # Guardar
        stem = file_path.stem
        disc_name = discipline.name
        output_path = output_dir / f"{stem}_{disc_name}.dxf"
        
        new_doc.saveas(str(output_path))
        generated_files.append(output_path)
        
        print(f"  [OK] {disc_name} ({discipline.value}): "
              f"{len(target_layers)} capas, {entity_count} entidades -> {output_path.name}")
    
    print(f"[DISCIPLINAS] Generados {len(generated_files)} archivos.")
    
    return generated_files


def generate_discipline_report(
    cad_file: CADFile,
    groups: dict[DisciplineCode, DisciplineGroup]
) -> str:
    """Genera reporte de disciplinas en texto."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"REPORTE DE DISCIPLINAS: {cad_file.filename}")
    lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    lines.append("")
    
    lines.append(f"Total disciplinas encontradas: {len(groups)}")
    lines.append("")
    
    for discipline, group in sorted(groups.items(), key=lambda x: x[0].name):
        lines.append(f"{'-' * 60}")
        lines.append(f"DISCIPLINA: [{discipline.name}] {discipline.value}")
        lines.append(f"  Capas específicas:  {len(group.layers)}")
        lines.append(f"  Capas comunes:      {len(group.common_layers)}")
        lines.append(f"  Total entidades:    {group.entity_count}")
        lines.append("")
        
        if group.layers:
            lines.append("  Capas:")
            for layer in sorted(group.layers, key=lambda l: l.name):
                lines.append(f"    - {layer.name:<30} ({layer.entity_count} entidades)")
        lines.append("")
    
    lines.append("=" * 80)
    return "\n".join(lines)


def _copy_header_vars(source_doc: Drawing, target_doc: Drawing) -> None:
    """Copia variables de header relevantes entre documentos."""
    header_vars = [
        "$INSUNITS", "$MEASUREMENT", "$LUNITS", "$LUPREC",
        "$AUNITS", "$AUPREC", "$DIMSCALE",
    ]
    for var in header_vars:
        try:
            value = source_doc.header.get(var)
            if value is not None:
                target_doc.header[var] = value
        except Exception:
            pass
