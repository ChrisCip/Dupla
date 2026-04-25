"""Coordinación 2.5D: registro de niveles, elementos con envolvente Z y clash determinista."""

from core.coordination.clash import (
    ClashConflict,
    ClashIncident,
    clash_pairs,
    conflicts_to_conflict_notes,
    group_conflicts_into_incidents,
)
from core.coordination.models_25d import (
    AttachmentPoint,
    Discipline,
    Element25D,
    ElevationMode,
    ProjectLevel,
    ZInterval,
    element_from_inventory_meters,
)
from core.coordination.registry import (
    ProjectLevelRegistry,
    ProjectLevelRegistryDocument,
    SourceExcludePattern,
    ViewLevelPattern,
)
from core.coordination.units import from_mm, to_mm

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
    "ZInterval",
    "ViewLevelPattern",
    "clash_pairs",
    "conflicts_to_conflict_notes",
    "group_conflicts_into_incidents",
    "element_from_inventory_meters",
    "from_mm",
    "to_mm",
]
