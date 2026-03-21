"""Tests para el módulo de normalización de unidades."""

import pytest
import ezdxf
from pathlib import Path

from cad_automation.units import normalize_units, detect_units
from cad_automation.models import UnitSystem


class TestDetectUnits:
    """Tests de detección de unidades."""
    
    def test_detect_inches(self, inches_file):
        unit, measurement = detect_units(inches_file)
        assert unit == UnitSystem.INCHES
        assert measurement == 0  # Imperial
    
    def test_detect_meters(self, meters_file):
        unit, measurement = detect_units(meters_file)
        assert unit == UnitSystem.METERS
        assert measurement == 1  # Metric


class TestNormalizeUnits:
    """Tests de normalización de unidades."""
    
    def test_inches_to_mm(self, inches_file, tmp_path):
        output_dir = tmp_path / "normalized"
        result = normalize_units(inches_file, UnitSystem.MILLIMETERS, output_dir)
        
        assert result is not None, "Debe generar archivo normalizado"
        assert result.exists()
        
        # Verificar que el archivo resultado tiene unidades mm
        doc = ezdxf.readfile(str(result))
        insunits = doc.header.get("$INSUNITS", 0)
        assert insunits == 4, "INSUNITS debe ser 4 (mm)"
    
    def test_meters_to_mm(self, meters_file, tmp_path):
        output_dir = tmp_path / "normalized"
        result = normalize_units(meters_file, UnitSystem.MILLIMETERS, output_dir)
        
        assert result is not None
        assert result.exists()
        
        doc = ezdxf.readfile(str(result))
        insunits = doc.header.get("$INSUNITS", 0)
        assert insunits == 4
    
    def test_mm_to_mm_no_change(self, tmp_path):
        """Un archivo ya en mm no debe generar salida."""
        # Crear archivo en mm
        doc = ezdxf.new("R2013")
        doc.header["$INSUNITS"] = 4  # mm
        file_path = tmp_path / "test_mm.dxf"
        doc.saveas(str(file_path))
        
        result = normalize_units(file_path, UnitSystem.MILLIMETERS, tmp_path / "out")
        assert result is None, "No debe generar archivo si ya está en mm"
    
    def test_scaling_preserves_geometry(self, inches_file, tmp_path):
        """Verifica que la geometría se escala correctamente."""
        # Leer original
        doc_orig = ezdxf.readfile(str(inches_file))
        msp_orig = doc_orig.modelspace()
        
        # Encontrar la polilínea
        orig_polylines = [e for e in msp_orig if e.dxftype() == "LWPOLYLINE"]
        assert len(orig_polylines) > 0
        
        orig_points = list(orig_polylines[0].get_points('xy'))
        # Original: rectángulo 120x96 pulgadas
        
        # Normalizar
        output_dir = tmp_path / "normalized"
        result = normalize_units(inches_file, UnitSystem.MILLIMETERS, output_dir)
        
        assert result is not None
        doc_new = ezdxf.readfile(str(result))
        msp_new = doc_new.modelspace()
        
        new_polylines = [e for e in msp_new if e.dxftype() == "LWPOLYLINE"]
        assert len(new_polylines) > 0
        
        new_points = list(new_polylines[0].get_points('xy'))
        
        # 120 pulgadas * 25.4 = 3048 mm
        assert new_points[1][0] == pytest.approx(120 * 25.4, rel=0.01)
        # 96 pulgadas * 25.4 = 2438.4 mm
        assert new_points[2][1] == pytest.approx(96 * 25.4, rel=0.01)
