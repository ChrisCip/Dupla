# Dupla

Dupla now uses an APS/Autodesk JSON-first budgeting pipeline. The official execution path no longer depends on AutoCAD COM automation.

## Official Architecture

```text
APS / Autodesk JSON + plan images
    -> normalized CAD facts
    -> normalized building inventory
    -> deterministic quantity takeoff
    -> rules engine expansion
    -> BC3 candidate matching
    -> final budget output
```

## Design Principles

- COM/AutoCAD automation is legacy only and is kept under [`_legacy`](/C:/Users/chris/Documents/Dupla/_legacy).
- Active modules stay project-agnostic. The production path does not assume Torre Giualca floor heights, apartment counts, fixed NPT tables, or hardcoded discipline mappings.
- Vision output is inventory-first, not Presto-discipline-first.
- Quantification is deterministic and every quantity carries a traceable formula.

## Active Modules

```text
Dupla/
├── agents/
│   ├── classifier_agent.py      # Deterministic BC3 candidate ranking
│   ├── quantifier_agent.py      # Deterministic quantity takeoff formulas
│   └── vision_agent.py          # Plan image -> normalized building inventory
├── aps_integration/
│   ├── aps_auth.py
│   ├── model_derivative.py      # APS/Model Derivative extraction helpers
│   └── oss_manager.py
├── core/
│   ├── pipeline.py              # Helper orchestration for the active path
│   └── schemas.py               # Shared typed models
├── processors/
│   ├── bc3_parser.py            # parse_bc3(path) reusable library function
│   └── json_processor.py        # Autodesk JSON -> normalized CAD facts
├── rules_engine/
│   └── __init__.py              # Minimal rule-expansion scaffold
├── tests/
│   ├── test_bc3_parser.py
│   └── test_quantifier_agent.py
├── requirements.txt             # Default APS/JSON-first dependencies
├── requirements-legacy.txt      # Optional legacy COM/CAD extras
└── _legacy/                     # Legacy COM and historical experiments
```

## Install

Default install for the active pipeline:

```powershell
pip install -r requirements.txt
```

Optional legacy install if you need to run old COM-based tooling:

```powershell
pip install -r requirements-legacy.txt
```

## Core Usage

### 1. Normalize Autodesk JSON facts

```powershell
python processors/json_processor.py resultados_model_derivative.json --output resumen_procesado.json
```

This produces a reusable fact payload with:

- layers
- texts
- dimensions
- hatches
- blocks
- geometry hints

### 2. Analyze plan images into normalized inventory

Use [`agents/vision_agent.py`](/C:/Users/chris/Documents/Dupla/agents/vision_agent.py) or import `analyze_plan(...)` / `run_full_vision_analysis(...)`.

The primary output is a `LevelInventory`-shaped JSON object containing:

- walls
- doors
- windows
- wet areas
- kitchens
- stairs
- fixtures
- structural elements

### 3. Parse BC3 catalogs

```powershell
python processors/bc3_parser.py data\catalog.bc3 --output data\catalog.json
```

Or import `parse_bc3(path)` directly.

### 4. Quantify and build budget candidates

```python
from core import ProjectContext, build_budget_from_inventory
from processors import parse_bc3
from core.schemas import level_inventory_from_dict
import json

with open("vision_inventory_result.json", "r", encoding="utf-8") as handle:
    level_payload = json.load(handle)

level_inventory = level_inventory_from_dict(level_payload)
catalog = parse_bc3("data/catalog.bc3")

context = ProjectContext(
    project_name="Example project",
    source_json_path="resultados_model_derivative.json",
    bc3_path="data/catalog.bc3",
)

budget = build_budget_from_inventory(context, [level_inventory], catalog)
```

## Notes

- [`TECHNICAL_DOCS.md`](/C:/Users/chris/Documents/Dupla/TECHNICAL_DOCS.md) documents the active APS/JSON-first modules.
- [`README_NUEVOS_CAMBIOS.md`](/C:/Users/chris/Documents/Dupla/README_NUEVOS_CAMBIOS.md) summarizes the migration.
- [`_legacy/README_LEGACY_COM.md`](/C:/Users/chris/Documents/Dupla/_legacy/README_LEGACY_COM.md) captures the retired COM assumptions and legacy execution notes.
