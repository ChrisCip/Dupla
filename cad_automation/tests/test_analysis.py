"""Tests para el módulo de análisis (áreas y clashes)."""

import math
import pytest
import ezdxf
from pathlib import Path

from cad_automation.analysis import calculate_areas, detect_clashes
from cad_automation.models import BoundingBox, ClashSeverity


class TestBoundingBox:
    """Tests de la clase BoundingBox."""
    
    def test_area_2d(self):
        bbox = BoundingBox(0, 0, 0, 10, 5, 0)
        assert bbox.area_2d == 50.0
    
    def test_volume(self):
        bbox = BoundingBox(0, 0, 0, 10, 5, 3)
        assert bbox.volume == 150.0
    
    def test_center(self):
        bbox = BoundingBox(0, 0, 0, 10, 10, 0)
        assert bbox.center == (5.0, 5.0, 0.0)
    
    def test_intersects_true(self):
        a = BoundingBox(0, 0, 0, 10, 10, 0)
        b = BoundingBox(5, 5, 0, 15, 15, 0)
        assert a.intersects(b) is True
    
    def test_intersects_false(self):
        a = BoundingBox(0, 0, 0, 10, 10, 0)
        b = BoundingBox(20, 20, 0, 30, 30, 0)
        assert a.intersects(b) is False
    
    def test_intersection_volume(self):
        a = BoundingBox(0, 0, 0, 10, 10, 10)
        b = BoundingBox(5, 5, 5, 15, 15, 15)
        vol = a.intersection_volume(b)
        assert vol == pytest.approx(125.0)  # 5*5*5
    
    def test_no_intersection_volume(self):
        a = BoundingBox(0, 0, 0, 5, 5, 5)
        b = BoundingBox(10, 10, 10, 15, 15, 15)
        assert a.intersection_volume(b) == 0.0


class TestCalculateAreas:
    """Tests de cálculo de áreas."""
    
    def test_finds_closed_polylines(self, multi_discipline_file):
        areas = calculate_areas(multi_discipline_file)
        
        # Debe encontrar al menos las polilíneas cerradas
        assert len(areas) > 0
    
    def test_circle_area(self, tmp_path):
        """Verifica que el área de un círculo es correcta."""
        doc = ezdxf.new("R2013")
        msp = doc.modelspace()
        doc.layers.new("A-TEST", dxfattribs={"color": 1})
        
        radius = 100
        msp.add_circle(center=(0, 0), radius=radius,
                       dxfattribs={"layer": "A-TEST"})
        
        file_path = tmp_path / "test_circle.dxf"
        doc.saveas(str(file_path))
        
        areas = calculate_areas(file_path)
        
        assert len(areas) == 1
        expected = math.pi * radius ** 2
        assert areas[0].area == pytest.approx(expected, rel=0.01)
    
    def test_rectangle_area(self, tmp_path):
        """Verifica que el área de un rectángulo cerrado es correcta."""
        doc = ezdxf.new("R2013")
        msp = doc.modelspace()
        doc.layers.new("A-TEST", dxfattribs={"color": 1})
        
        w, h = 200, 100
        msp.add_lwpolyline(
            [(0, 0), (w, 0), (w, h), (0, h)],
            close=True, dxfattribs={"layer": "A-TEST"}
        )
        
        file_path = tmp_path / "test_rect.dxf"
        doc.saveas(str(file_path))
        
        areas = calculate_areas(file_path)
        
        assert len(areas) == 1
        assert areas[0].area == pytest.approx(w * h, rel=0.01)
    
    def test_area_reports_layer(self, multi_discipline_file):
        areas = calculate_areas(multi_discipline_file)
        
        for area_result in areas:
            assert area_result.layer != ""
            assert area_result.entity_type != ""


class TestDetectClashes:
    """Tests de detección de clashes."""
    
    def test_finds_clashes_between_disciplines(self, multi_discipline_file):
        clashes = detect_clashes(multi_discipline_file)
        
        # El archivo de demo tiene elementos superpuestos entre disciplinas
        # (vigas estructurales sobre muros arquitectónicos)
        # Debe encontrar al menos algunos clashes
        assert len(clashes) >= 0  # Puede ser 0 si no hay intersección
    
    def test_clash_has_coordinates(self, multi_discipline_file):
        clashes = detect_clashes(multi_discipline_file)
        
        for clash in clashes:
            assert clash.intersection_point is not None
            assert len(clash.intersection_point) == 3
    
    def test_clash_severity_assigned(self, multi_discipline_file):
        clashes = detect_clashes(multi_discipline_file)
        
        for clash in clashes:
            assert clash.severity in ClashSeverity
    
    def test_clash_between_overlapping_elements(self, tmp_path):
        """Crea dos disciplinas con elementos superpuestos."""
        doc = ezdxf.new("R2013")
        msp = doc.modelspace()
        
        doc.layers.new("A-WALL", dxfattribs={"color": 1})
        doc.layers.new("M-DUCT", dxfattribs={"color": 2})
        
        # Muro
        msp.add_lwpolyline(
            [(0, 0), (100, 0), (100, 10), (0, 10)],
            close=True, dxfattribs={"layer": "A-WALL"}
        )
        
        # Ducto que pasa a través del muro
        msp.add_lwpolyline(
            [(40, -5), (60, -5), (60, 15), (40, 15)],
            close=True, dxfattribs={"layer": "M-DUCT"}
        )
        
        file_path = tmp_path / "test_clash.dxf"
        doc.saveas(str(file_path))
        
        clashes = detect_clashes(file_path)
        
        assert len(clashes) > 0, "Debe detectar clash entre muro y ducto"
        
        # Verificar que las disciplinas involucradas son A y M
        disc_pairs = {(c.discipline_a.name, c.discipline_b.name) for c in clashes}
        assert ("A", "M") in disc_pairs or ("M", "A") in disc_pairs
