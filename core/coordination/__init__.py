"""Backward-compatible re-exports.

Todo el código de coordinación vive ahora en el paquete top-level
`coordination/`. Estos re-exports existen para no romper imports
legacy. Nuevos imports deben usar `coordination.*` directamente.
"""

# Core
from coordination.core.clash import clash_pairs, group_conflicts_into_incidents, ClashConflict, ClashIncident, conflicts_to_conflict_notes
from coordination.core.models_25d import AttachmentPoint, Discipline, Element25D, ElevationMode, ProjectLevel, ZInterval, element_from_inventory_meters
from coordination.core.clash_element_mapper import *
from coordination.core.units import *
from coordination.core.registry import *
from coordination.core.nasas_paths import *

# Extraction
from coordination.extraction.from_dwg_accore import *
from coordination.extraction.from_dwg_aps import *
from coordination.extraction.from_dwg_com import *
from coordination.extraction.from_dwg_ezdxf import *
from coordination.extraction.from_pdf_vector import *
from coordination.extraction.from_raster_image import *
from coordination.extraction.from_autodesk_properties import *
from coordination.extraction.from_aps_viewer_dump import *
from coordination.extraction.aps_cache import *

# Selection
from coordination.selection.source_selection import *
from coordination.selection.fast_compare import *
from coordination.selection.coordinate_audit import *
from coordination.selection.level_inference import *

# Semantic
from coordination.semantic.semantic_elements import *

# Reporting
from coordination.reporting.reporting import *

__all__ = [
    "AttachmentPoint",
    "ClashConflict",
    "ClashIncident",
    "Discipline",
    "Element25D",
    "ElevationMode",
    "ProjectLevel",
    "ProjectLevelRegistry",
    "ProjectLevelRegistryDocument",
    "SourceExcludePattern",
    "ViewLevelPattern",
    "ZInterval",
    "clash_pairs",
    "conflicts_to_conflict_notes",
    "element_from_inventory_meters",
    "from_mm",
    "group_conflicts_into_incidents",
    "to_mm",
]
