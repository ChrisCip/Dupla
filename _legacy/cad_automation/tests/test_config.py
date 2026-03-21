"""Tests para el módulo de configuración y nomenclatura."""

import pytest
from cad_automation.config import classify_layer, is_common_layer, get_conversion_factor
from cad_automation.models import DisciplineCode, UnitSystem


class TestClassifyLayer:
    """Tests de clasificación de capas por nomenclatura."""
    
    def test_architecture_standard(self):
        assert classify_layer("A-WALL") == DisciplineCode.A
        assert classify_layer("A-DOOR-FULL") == DisciplineCode.A
        assert classify_layer("A-FURN") == DisciplineCode.A
    
    def test_structural_standard(self):
        assert classify_layer("S-BEAM") == DisciplineCode.S
        assert classify_layer("S-COLS-300") == DisciplineCode.S
        assert classify_layer("S-FNDN") == DisciplineCode.S
    
    def test_mechanical_standard(self):
        assert classify_layer("M-DUCT") == DisciplineCode.M
        assert classify_layer("M-HVAC-SUPPLY") == DisciplineCode.M
    
    def test_electrical_standard(self):
        assert classify_layer("E-POWR") == DisciplineCode.E
        assert classify_layer("E-LITE") == DisciplineCode.E
    
    def test_plumbing_standard(self):
        assert classify_layer("P-PIPE") == DisciplineCode.P
        assert classify_layer("P-FIXT") == DisciplineCode.P
    
    def test_civil_standard(self):
        assert classify_layer("C-TOPO") == DisciplineCode.C
        assert classify_layer("C-ROAD") == DisciplineCode.C
    
    def test_fire_protection(self):
        assert classify_layer("F-SPKL") == DisciplineCode.F
    
    def test_common_layers_classified_as_general(self):
        assert classify_layer("G-GRID") == DisciplineCode.G
        assert classify_layer("G-ANNO") == DisciplineCode.G
    
    def test_layer_0_is_general(self):
        assert classify_layer("0") == DisciplineCode.G
    
    def test_defpoints_is_general(self):
        assert classify_layer("DEFPOINTS") == DisciplineCode.G
    
    def test_unknown_layers(self):
        assert classify_layer("RANDOM_LAYER") == DisciplineCode.UNKNOWN
        assert classify_layer("NOPREFIX") == DisciplineCode.UNKNOWN
    
    def test_case_insensitive(self):
        assert classify_layer("a-wall") == DisciplineCode.A
        assert classify_layer("s-beam") == DisciplineCode.S
        assert classify_layer("e-powr") == DisciplineCode.E
    
    def test_underscore_separator(self):
        assert classify_layer("A_WALL") == DisciplineCode.A
        assert classify_layer("S_BEAM") == DisciplineCode.S


class TestIsCommonLayer:
    """Tests para detección de capas comunes."""
    
    def test_layer_0(self):
        assert is_common_layer("0") is True
    
    def test_defpoints(self):
        assert is_common_layer("DEFPOINTS") is True
        assert is_common_layer("defpoints") is True
    
    def test_general_layers(self):
        assert is_common_layer("G-GRID") is True
        assert is_common_layer("G-ANNO") is True
    
    def test_border_layers(self):
        assert is_common_layer("BORDER") is True
        assert is_common_layer("BORDER_A3") is True
    
    def test_not_common(self):
        assert is_common_layer("A-WALL") is False
        assert is_common_layer("S-BEAM") is False


class TestUnitConversion:
    """Tests para factores de conversión de unidades."""
    
    def test_inches_to_mm(self):
        factor = get_conversion_factor(UnitSystem.INCHES, UnitSystem.MILLIMETERS)
        assert factor == pytest.approx(25.4)
    
    def test_feet_to_mm(self):
        factor = get_conversion_factor(UnitSystem.FEET, UnitSystem.MILLIMETERS)
        assert factor == pytest.approx(304.8)
    
    def test_meters_to_mm(self):
        factor = get_conversion_factor(UnitSystem.METERS, UnitSystem.MILLIMETERS)
        assert factor == pytest.approx(1000.0)
    
    def test_cm_to_mm(self):
        factor = get_conversion_factor(UnitSystem.CENTIMETERS, UnitSystem.MILLIMETERS)
        assert factor == pytest.approx(10.0)
    
    def test_mm_to_mm(self):
        factor = get_conversion_factor(UnitSystem.MILLIMETERS, UnitSystem.MILLIMETERS)
        assert factor == pytest.approx(1.0)
    
    def test_inches_to_meters(self):
        factor = get_conversion_factor(UnitSystem.INCHES, UnitSystem.METERS)
        assert factor == pytest.approx(0.0254)
    
    def test_feet_to_meters(self):
        factor = get_conversion_factor(UnitSystem.FEET, UnitSystem.METERS)
        assert factor == pytest.approx(0.3048)
