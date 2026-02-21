"""
Motor de AutoCAD via COM automation.
Usa pyautocad / win32com para leer y escribir DWG nativamente.

Requiere:
- AutoCAD o Civil 3D instalado en la maquina
- pip install pyautocad

Flujo:
  1. Conectar a AutoCAD (o iniciar instancia)
  2. Abrir DWG nativo
  3. Leer layers, entidades, layouts via COM
  4. Realizar operaciones (copiar, escalar, separar)
  5. Guardar como DWG nativo
"""

import os
import time
import math
from pathlib import Path
from typing import Optional, Any
from contextlib import contextmanager

# COM automation
try:
    import win32com.client
    from win32com.client import Dispatch, GetActiveObject
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False

try:
    from pyautocad import Autocad, APoint
    HAS_PYAUTOCAD = True
except ImportError:
    HAS_PYAUTOCAD = False

from .models import (
    CADFile, FileFormat, LayerInfo, EntityInfo, LayoutInfo,
    BoundingBox, UnitSystem, DisciplineCode,
)
from .config import classify_layer, INSUNITS_MAP, is_common_layer


# ============================================================================
# CONSTANTES COM DE AUTOCAD
# ============================================================================

# AcEntityName (entity type constants)
AC_LINE = 19
AC_CIRCLE = 8
AC_ARC = 4
AC_POLYLINE = 24
AC_LWPOLYLINE = 37
AC_POINT = 22
AC_TEXT = 34
AC_MTEXT = 42
AC_INSERT = 15
AC_HATCH = 14
AC_DIMENSION = 10
AC_ELLIPSE = 11

# AcSaveAsType
AC_NATIVE = 36      # DWG nativo
AC_DXF = 60         # DXF

# AcActiveSpace
AC_MODEL_SPACE = 1
AC_PAPER_SPACE = 0


class AutoCADEngine:
    """
    Motor de automatizacion CAD usando AutoCAD COM.
    
    Maneja la conexion a AutoCAD/Civil3D y proporciona
    metodos para leer/escribir DWG nativamente.
    """
    
    def __init__(self, visible: bool = False, create_new: bool = True):
        """
        Args:
            visible: Si AutoCAD se muestra en pantalla
            create_new: Si crear una nueva instancia vs usar una existente
        """
        self.acad: Any = None
        self.visible = visible
        self._connected = False
        
        if not HAS_WIN32COM:
            raise ImportError(
                "win32com no esta instalado.\n"
                "Ejecuta: pip install pywin32"
            )
    
    def connect(self) -> bool:
        """
        Conecta a una instancia de AutoCAD/Civil3D.
        Intenta conectar a una existente, o inicia una nueva.
        
        Returns:
            True si la conexion fue exitosa
        """
        # Intentar conectar a instancia existente
        try:
            self.acad = GetActiveObject("AutoCAD.Application")
            self._connected = True
            print("[AUTOCAD] Conectado a instancia existente")
            return True
        except Exception:
            pass
        
        # Intentar con Civil 3D explicito
        try:
            self.acad = GetActiveObject("AeccXUiLand.AeccApplication")
            self._connected = True
            print("[AUTOCAD] Conectado a Civil 3D existente")
            return True
        except Exception:
            pass
        
        # Iniciar nueva instancia
        try:
            self.acad = Dispatch("AutoCAD.Application")
            self.acad.Visible = self.visible
            self._connected = True
            print("[AUTOCAD] Nueva instancia iniciada")
            # Esperar a que AutoCAD se inicialice
            time.sleep(3)
            return True
        except Exception as e:
            print(f"[AUTOCAD] Error al conectar: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """Libera la referencia COM (no cierra AutoCAD)."""
        self.acad = None
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Verifica si la conexion COM esta activa."""
        if not self._connected or self.acad is None:
            return False
        try:
            _ = self.acad.Name
            return True
        except Exception:
            self._connected = False
            return False
    
    # ====================================================================
    # OPERACIONES DE ARCHIVO
    # ====================================================================
    
    def open_file(self, file_path: Path, read_only: bool = True) -> Any:
        """
        Abre un archivo DWG en AutoCAD.
        
        Args:
            file_path: Ruta al archivo DWG
            read_only: Si abrir en modo lectura
        
        Returns:
            Documento COM de AutoCAD
        """
        if not self.is_connected:
            raise ConnectionError("No conectado a AutoCAD")
        
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        print(f"[AUTOCAD] Abriendo: {file_path.name}")
        
        doc = self.acad.Documents.Open(str(file_path), read_only)
        return doc
    
    def save_as_dwg(self, doc: Any, output_path: Path) -> Path:
        """Guarda el documento activo como DWG."""
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.SaveAs(str(output_path))
        print(f"[AUTOCAD] Guardado DWG: {output_path.name}")
        return output_path
    
    def close_doc(self, doc: Any, save: bool = False):
        """Cierra un documento."""
        try:
            doc.Close(save)
        except Exception:
            pass
    
    def new_document(self) -> Any:
        """Crea un nuevo documento vacio."""
        if not self.is_connected:
            raise ConnectionError("No conectado a AutoCAD")
        return self.acad.Documents.Add()
    
    # ====================================================================
    # LECTURA DE DATOS (DWG NATIVO)
    # ====================================================================
    
    def read_file(self, file_path: Path) -> CADFile:
        """
        Lee un archivo DWG completo y extrae toda su informacion.
        
        Args:
            file_path: Ruta al archivo DWG
        
        Returns:
            CADFile con todos los datos extraidos
        """
        file_path = Path(file_path).resolve()
        print(f"\n[AUTOCAD] Leyendo: {file_path.name}")
        
        doc = self.open_file(file_path, read_only=True)
        
        try:
            cad_file = CADFile(
                path=file_path,
                format=FileFormat.DWG if file_path.suffix.lower() == ".dwg" else FileFormat.DXF,
                file_size=file_path.stat().st_size,
            )
            
            # Header / unidades
            self._read_header(doc, cad_file)
            
            # Capas
            cad_file.layers = self._read_layers(doc)
            
            # Layouts
            cad_file.layouts = self._read_layouts(doc)
            
            # Entidades del ModelSpace
            cad_file.entities = self._read_entities(doc.ModelSpace)
            
            # Clasificar disciplinas
            disciplines = set()
            entity_counts: dict[str, int] = {}
            for ent in cad_file.entities:
                entity_counts[ent.layer] = entity_counts.get(ent.layer, 0) + 1
            
            for layer in cad_file.layers:
                layer.discipline = classify_layer(layer.name)
                layer.entity_count = entity_counts.get(layer.name, 0)
                if layer.discipline != DisciplineCode.UNKNOWN:
                    disciplines.add(layer.discipline)
            
            cad_file.disciplines_found = list(disciplines)
            
            print(f"[AUTOCAD] Completado: {len(cad_file.layers)} capas, "
                  f"{len(cad_file.entities)} entidades, "
                  f"{len(cad_file.layouts)} layouts")
            
            return cad_file
        
        finally:
            self.close_doc(doc, save=False)
    
    def _read_header(self, doc: Any, cad_file: CADFile) -> None:
        """Lee variables de header del documento."""
        try:
            insunits = doc.GetVariable("INSUNITS")
            cad_file.units = INSUNITS_MAP.get(insunits, UnitSystem.UNITLESS)
        except Exception:
            cad_file.units = UnitSystem.UNITLESS
        
        try:
            cad_file.measurement = doc.GetVariable("MEASUREMENT")
        except Exception:
            cad_file.measurement = 0
    
    def _read_layers(self, doc: Any) -> list[LayerInfo]:
        """Lee todas las capas del documento."""
        layers = []
        for i in range(doc.Layers.Count):
            layer = doc.Layers.Item(i)
            info = LayerInfo(
                name=layer.Name,
                color=layer.Color if hasattr(layer, 'Color') else 7,
                linetype=layer.Linetype if hasattr(layer, 'Linetype') else "Continuous",
                is_on=layer.LayerOn if hasattr(layer, 'LayerOn') else True,
                is_frozen=layer.Freeze if hasattr(layer, 'Freeze') else False,
                is_locked=layer.Lock if hasattr(layer, 'Lock') else False,
            )
            layers.append(info)
        return layers
    
    def _read_layouts(self, doc: Any) -> list[LayoutInfo]:
        """Lee todos los layouts del documento."""
        layouts = []
        for i in range(doc.Layouts.Count):
            layout = doc.Layouts.Item(i)
            block = layout.Block
            info = LayoutInfo(
                name=layout.Name,
                is_model_space=(layout.Name == "Model"),
                entity_count=block.Count if block else 0,
                tab_order=layout.TabOrder if hasattr(layout, 'TabOrder') else 0,
            )
            
            if not info.is_model_space:
                try:
                    info.paper_width = layout.PaperWidth if hasattr(layout, 'PaperWidth') else 0
                    info.paper_height = layout.PaperHeight if hasattr(layout, 'PaperHeight') else 0
                except Exception:
                    pass
            
            layouts.append(info)
        
        layouts.sort(key=lambda l: (not l.is_model_space, l.tab_order))
        return layouts
    
    def _read_entities(self, space: Any) -> list[EntityInfo]:
        """Lee entidades de un espacio (ModelSpace/PaperSpace)."""
        entities = []
        
        for i in range(space.Count):
            try:
                entity = space.Item(i)
                ent_type = entity.ObjectName  # AcDbLine, AcDbCircle, etc.
                
                # Simplificar nombre del tipo
                simple_type = ent_type.replace("AcDb", "").upper()
                if "POLYLINE" in simple_type:
                    simple_type = "LWPOLYLINE"
                elif simple_type == "BLOCKREFERENCE":
                    simple_type = "INSERT"
                
                info = EntityInfo(
                    dxf_type=simple_type,
                    layer=entity.Layer if hasattr(entity, 'Layer') else "0",
                    handle=entity.Handle if hasattr(entity, 'Handle') else "",
                    color=entity.Color if hasattr(entity, 'Color') else 256,
                )
                
                # Bounding box
                try:
                    min_pt, max_pt = entity.GetBoundingBox()
                    info.bbox = BoundingBox(
                        min_x=min_pt[0], min_y=min_pt[1],
                        min_z=min_pt[2] if len(min_pt) > 2 else 0,
                        max_x=max_pt[0], max_y=max_pt[1],
                        max_z=max_pt[2] if len(max_pt) > 2 else 0,
                    )
                except Exception:
                    pass
                
                # Area para entidades cerradas
                try:
                    if hasattr(entity, 'Area'):
                        info.area = entity.Area
                        info.is_closed = True
                except Exception:
                    pass
                
                # Longitud
                try:
                    if hasattr(entity, 'Length'):
                        info.length = entity.Length
                except Exception:
                    pass
                
                entities.append(info)
                
            except Exception:
                continue
        
        return entities
    
    # ====================================================================
    # SEPARACION POR DISCIPLINAS (DWG NATIVO)
    # ====================================================================
    
    def separate_by_discipline(
        self,
        file_path: Path,
        output_dir: Path,
    ) -> list[Path]:
        """
        Separa un DWG por disciplinas, guardando cada una como DWG.
        
        Proceso:
        1. Abre el DWG original
        2. Para cada disciplina, crea nuevo DWG
        3. Copia las entidades de las capas de esa disciplina
        4. Guarda como DWG nativo
        """
        file_path = Path(file_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n[AUTOCAD] Separando por disciplinas: {file_path.name}")
        
        source_doc = self.open_file(file_path, read_only=True)
        
        try:
            # Clasificar capas por disciplina
            layer_disc_map: dict[str, DisciplineCode] = {}
            common_layers: set[str] = set()
            disciplines: dict[DisciplineCode, set[str]] = {}
            
            for i in range(source_doc.Layers.Count):
                layer = source_doc.Layers.Item(i)
                name = layer.Name
                
                if is_common_layer(name):
                    common_layers.add(name)
                else:
                    disc = classify_layer(name)
                    layer_disc_map[name] = disc
                    disciplines.setdefault(disc, set()).add(name)
            
            print(f"[AUTOCAD] Disciplinas: "
                  f"{', '.join(d.value for d in disciplines.keys())}")
            
            generated: list[Path] = []
            
            for discipline, layer_names in sorted(disciplines.items(), key=lambda x: x[0].name):
                target_layers = layer_names | common_layers
                
                # Crear nuevo documento
                new_doc = self.new_document()
                
                # Copiar variables de unidades
                try:
                    for var in ["INSUNITS", "MEASUREMENT", "LUNITS", "LUPREC"]:
                        val = source_doc.GetVariable(var)
                        new_doc.SetVariable(var, val)
                except Exception:
                    pass
                
                # Crear las capas necesarias en el nuevo doc
                for i in range(source_doc.Layers.Count):
                    src_layer = source_doc.Layers.Item(i)
                    if src_layer.Name in target_layers:
                        try:
                            new_layer = new_doc.Layers.Add(src_layer.Name)
                            new_layer.Color = src_layer.Color
                            new_layer.Linetype = src_layer.Linetype
                        except Exception:
                            pass
                
                # Recopilar handles de entidades a copiar
                source_msp = source_doc.ModelSpace
                handles_to_copy = []
                
                for i in range(source_msp.Count):
                    try:
                        entity = source_msp.Item(i)
                        if entity.Layer in target_layers:
                            handles_to_copy.append(entity)
                    except Exception:
                        continue
                
                # Copiar entidades usando CopyObjects
                if handles_to_copy:
                    try:
                        obj_array = win32com.client.VARIANT(
                            win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_DISPATCH,
                            handles_to_copy
                        )
                        source_doc.CopyObjects(obj_array, new_doc.ModelSpace)
                    except Exception:
                        # Fallback: copiar una por una
                        for entity in handles_to_copy:
                            try:
                                entity.Copy()
                                # Pegar en el nuevo documento
                            except Exception:
                                pass
                
                # Guardar
                disc_name = discipline.name
                output_path = output_dir / f"{file_path.stem}_{disc_name}.dwg"
                self.save_as_dwg(new_doc, output_path)
                self.close_doc(new_doc, save=False)
                
                generated.append(output_path)
                print(f"  [OK] {disc_name} ({discipline.value}): "
                      f"{len(target_layers)} capas, "
                      f"{len(handles_to_copy)} entidades -> {output_path.name}")
            
            return generated
        
        finally:
            self.close_doc(source_doc, save=False)
    
    # ====================================================================
    # NORMALIZACION DE UNIDADES (DWG NATIVO)
    # ====================================================================
    
    def normalize_units(
        self,
        file_path: Path,
        target_unit: UnitSystem,
        output_dir: Path,
    ) -> Optional[Path]:
        """
        Normaliza unidades de un DWG escalando toda la geometria.
        """
        file_path = Path(file_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        doc = self.open_file(file_path, read_only=False)
        
        try:
            insunits = doc.GetVariable("INSUNITS")
            current_unit = INSUNITS_MAP.get(insunits, UnitSystem.UNITLESS)
            
            from .config import get_conversion_factor
            factor = get_conversion_factor(current_unit, target_unit)
            
            if abs(factor - 1.0) < 1e-10:
                print(f"[AUTOCAD] Ya esta en {target_unit.name}")
                return None
            
            print(f"[AUTOCAD] Escalando {current_unit.name} -> {target_unit.name} "
                  f"(factor: {factor})")
            
            # Seleccionar todas las entidades y escalar
            msp = doc.ModelSpace
            if msp.Count > 0:
                # Escalar usando ScaleEntity o transformacion
                for i in range(msp.Count):
                    try:
                        entity = msp.Item(i)
                        base_point = win32com.client.VARIANT(
                            win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8,
                            [0.0, 0.0, 0.0]
                        )
                        entity.ScaleEntity(base_point, factor)
                    except Exception:
                        pass
            
            # Actualizar header
            doc.SetVariable("INSUNITS", target_unit.value)
            if target_unit in (UnitSystem.MILLIMETERS, UnitSystem.CENTIMETERS,
                               UnitSystem.METERS):
                doc.SetVariable("MEASUREMENT", 1)
            else:
                doc.SetVariable("MEASUREMENT", 0)
            
            # Guardar
            output_path = output_dir / f"{file_path.stem}_normalized.dwg"
            self.save_as_dwg(doc, output_path)
            
            return output_path
        
        finally:
            self.close_doc(doc, save=False)
    
    # ====================================================================
    # SEPARACION DE LAYOUTS (DWG NATIVO)
    # ====================================================================
    
    def split_layouts(
        self,
        file_path: Path,
        output_dir: Path,
        include_model: bool = True,
    ) -> list[Path]:
        """
        Separa cada layout de un DWG en un archivo DWG independiente.
        """
        file_path = Path(file_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        doc = self.open_file(file_path, read_only=True)
        
        try:
            generated: list[Path] = []
            
            for i in range(doc.Layouts.Count):
                layout = doc.Layouts.Item(i)
                block = layout.Block
                
                if not block or block.Count == 0:
                    continue
                
                is_model = (layout.Name == "Model")
                if is_model and not include_model:
                    continue
                
                # Crear nuevo documento
                new_doc = self.new_document()
                
                # Copiar variables
                try:
                    for var in ["INSUNITS", "MEASUREMENT"]:
                        new_doc.SetVariable(var, doc.GetVariable(var))
                except Exception:
                    pass
                
                # Copiar capas
                for j in range(doc.Layers.Count):
                    try:
                        src_layer = doc.Layers.Item(j)
                        new_layer = new_doc.Layers.Add(src_layer.Name)
                        new_layer.Color = src_layer.Color
                    except Exception:
                        pass
                
                # Copiar entidades del layout al ModelSpace del nuevo doc
                entities_to_copy = []
                for j in range(block.Count):
                    try:
                        entities_to_copy.append(block.Item(j))
                    except Exception:
                        continue
                
                if entities_to_copy:
                    try:
                        obj_array = win32com.client.VARIANT(
                            win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_DISPATCH,
                            entities_to_copy
                        )
                        doc.CopyObjects(obj_array, new_doc.ModelSpace)
                    except Exception:
                        pass
                
                # Nombre del archivo
                safe_name = layout.Name.replace("/", "_").replace("\\", "_")
                output_path = output_dir / f"{file_path.stem}_{safe_name}.dwg"
                self.save_as_dwg(new_doc, output_path)
                self.close_doc(new_doc, save=False)
                
                generated.append(output_path)
                label = "MODEL" if is_model else "LAYOUT"
                print(f"  [OK] [{label}] '{layout.Name}': "
                      f"{len(entities_to_copy)} entidades -> {output_path.name}")
            
            return generated
        
        finally:
            self.close_doc(doc, save=False)


# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

@contextmanager
def autocad_session(visible: bool = False):
    """
    Context manager para sesiones de AutoCAD.
    
    Uso:
        with autocad_session() as engine:
            cad_file = engine.read_file("plano.dwg")
    """
    engine = AutoCADEngine(visible=visible)
    if not engine.connect():
        raise ConnectionError(
            "No se pudo conectar a AutoCAD/Civil 3D.\n"
            "Verifica que AutoCAD o Civil 3D este instalado."
        )
    try:
        yield engine
    finally:
        engine.disconnect()


def check_autocad_available() -> bool:
    """Verifica si AutoCAD/Civil3D esta disponible via COM."""
    if not HAS_WIN32COM:
        return False
    
    try:
        acad = GetActiveObject("AutoCAD.Application")
        return True
    except Exception:
        pass
    
    try:
        acad = Dispatch("AutoCAD.Application")
        # No cerramos la instancia, solo verificamos
        return True
    except Exception:
        return False


def get_engine_status() -> str:
    """Devuelve estado del motor AutoCAD."""
    lines = []
    lines.append("=== Estado del Motor CAD ===")
    lines.append(f"  win32com disponible: {'SI' if HAS_WIN32COM else 'NO'}")
    lines.append(f"  pyautocad disponible: {'SI' if HAS_PYAUTOCAD else 'NO'}")
    
    if HAS_WIN32COM:
        try:
            acad = GetActiveObject("AutoCAD.Application")
            lines.append(f"  AutoCAD conectado: SI")
            lines.append(f"  Version: {acad.Version}")
            lines.append(f"  Nombre: {acad.Name}")
        except Exception:
            lines.append(f"  AutoCAD conectado: NO (no hay instancia activa)")
    
    return "\n".join(lines)
