"""
Módulo de separación de planos (layouts).
Toma un archivo DXF con múltiples layouts (paper spaces)
y genera un archivo separado por cada uno.
"""

import ezdxf
from ezdxf.document import Drawing
from pathlib import Path
from datetime import datetime

from .config import get_output_dir


def list_layouts(file_path: Path) -> list[dict]:
    """
    Lista todos los layouts de un archivo DXF.
    
    Returns:
        Lista de diccionarios con info de cada layout
    """
    doc = ezdxf.readfile(str(file_path))
    
    layouts_info = []
    for layout in doc.layouts:
        entity_count = len(list(layout))
        info = {
            "name": layout.name,
            "is_model": layout.name == "Model",
            "entity_count": entity_count,
        }
        
        if not info["is_model"]:
            try:
                info["paper_width"] = layout.dxf.paper_width if hasattr(layout.dxf, 'paper_width') else 0
                info["paper_height"] = layout.dxf.paper_height if hasattr(layout.dxf, 'paper_height') else 0
            except Exception:
                info["paper_width"] = 0
                info["paper_height"] = 0
        
        layouts_info.append(info)
    
    return layouts_info


def split_layouts(
    file_path: Path,
    output_dir: Path | None = None,
    include_model_space: bool = True,
    skip_empty: bool = True,
) -> list[Path]:
    """
    Separa cada layout (paper space) de un archivo DXF en un archivo individual.
    
    Proceso:
    1. Enumera todos los layouts del archivo
    2. Para cada layout, crea un nuevo DXF
    3. Copia las capas, estilos y entidades necesarios
    4. El Model Space va a un archivo separado si tiene geometría
    
    Args:
        file_path: Ruta al archivo DXF original
        output_dir: Directorio de salida
        include_model_space: Si incluir el modelspace como archivo separado
        skip_empty: Si omitir layouts sin entidades
    
    Returns:
        Lista de rutas a los archivos generados
    """
    print(f"\n[SPLITTER] Procesando: {file_path.name}")
    
    doc = ezdxf.readfile(str(file_path))
    
    if output_dir is None:
        output_dir = get_output_dir(file_path, "split")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generated_files: list[Path] = []
    layout_names = list(doc.layouts.names())
    
    print(f"[SPLITTER] Layouts encontrados: {len(layout_names)} -> {layout_names}")
    
    for layout_name in layout_names:
        layout = doc.layouts.get(layout_name)
        entity_count = len(list(layout))
        
        is_model = (layout_name == "Model")
        
        if is_model and not include_model_space:
            print(f"  [SKIP] Model Space (excluido)")
            continue
        
        if skip_empty and entity_count == 0:
            print(f"  [SKIP] '{layout_name}' (vacío)")
            continue
        
        # Crear nuevo documento
        new_doc = ezdxf.new(dxfversion=doc.dxfversion)
        
        # Copiar variables de header
        _copy_header(doc, new_doc)
        
        # Copiar todas las capas (necesarias para las entidades)
        _copy_layers(doc, new_doc)
        
        # Copiar linetypes
        _copy_linetypes(doc, new_doc)
        
        # Copiar text styles
        _copy_text_styles(doc, new_doc)
        
        if is_model:
            # Copiar entidades al modelspace del nuevo documento
            new_msp = new_doc.modelspace()
            copied = _copy_entities(layout, new_msp)
            suffix = "Model"
        else:
            # Para paper space: copiar entidades al modelspace del nuevo doc
            # (tratamos el contenido del layout como el modelo principal)
            new_msp = new_doc.modelspace()
            copied = _copy_entities(layout, new_msp)
            # Sanitizar nombre del layout para usar como nombre de archivo
            suffix = _sanitize_filename(layout_name)
        
        # Nombre del archivo de salida
        stem = file_path.stem
        output_path = output_dir / f"{stem}_{suffix}.dxf"
        
        new_doc.saveas(str(output_path))
        generated_files.append(output_path)
        
        label = "MODEL" if is_model else "LAYOUT"
        print(f"  [OK] [{label}] '{layout_name}': {copied} entidades -> {output_path.name}")
    
    print(f"[SPLITTER] Generados {len(generated_files)} archivos.")
    
    return generated_files


def _copy_header(source: Drawing, target: Drawing) -> None:
    """Copia variables de header relevantes."""
    vars_to_copy = [
        "$INSUNITS", "$MEASUREMENT", "$LUNITS", "$LUPREC",
        "$AUNITS", "$AUPREC", "$DIMSCALE", "$LTSCALE",
        "$TEXTSIZE", "$DIMTXT",
    ]
    for var in vars_to_copy:
        try:
            val = source.header.get(var)
            if val is not None:
                target.header[var] = val
        except Exception:
            pass


def _copy_layers(source: Drawing, target: Drawing) -> None:
    """Copia todas las capas del documento fuente al destino."""
    for layer in source.layers:
        name = layer.dxf.name
        if name == "0":
            # Capa 0 siempre existe, solo actualizar propiedades
            target_layer = target.layers.get("0")
            target_layer.dxf.color = layer.dxf.color
            continue
        try:
            new_layer = target.layers.new(name=name)
            new_layer.dxf.color = layer.dxf.color
            if hasattr(layer.dxf, 'linetype'):
                new_layer.dxf.linetype = layer.dxf.linetype
        except ezdxf.DXFTableEntryError:
            pass  # Ya existe


def _copy_linetypes(source: Drawing, target: Drawing) -> None:
    """Copia linetypes del fuente al destino."""
    builtin = {"ByBlock", "ByLayer", "Continuous"}
    for lt in source.linetypes:
        if lt.dxf.name in builtin:
            continue
        try:
            target.linetypes.new(lt.dxf.name)
        except Exception:
            pass


def _copy_text_styles(source: Drawing, target: Drawing) -> None:
    """Copia text styles del fuente al destino."""
    for style in source.styles:
        name = style.dxf.name
        if name == "Standard":
            continue
        try:
            new_style = target.styles.new(name=name)
            if hasattr(style.dxf, 'font'):
                new_style.dxf.font = style.dxf.font
            if hasattr(style.dxf, 'height'):
                new_style.dxf.height = style.dxf.height
        except Exception:
            pass


def _copy_entities(source_layout, target_layout) -> int:
    """Copia entidades de un layout a otro. Retorna el conteo."""
    count = 0
    for entity in source_layout:
        try:
            target_layout.add_entity(entity.copy())
            count += 1
        except Exception:
            pass
    return count


def _sanitize_filename(name: str) -> str:
    """Sanitiza un nombre de layout para uso como nombre de archivo."""
    # Reemplazar caracteres no válidos
    invalid_chars = '<>:"/\\|?*'
    result = name
    for char in invalid_chars:
        result = result.replace(char, "_")
    return result.strip().rstrip(".")


def generate_split_report(
    file_path: Path,
    layouts: list[dict],
    generated_files: list[Path]
) -> str:
    """Genera reporte de separación de layouts."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"REPORTE DE SEPARACIÓN DE PLANOS")
    lines.append(f"Archivo fuente: {file_path.name}")
    lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    lines.append("")
    
    lines.append(f"Layouts encontrados: {len(layouts)}")
    lines.append("")
    
    for layout in layouts:
        ltype = "MODEL" if layout.get("is_model") else "PAPER"
        lines.append(f"  [{ltype}] {layout['name']:<30} | "
                     f"{layout['entity_count']} entidades")
    lines.append("")
    
    lines.append(f"Archivos generados: {len(generated_files)}")
    for f in generated_files:
        lines.append(f"  -> {f.name}")
    
    lines.append("")
    lines.append("=" * 80)
    return "\n".join(lines)
