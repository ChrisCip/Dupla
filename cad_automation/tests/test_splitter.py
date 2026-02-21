"""Tests para el módulo de separación de layouts."""

import pytest
import ezdxf
from pathlib import Path

from cad_automation.splitter import split_layouts, list_layouts


class TestListLayouts:
    """Tests de listado de layouts."""
    
    def test_lists_all_layouts(self, multi_layout_file):
        layouts = list_layouts(multi_layout_file)
        
        # Model + default Layout1 + 3 custom paper spaces = 5 layouts
        assert len(layouts) == 5
    
    def test_model_space_identified(self, multi_layout_file):
        layouts = list_layouts(multi_layout_file)
        
        model_layouts = [l for l in layouts if l["is_model"]]
        assert len(model_layouts) == 1
        assert model_layouts[0]["name"] == "Model"
    
    def test_paper_spaces_named(self, multi_layout_file):
        layouts = list_layouts(multi_layout_file)
        
        paper_names = {l["name"] for l in layouts if not l["is_model"]}
        assert "Planta_Baja" in paper_names
        assert "Planta_Alta" in paper_names
        assert "Corte_A-A" in paper_names


class TestSplitLayouts:
    """Tests de separación de layouts."""
    
    def test_generates_files(self, multi_layout_file, tmp_path):
        output_dir = tmp_path / "split"
        generated = split_layouts(multi_layout_file, output_dir)
        
        assert len(generated) > 0, "Debe generar al menos un archivo"
        
        for f in generated:
            assert f.exists()
            assert f.suffix == ".dxf"
    
    def test_correct_number_of_files(self, multi_layout_file, tmp_path):
        output_dir = tmp_path / "split"
        generated = split_layouts(multi_layout_file, output_dir)
        
        # Model + 3 paper spaces = 4 archivos
        assert len(generated) == 4
    
    def test_no_model_option(self, multi_layout_file, tmp_path):
        output_dir = tmp_path / "split_no_model"
        generated = split_layouts(
            multi_layout_file, output_dir,
            include_model_space=False,
        )
        
        # Solo 3 paper spaces
        assert len(generated) == 3
        
        # Ninguno debe ser "Model"
        for f in generated:
            assert "Model" not in f.name
    
    def test_each_file_has_entities(self, multi_layout_file, tmp_path):
        output_dir = tmp_path / "split_entities"
        generated = split_layouts(multi_layout_file, output_dir)
        
        for f in generated:
            doc = ezdxf.readfile(str(f))
            msp = doc.modelspace()
            entities = list(msp)
            assert len(entities) > 0, \
                f"Archivo {f.name} debe tener entidades"
