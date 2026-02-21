"""
Fixtures de pytest: genera archivos DXF sintéticos en memoria
para probar todos los módulos sin necesidad de archivos reales.
"""

import math
import ezdxf
import pytest
from pathlib import Path
from ezdxf.document import Drawing


def create_multi_discipline_dxf() -> Drawing:
    """
    Crea un DXF sintético con capas de múltiples disciplinas.
    
    Disciplinas incluidas:
    - Arquitectura (A-WALL, A-DOOR, A-FURN)
    - Estructural (S-BEAM, S-COLS, S-FNDN)
    - Mecánico (M-DUCT, M-HVAC)
    - Eléctrico (E-POWR, E-LITE)
    - Plomería (P-PIPE, P-FIXT)
    - General (G-GRID, G-ANNO)
    - Capa 0 (común)
    """
    doc = ezdxf.new("R2013")
    msp = doc.modelspace()
    
    # --- Capas de Arquitectura ---
    doc.layers.new("A-WALL", dxfattribs={"color": 1})  # Rojo
    doc.layers.new("A-DOOR", dxfattribs={"color": 3})  # Verde
    doc.layers.new("A-FURN", dxfattribs={"color": 5})  # Azul
    
    # Muros (rectángulo exterior)
    msp.add_lwpolyline(
        [(0, 0), (10000, 0), (10000, 8000), (0, 8000)],
        close=True, dxfattribs={"layer": "A-WALL"}
    )
    # Muros interiores
    msp.add_line((5000, 0), (5000, 8000), dxfattribs={"layer": "A-WALL"})
    msp.add_line((0, 4000), (5000, 4000), dxfattribs={"layer": "A-WALL"})
    
    # Puertas
    msp.add_arc(center=(5000, 3200), radius=800, start_angle=0, end_angle=90,
                dxfattribs={"layer": "A-DOOR"})
    msp.add_arc(center=(5000, 4800), radius=800, start_angle=270, end_angle=360,
                dxfattribs={"layer": "A-DOOR"})
    
    # Muebles
    msp.add_lwpolyline(
        [(1000, 1000), (2500, 1000), (2500, 2000), (1000, 2000)],
        close=True, dxfattribs={"layer": "A-FURN"}
    )
    msp.add_circle(center=(7500, 6000), radius=500,
                   dxfattribs={"layer": "A-FURN"})
    
    # --- Capas Estructurales ---
    doc.layers.new("S-BEAM", dxfattribs={"color": 2})  # Amarillo
    doc.layers.new("S-COLS", dxfattribs={"color": 4})  # Cyan
    doc.layers.new("S-FNDN", dxfattribs={"color": 6})  # Magenta
    
    # Columnas (cuadrados 300x300)
    col_positions = [(0, 0), (5000, 0), (10000, 0),
                     (0, 8000), (5000, 8000), (10000, 8000)]
    for cx, cy in col_positions:
        msp.add_lwpolyline(
            [(cx-150, cy-150), (cx+150, cy-150),
             (cx+150, cy+150), (cx-150, cy+150)],
            close=True, dxfattribs={"layer": "S-COLS"}
        )
    
    # Vigas
    msp.add_line((0, 0), (10000, 0), dxfattribs={"layer": "S-BEAM"})
    msp.add_line((0, 8000), (10000, 8000), dxfattribs={"layer": "S-BEAM"})
    msp.add_line((5000, 0), (5000, 8000), dxfattribs={"layer": "S-BEAM"})
    
    # Fundación
    msp.add_lwpolyline(
        [(-500, -500), (10500, -500), (10500, 8500), (-500, 8500)],
        close=True, dxfattribs={"layer": "S-FNDN"}
    )
    
    # --- Capas Mecánicas (HVAC) ---
    doc.layers.new("M-DUCT", dxfattribs={"color": 30})  # Naranja
    doc.layers.new("M-HVAC", dxfattribs={"color": 32})
    
    # Ductos
    msp.add_lwpolyline(
        [(2000, 7500), (8000, 7500), (8000, 7200), (2000, 7200)],
        close=True, dxfattribs={"layer": "M-DUCT"}
    )
    msp.add_line((5000, 7500), (5000, 6000), dxfattribs={"layer": "M-DUCT"})
    
    # Equipos HVAC
    msp.add_circle(center=(5000, 5500), radius=300,
                   dxfattribs={"layer": "M-HVAC"})
    
    # --- Capas Eléctricas ---
    doc.layers.new("E-POWR", dxfattribs={"color": 10})  # Rojo oscuro
    doc.layers.new("E-LITE", dxfattribs={"color": 14})
    
    # Circuitos eléctricos
    msp.add_line((1000, 0), (1000, 4000), dxfattribs={"layer": "E-POWR"})
    msp.add_line((1000, 4000), (4000, 4000), dxfattribs={"layer": "E-POWR"})
    
    # Luminarias
    msp.add_circle(center=(2500, 2000), radius=100,
                   dxfattribs={"layer": "E-LITE"})
    msp.add_circle(center=(2500, 6000), radius=100,
                   dxfattribs={"layer": "E-LITE"})
    msp.add_circle(center=(7500, 4000), radius=100,
                   dxfattribs={"layer": "E-LITE"})
    
    # --- Capas de Plomería ---
    doc.layers.new("P-PIPE", dxfattribs={"color": 160})
    doc.layers.new("P-FIXT", dxfattribs={"color": 170})
    
    # Tuberías
    msp.add_line((8000, 1000), (8000, 7000), dxfattribs={"layer": "P-PIPE"})
    msp.add_line((6000, 1000), (8000, 1000), dxfattribs={"layer": "P-PIPE"})
    
    # Accesorios (fixtures)
    msp.add_circle(center=(6000, 1000), radius=200,
                   dxfattribs={"layer": "P-FIXT"})
    
    # --- Capas Generales ---
    doc.layers.new("G-GRID", dxfattribs={"color": 8})  # Gris
    doc.layers.new("G-ANNO", dxfattribs={"color": 7})
    
    # Grilla
    for x in range(0, 11000, 5000):
        msp.add_line((x, -1000), (x, 9000), dxfattribs={"layer": "G-GRID"})
    for y in range(0, 9000, 4000):
        msp.add_line((-1000, y), (11000, y), dxfattribs={"layer": "G-GRID"})
    
    # Anotaciones
    msp.add_text("PLANTA GENERAL", dxfattribs={
        "layer": "G-ANNO", "height": 300,
        "insert": (3000, 9000),
    })
    
    # Entidades en capa 0 (común)
    msp.add_point((0, 0), dxfattribs={"layer": "0"})
    
    # Configurar unidades: pulgadas (para probar normalización)
    doc.header["$INSUNITS"] = 1  # Inches
    doc.header["$MEASUREMENT"] = 0  # Imperial
    
    return doc


def create_multi_layout_dxf() -> Drawing:
    """
    Crea un DXF con múltiples layouts (paper spaces).
    
    Layouts:
    - Model: geometría del edificio
    - Planta Baja: paper space con vista de planta baja
    - Planta Alta: paper space con vista de planta alta
    - Corte A-A: paper space con sección
    """
    doc = ezdxf.new("R2013")
    msp = doc.modelspace()
    
    # Capas
    doc.layers.new("A-WALL", dxfattribs={"color": 1})
    doc.layers.new("A-DOOR", dxfattribs={"color": 3})
    doc.layers.new("G-BORDER", dxfattribs={"color": 7})
    
    # Geometría en Model Space
    msp.add_lwpolyline(
        [(0, 0), (20000, 0), (20000, 15000), (0, 15000)],
        close=True, dxfattribs={"layer": "A-WALL"}
    )
    msp.add_line((10000, 0), (10000, 15000), dxfattribs={"layer": "A-WALL"})
    msp.add_line((0, 7500), (20000, 7500), dxfattribs={"layer": "A-WALL"})
    
    # Crear Paper Spaces
    layout_names = ["Planta_Baja", "Planta_Alta", "Corte_A-A"]
    
    for name in layout_names:
        layout = doc.layouts.new(name)
        # Agregar un borde al paper space
        layout.add_lwpolyline(
            [(0, 0), (420, 0), (420, 297), (0, 297)],
            close=True, dxfattribs={"layer": "G-BORDER"}
        )
        # Título
        layout.add_text(name.replace("_", " ").upper(), dxfattribs={
            "layer": "G-BORDER", "height": 10,
            "insert": (20, 280),
        })
    
    doc.header["$INSUNITS"] = 4  # Millimeters
    doc.header["$MEASUREMENT"] = 1  # Metric
    
    return doc


def create_inches_dxf() -> Drawing:
    """Crea un DXF en pulgadas para probar conversión de unidades."""
    doc = ezdxf.new("R2013")
    msp = doc.modelspace()
    
    doc.layers.new("A-WALL", dxfattribs={"color": 1})
    
    # Un rectángulo de 10' x 8' (120" x 96") en pulgadas
    msp.add_lwpolyline(
        [(0, 0), (120, 0), (120, 96), (0, 96)],
        close=True, dxfattribs={"layer": "A-WALL"}
    )
    
    # Un círculo de 24" de diámetro
    msp.add_circle(center=(60, 48), radius=12, dxfattribs={"layer": "A-WALL"})
    
    doc.header["$INSUNITS"] = 1  # Inches
    doc.header["$MEASUREMENT"] = 0  # Imperial
    
    return doc


def create_meters_dxf() -> Drawing:
    """Crea un DXF en metros para probar conversión de unidades."""
    doc = ezdxf.new("R2013")
    msp = doc.modelspace()
    
    doc.layers.new("S-BEAM", dxfattribs={"color": 2})
    
    # Viga de 6m de largo
    msp.add_line((0, 0), (6, 0), dxfattribs={"layer": "S-BEAM"})
    msp.add_line((0, 0.3), (6, 0.3), dxfattribs={"layer": "S-BEAM"})
    
    doc.header["$INSUNITS"] = 6  # Meters
    doc.header["$MEASUREMENT"] = 1  # Metric
    
    return doc


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
def tmp_dxf_dir(tmp_path) -> Path:
    """Directorio temporal para archivos DXF de prueba."""
    return tmp_path


@pytest.fixture
def multi_discipline_file(tmp_path) -> Path:
    """Archivo DXF multi-disciplina guardado en disco."""
    file_path = tmp_path / "test_multi_discipline.dxf"
    doc = create_multi_discipline_dxf()
    doc.saveas(str(file_path))
    return file_path


@pytest.fixture
def multi_layout_file(tmp_path) -> Path:
    """Archivo DXF multi-layout guardado en disco."""
    file_path = tmp_path / "test_multi_layout.dxf"
    doc = create_multi_layout_dxf()
    doc.saveas(str(file_path))
    return file_path


@pytest.fixture
def inches_file(tmp_path) -> Path:
    """Archivo DXF en pulgadas guardado en disco."""
    file_path = tmp_path / "test_inches.dxf"
    doc = create_inches_dxf()
    doc.saveas(str(file_path))
    return file_path


@pytest.fixture
def meters_file(tmp_path) -> Path:
    """Archivo DXF en metros guardado en disco."""
    file_path = tmp_path / "test_meters.dxf"
    doc = create_meters_dxf()
    doc.saveas(str(file_path))
    return file_path
