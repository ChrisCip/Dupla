"""
Shared typed models for the active APS/JSON inventory pipeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass
class ModelBase:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectContext(ModelBase):
    project_id: str | None = None
    project_name: str | None = None
    source_json_path: str | None = None
    plan_image_paths: list[str] = field(default_factory=list)
    bc3_path: str | None = None
    measurement_unit: str = "m"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Wall(ModelBase):
    id: str
    level_id: str | None = None
    source_layers: list[str] = field(default_factory=list)
    length_m: float | None = None
    height_m: float | None = None
    thickness_m: float | None = None
    area_m2: float | None = None
    material_hint: str | None = None
    structural: bool | None = None
    openings_count: int = 0
    confidence: float | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class Door(ModelBase):
    id: str
    level_id: str | None = None
    source_layers: list[str] = field(default_factory=list)
    count: int = 1
    width_m: float | None = None
    height_m: float | None = None
    type_hint: str | None = None
    material_hint: str | None = None
    exterior: bool | None = None
    confidence: float | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class Window(ModelBase):
    id: str
    level_id: str | None = None
    source_layers: list[str] = field(default_factory=list)
    count: int = 1
    width_m: float | None = None
    height_m: float | None = None
    type_hint: str | None = None
    glazing_hint: str | None = None
    confidence: float | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class WetArea(ModelBase):
    id: str
    level_id: str | None = None
    kind: str = "bathroom"
    count: int = 1
    estimated_area_m2: float | None = None
    fixture_ids: list[str] = field(default_factory=list)
    confidence: float | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class Kitchen(ModelBase):
    id: str
    level_id: str | None = None
    count: int = 1
    estimated_area_m2: float | None = None
    island_present: bool | None = None
    fixture_ids: list[str] = field(default_factory=list)
    confidence: float | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class Stair(ModelBase):
    id: str
    level_id: str | None = None
    count: int = 1
    flights: int | None = None
    riser_count: int | None = None
    tread_count: int | None = None
    width_m: float | None = None
    elevation_change_m: float | None = None
    confidence: float | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class Fixture(ModelBase):
    id: str
    level_id: str | None = None
    fixture_type: str = "other"
    count: int = 1
    unit: str = "unit"
    location_hint: str | None = None
    confidence: float | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class StructuralElement(ModelBase):
    id: str
    level_id: str | None = None
    element_type: str = "other"
    count: int = 1
    length_m: float | None = None
    area_m2: float | None = None
    volume_m3: float | None = None
    material_hint: str | None = None
    confidence: float | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class LevelInventory(ModelBase):
    level_id: str
    level_name: str
    source_image: str | None = None
    source_view: str | None = None
    cad_hints: dict[str, Any] = field(default_factory=dict)
    walls: list[Wall] = field(default_factory=list)
    doors: list[Door] = field(default_factory=list)
    windows: list[Window] = field(default_factory=list)
    wet_areas: list[WetArea] = field(default_factory=list)
    kitchens: list[Kitchen] = field(default_factory=list)
    stairs: list[Stair] = field(default_factory=list)
    fixtures: list[Fixture] = field(default_factory=list)
    structural_elements: list[StructuralElement] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    confidence: float | None = None


@dataclass
class QuantityTakeoff(ModelBase):
    item_key: str
    source_element_type: str
    level_id: str | None = None
    quantity: float = 0.0
    unit: str = ""
    formula: str = ""
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetCandidate(ModelBase):
    takeoff_key: str
    bc3_code: str
    summary: str
    unit: str
    score: float
    rationale: str
    source: str = "keyword_match"


def project_context_from_dict(data: Mapping[str, Any]) -> ProjectContext:
    return ProjectContext(
        project_id=data.get("project_id"),
        project_name=data.get("project_name"),
        source_json_path=data.get("source_json_path"),
        plan_image_paths=list(data.get("plan_image_paths", [])),
        bc3_path=data.get("bc3_path"),
        measurement_unit=str(data.get("measurement_unit", "m")),
        metadata=dict(data.get("metadata", {})),
    )


def _list_of(model_cls: Any, values: list[Mapping[str, Any]], level_id: str) -> list[Any]:
    items: list[Any] = []
    for value in values:
        payload = dict(value)
        payload.setdefault("level_id", level_id)
        items.append(model_cls(**payload))
    return items


def level_inventory_from_dict(data: Mapping[str, Any]) -> LevelInventory:
    level_id = str(data.get("level_id") or data.get("level_name") or "level")
    return LevelInventory(
        level_id=level_id,
        level_name=str(data.get("level_name") or level_id),
        source_image=data.get("source_image"),
        source_view=data.get("source_view"),
        cad_hints=dict(data.get("cad_hints", {})),
        walls=_list_of(Wall, list(data.get("walls", [])), level_id),
        doors=_list_of(Door, list(data.get("doors", [])), level_id),
        windows=_list_of(Window, list(data.get("windows", [])), level_id),
        wet_areas=_list_of(WetArea, list(data.get("wet_areas", [])), level_id),
        kitchens=_list_of(Kitchen, list(data.get("kitchens", [])), level_id),
        stairs=_list_of(Stair, list(data.get("stairs", [])), level_id),
        fixtures=_list_of(Fixture, list(data.get("fixtures", [])), level_id),
        structural_elements=_list_of(
            StructuralElement,
            list(data.get("structural_elements", [])),
            level_id,
        ),
        notes=list(data.get("notes", [])),
        confidence=data.get("confidence"),
    )
