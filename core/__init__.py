from .schemas import (
    BudgetCandidate,
    Door,
    Fixture,
    Kitchen,
    LevelInventory,
    ProjectContext,
    QuantityTakeoff,
    Stair,
    StructuralElement,
    Wall,
    WetArea,
    Window,
    level_inventory_from_dict,
    project_context_from_dict,
)


def bootstrap_pipeline_inputs(*args, **kwargs):
    from .pipeline import bootstrap_pipeline_inputs as _bootstrap_pipeline_inputs

    return _bootstrap_pipeline_inputs(*args, **kwargs)


def build_budget_from_inventory(*args, **kwargs):
    from .pipeline import build_budget_from_inventory as _build_budget_from_inventory

    return _build_budget_from_inventory(*args, **kwargs)


def build_final_budget(*args, **kwargs):
    from .pipeline import build_final_budget as _build_final_budget

    return _build_final_budget(*args, **kwargs)

__all__ = [
    "bootstrap_pipeline_inputs",
    "build_budget_from_inventory",
    "build_final_budget",
    "BudgetCandidate",
    "Door",
    "Fixture",
    "Kitchen",
    "LevelInventory",
    "ProjectContext",
    "QuantityTakeoff",
    "Stair",
    "StructuralElement",
    "Wall",
    "WetArea",
    "Window",
    "level_inventory_from_dict",
    "project_context_from_dict",
]
