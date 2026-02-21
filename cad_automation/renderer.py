"""
Renderizador DWG -> PDF usando AutoCAD COM.

Usa el plotter "DWG To PDF.pc3" integrado en AutoCAD/Civil 3D
para exportar cada layout a PDF con calidad vectorial.
"""

import time
from pathlib import Path
from typing import Optional

try:
    import win32com.client
    from win32com.client import GetActiveObject
    HAS_COM = True
except ImportError:
    HAS_COM = False


def render_layouts_to_pdf(
    output_dir: Optional[Path] = None,
    layouts: Optional[list[str]] = None,
) -> list[Path]:
    """
    Exporta cada layout del documento activo en Civil 3D a PDF.
    
    Args:
        output_dir: Directorio de salida (default: junto al DWG)
        layouts: Lista de nombres de layouts a exportar (default: todos)
    
    Returns:
        Lista de PDFs generados
    """
    if not HAS_COM:
        raise ImportError("win32com no disponible")
    
    acad = GetActiveObject("AutoCAD.Application")
    doc = acad.ActiveDocument
    
    if output_dir is None:
        output_dir = Path(doc.FullName).parent / "pdf_output"
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    dwg_name = Path(doc.Name).stem
    generated = []
    
    print(f"[RENDER] Exportando layouts a PDF...")
    print(f"[RENDER] Documento: {doc.Name}")
    print(f"[RENDER] Salida: {output_dir}")
    
    # Obtener layouts disponibles
    available_layouts = []
    for i in range(doc.Layouts.Count):
        layout = doc.Layouts.Item(i)
        if layouts is None or layout.Name in layouts:
            available_layouts.append(layout.Name)
    
    for layout_name in available_layouts:
        try:
            layout = doc.Layouts(layout_name)
            
            # Configurar layout activo
            doc.ActiveLayout = layout
            time.sleep(0.5)
            
            # Nombre del PDF
            safe_name = layout_name.replace("/", "_").replace("\\", "_")
            pdf_path = output_dir / f"{dwg_name}_{safe_name}.pdf"
            
            # Exportar usando Plot
            plot = doc.Plot
            
            # Configurar plotter PDF
            layout.ConfigName = "DWG To PDF.pc3"
            
            # Plot a archivo
            plot.PlotToFile(str(pdf_path))
            
            generated.append(pdf_path)
            print(f"  [OK] {layout_name} -> {pdf_path.name}")
            
        except Exception as e:
            print(f"  [ERROR] {layout_name}: {e}")
            # Fallback: intentar Export method
            try:
                pdf_path = output_dir / f"{dwg_name}_{safe_name}.pdf"
                doc.Export(str(pdf_path), "PDF", layout_name)
                generated.append(pdf_path)
                print(f"  [OK] {layout_name} -> {pdf_path.name} (via Export)")
            except Exception as e2:
                print(f"  [FAIL] {layout_name}: {e2}")
    
    print(f"[RENDER] {len(generated)} PDFs generados")
    return generated


def render_by_discipline(
    output_dir: Optional[Path] = None,
) -> list[Path]:
    """
    Renderiza vistas separadas por disciplina.
    Apaga todas las capas excepto las de una disciplina, exporta, repite.
    """
    from .config import classify_layer, is_common_layer
    from .models import DisciplineCode
    
    acad = GetActiveObject("AutoCAD.Application")
    doc = acad.ActiveDocument
    
    if output_dir is None:
        output_dir = Path(doc.FullName).parent / "pdf_disciplinas"
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    dwg_name = Path(doc.Name).stem
    
    # Guardar estado original de las capas
    original_states = {}
    layer_disciplines = {}
    
    for i in range(doc.Layers.Count):
        layer = doc.Layers.Item(i)
        original_states[layer.Name] = layer.LayerOn
        layer_disciplines[layer.Name] = classify_layer(layer.Name)
    
    # Identificar disciplinas unicas
    disciplines = set(layer_disciplines.values())
    disciplines.discard(DisciplineCode.UNKNOWN)
    disciplines.discard(DisciplineCode.G)  # General siempre visible
    
    generated = []
    
    print(f"[RENDER-DISC] Renderizando por disciplina...")
    
    for disc in sorted(disciplines, key=lambda d: d.name):
        try:
            # Apagar todas, prender solo esta disciplina + comunes
            for i in range(doc.Layers.Count):
                layer = doc.Layers.Item(i)
                layer_disc = layer_disciplines[layer.Name]
                should_be_on = (
                    layer_disc == disc or
                    layer_disc == DisciplineCode.G or
                    is_common_layer(layer.Name)
                )
                try:
                    layer.LayerOn = should_be_on
                except Exception:
                    pass
            
            time.sleep(0.5)
            
            # Exportar el Model space
            doc.ActiveLayout = doc.Layouts("Model")
            time.sleep(0.3)
            
            pdf_path = output_dir / f"{dwg_name}_DISC_{disc.name}.pdf"
            
            try:
                plot = doc.Plot
                plot.PlotToFile(str(pdf_path))
                generated.append(pdf_path)
                print(f"  [OK] {disc.name} ({disc.value}) -> {pdf_path.name}")
            except Exception:
                pass
            
        except Exception as e:
            print(f"  [ERROR] {disc.name}: {e}")
    
    # Restaurar estado original de capas
    for i in range(doc.Layers.Count):
        layer = doc.Layers.Item(i)
        try:
            layer.LayerOn = original_states.get(layer.Name, True)
        except Exception:
            pass
    
    print(f"[RENDER-DISC] {len(generated)} PDFs por disciplina generados")
    return generated
