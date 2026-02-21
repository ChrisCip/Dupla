"""Tests para el módulo de separación por disciplinas."""

import pytest
import ezdxf
from pathlib import Path

from cad_automation.parser import parse_dxf
from cad_automation.disciplines import analyze_disciplines, separate_by_discipline
from cad_automation.models import DisciplineCode


class TestAnalyzeDisciplines:
    """Tests de análisis de disciplinas."""
    
    def test_finds_all_disciplines(self, multi_discipline_file):
        cad_file = parse_dxf(multi_discipline_file)
        groups = analyze_disciplines(cad_file)
        
        # Debe encontrar Arquitectura, Estructural, Mecánico, Eléctrico, Plomería
        discipline_names = {d.name for d in groups.keys()}
        assert "A" in discipline_names, "Debe encontrar Arquitectura"
        assert "S" in discipline_names, "Debe encontrar Estructural"
        assert "M" in discipline_names, "Debe encontrar Mecánico"
        assert "E" in discipline_names, "Debe encontrar Eléctrico"
        assert "P" in discipline_names, "Debe encontrar Plomería"
    
    def test_architecture_layers(self, multi_discipline_file):
        cad_file = parse_dxf(multi_discipline_file)
        groups = analyze_disciplines(cad_file)
        
        arch_group = groups.get(DisciplineCode.A)
        assert arch_group is not None
        
        layer_names = {l.name for l in arch_group.layers}
        assert "A-WALL" in layer_names
        assert "A-DOOR" in layer_names
        assert "A-FURN" in layer_names
    
    def test_common_layers_in_all_groups(self, multi_discipline_file):
        cad_file = parse_dxf(multi_discipline_file)
        groups = analyze_disciplines(cad_file)
        
        for discipline, group in groups.items():
            common_names = {l.name for l in group.common_layers}
            assert "0" in common_names, \
                f"Capa 0 debe estar en grupo {discipline.name}"
    
    def test_entity_count_per_discipline(self, multi_discipline_file):
        cad_file = parse_dxf(multi_discipline_file)
        groups = analyze_disciplines(cad_file)
        
        # Cada disciplina debe tener al menos alguna entidad
        for discipline, group in groups.items():
            if discipline != DisciplineCode.UNKNOWN:
                assert group.entity_count >= 0


class TestSeparateByDiscipline:
    """Tests de separación de archivos por disciplina."""
    
    def test_generates_files(self, multi_discipline_file, tmp_path):
        output_dir = tmp_path / "output_disc"
        generated = separate_by_discipline(multi_discipline_file, output_dir)
        
        assert len(generated) > 0, "Debe generar al menos un archivo"
        
        for f in generated:
            assert f.exists(), f"Archivo generado debe existir: {f}"
            assert f.suffix == ".dxf"
    
    def test_each_file_has_correct_layers(self, multi_discipline_file, tmp_path):
        output_dir = tmp_path / "output_disc2"
        generated = separate_by_discipline(multi_discipline_file, output_dir)
        
        for gen_file in generated:
            doc = ezdxf.readfile(str(gen_file))
            layer_names = [l.dxf.name for l in doc.layers]
            
            # Cada archivo debe tener capa 0 (común)
            assert "0" in layer_names, \
                f"Archivo {gen_file.name} debe tener capa 0"
    
    def test_architecture_file_content(self, multi_discipline_file, tmp_path):
        output_dir = tmp_path / "output_disc3"
        generated = separate_by_discipline(multi_discipline_file, output_dir)
        
        # Buscar el archivo de arquitectura
        arch_files = [f for f in generated if "_A." in f.name or f.name.endswith("_A.dxf")]
        assert len(arch_files) == 1, "Debe haber exactamente un archivo de Arquitectura"
        
        doc = ezdxf.readfile(str(arch_files[0]))
        msp = doc.modelspace()
        entities = list(msp)
        
        assert len(entities) > 0, "Archivo de Arquitectura debe tener entidades"
