"""
Modelos de datos para el sistema de automatización CAD.
Dataclasses que representan archivos, capas, disciplinas y resultados de análisis.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from datetime import datetime


class DisciplineCode(Enum):
    """Códigos de disciplina estándar NCS/AIA para AEC."""
    A = "Arquitectura"
    S = "Estructural"
    M = "Mecánico / HVAC"
    E = "Eléctrico"
    P = "Plomería"
    C = "Civil"
    F = "Protección contra Incendios"
    G = "General"
    L = "Paisajismo"
    T = "Telecomunicaciones"
    I = "Interiorismo"
    Q = "Equipamiento"
    UNKNOWN = "Sin clasificar"


class UnitSystem(Enum):
    """Sistemas de unidades CAD ($INSUNITS values)."""
    UNITLESS = 0
    INCHES = 1
    FEET = 2
    MILES = 3
    MILLIMETERS = 4
    CENTIMETERS = 5
    METERS = 6
    KILOMETERS = 7
    MICROINCHES = 8
    MILS = 9
    YARDS = 10
    ANGSTROMS = 11
    NANOMETERS = 12
    MICRONS = 13
    DECIMETERS = 14
    DECAMETERS = 15
    HECTOMETERS = 16
    GIGAMETERS = 17
    ASTRONOMICAL = 18
    LIGHTYEARS = 19
    PARSECS = 20


class FileFormat(Enum):
    """Formatos de archivo CAD soportados."""
    DXF = "dxf"
    DWG = "dwg"
    RVT = "rvt"
    IFC = "ifc"


class ClashSeverity(Enum):
    """Severidad de clashes detectados."""
    CRITICAL = "CRITICO"      # Penetración significativa
    MAJOR = "MAYOR"           # Intersección parcial  
    MINOR = "MENOR"           # Proximidad peligrosa (clearance)
    INFO = "INFORMATIVO"      # Toque o proximidad


@dataclass
class BoundingBox:
    """Bounding box de una entidad o grupo de entidades."""
    min_x: float = 0.0
    min_y: float = 0.0
    min_z: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0
    max_z: float = 0.0

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def depth(self) -> float:
        return self.max_z - self.min_z

    @property
    def area_2d(self) -> float:
        """Área en planta (XY)."""
        return self.width * self.height

    @property
    def volume(self) -> float:
        """Volumen del bounding box."""
        return self.width * self.height * self.depth

    @property
    def center(self) -> tuple[float, float, float]:
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2,
        )

    def intersects(self, other: "BoundingBox") -> bool:
        """Verifica si dos bounding boxes se intersectan."""
        return (
            self.min_x <= other.max_x and self.max_x >= other.min_x and
            self.min_y <= other.max_y and self.max_y >= other.min_y and
            self.min_z <= other.max_z and self.max_z >= other.min_z
        )

    def intersection_volume(self, other: "BoundingBox") -> float:
        """Calcula el volumen de intersección entre dos bounding boxes."""
        if not self.intersects(other):
            return 0.0
        ix = max(0, min(self.max_x, other.max_x) - max(self.min_x, other.min_x))
        iy = max(0, min(self.max_y, other.max_y) - max(self.min_y, other.min_y))
        iz = max(0, min(self.max_z, other.max_z) - max(self.min_z, other.min_z))
        return ix * iy * iz


@dataclass
class LayerInfo:
    """Información de una capa CAD."""
    name: str
    color: int = 7  # 7 = blanco/negro por defecto en AutoCAD
    linetype: str = "Continuous"
    is_on: bool = True
    is_frozen: bool = False
    is_locked: bool = False
    entity_count: int = 0
    discipline: DisciplineCode = DisciplineCode.UNKNOWN
    
    @property
    def is_visible(self) -> bool:
        return self.is_on and not self.is_frozen


@dataclass
class EntityInfo:
    """Información resumida de una entidad CAD."""
    dxf_type: str  # LINE, LWPOLYLINE, CIRCLE, TEXT, INSERT, etc.
    layer: str
    handle: str = ""
    color: int = 256  # BYLAYER
    bbox: Optional[BoundingBox] = None
    is_closed: bool = False
    area: float = 0.0
    length: float = 0.0


@dataclass
class LayoutInfo:
    """Información de un layout (paper space) en un archivo DXF."""
    name: str
    tab_order: int = 0
    entity_count: int = 0
    is_model_space: bool = False
    paper_width: float = 0.0
    paper_height: float = 0.0


@dataclass
class CADFile:
    """Modelo completo de un archivo CAD procesado."""
    path: Path
    format: FileFormat
    file_size: int = 0
    modified_date: Optional[datetime] = None
    dxf_version: str = ""
    units: UnitSystem = UnitSystem.UNITLESS
    measurement: int = 0  # 0=imperial, 1=metric
    
    # Datos extraídos
    layers: list[LayerInfo] = field(default_factory=list)
    layouts: list[LayoutInfo] = field(default_factory=list)
    entities: list[EntityInfo] = field(default_factory=list)
    
    # Clasificación
    disciplines_found: list[DisciplineCode] = field(default_factory=list)
    
    @property
    def filename(self) -> str:
        return self.path.name
    
    @property
    def total_entities(self) -> int:
        return len(self.entities)
    
    @property
    def total_layers(self) -> int:
        return len(self.layers)


@dataclass
class DisciplineGroup:
    """Agrupación de capas y entidades de una disciplina."""
    discipline: DisciplineCode
    layers: list[LayerInfo] = field(default_factory=list)
    entity_count: int = 0
    common_layers: list[LayerInfo] = field(default_factory=list)
    
    @property
    def total_layers(self) -> int:
        return len(self.layers) + len(self.common_layers)


@dataclass
class ClashResult:
    """Resultado de un clash entre dos entidades/disciplinas."""
    entity_a_handle: str
    entity_a_layer: str
    entity_a_type: str
    discipline_a: DisciplineCode
    entity_b_handle: str
    entity_b_layer: str
    entity_b_type: str
    discipline_b: DisciplineCode
    severity: ClashSeverity
    intersection_point: tuple[float, float, float] = (0.0, 0.0, 0.0)
    intersection_volume: float = 0.0
    description: str = ""


@dataclass
class AreaResult:
    """Resultado de cálculo de área."""
    entity_handle: str
    entity_type: str
    layer: str
    discipline: DisciplineCode
    area: float  # en unidades cuadradas del archivo
    perimeter: float = 0.0
    description: str = ""


@dataclass
class AnalysisSummary:
    """Resumen completo del análisis de un archivo."""
    source_file: Path
    timestamp: datetime = field(default_factory=datetime.now)
    total_entities: int = 0
    total_layers: int = 0
    total_layouts: int = 0
    disciplines_found: list[DisciplineCode] = field(default_factory=list)
    areas: list[AreaResult] = field(default_factory=list)
    clashes: list[ClashResult] = field(default_factory=list)
    unit_original: UnitSystem = UnitSystem.UNITLESS
    unit_converted: Optional[UnitSystem] = None
    files_generated: list[Path] = field(default_factory=list)

    @property
    def total_area(self) -> float:
        return sum(a.area for a in self.areas)
    
    @property
    def total_clashes(self) -> int:
        return len(self.clashes)
    
    @property
    def critical_clashes(self) -> int:
        return sum(1 for c in self.clashes if c.severity == ClashSeverity.CRITICAL)
