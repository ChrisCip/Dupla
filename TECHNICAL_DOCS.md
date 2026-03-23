# Technical Docs

## Active Pipeline

The supported production flow is:

```text
APS / Autodesk JSON + plan images
    -> normalized CAD facts
    -> normalized building inventory
    -> deterministic quantity takeoff
    -> rules engine expansion
    -> BC3 candidate matching
    -> final budget output
```

## Module Responsibilities

### `processors/json_processor.py`

- Loads Autodesk Model Derivative JSON payloads.
- Normalizes reusable CAD facts instead of mapping directly to budget chapters.
- Emits:
  - `layers`
  - `texts`
  - `dimensions`
  - `hatches`
  - `blocks`
  - `geometry_hints`

### `agents/vision_agent.py`

- Uses plan images plus normalized CAD hints.
- Produces `LevelInventory`-shaped output.
- Avoids hardcoded tower calibration, fixed NPT tables, and default floor-height assumptions.

### `agents/quantifier_agent.py`

- Converts normalized inventory into deterministic `QuantityTakeoff` items.
- Every output quantity carries a formula and trace payload.

### `rules_engine`

- Minimal expansion scaffold for derived items.
- Current default behavior is conservative and only expands explicitly declared derivations.

### `processors/bc3_parser.py`

- Exposes `parse_bc3(path: str)`.
- Parses concepts, chapters, texts, hierarchy, and measurement records without hardcoded local paths.

### `agents/classifier_agent.py`

- Ranks BC3 candidates per takeoff using deterministic token overlap and unit compatibility.
- Keeps candidate selection separated from inventory inference and quantification.

## Schemas

Shared models live in [`core/schemas.py`](/C:/Users/chris/Documents/Dupla/core/schemas.py):

- `ProjectContext`
- `LevelInventory`
- `Wall`
- `Door`
- `Window`
- `WetArea`
- `Kitchen`
- `Stair`
- `Fixture`
- `StructuralElement`
- `QuantityTakeoff`
- `BudgetCandidate`

## Legacy

COM/AutoCAD automation and related assumptions remain available only under [`_legacy`](/C:/Users/chris/Documents/Dupla/_legacy). They are not part of the main execution path.
