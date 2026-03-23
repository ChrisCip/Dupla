# Migration Summary

## What Changed

- The official architecture is now APS/Autodesk JSON plus plan images, not COM.
- Active modules now produce normalized facts, normalized inventory, deterministic quantities, rule-expanded takeoffs, and BC3 candidate matches.
- COM-specific assumptions and Windows-only AutoCAD automation were pushed out of the production path and documented as legacy only.

## Main Refactors

- [`processors/bc3_parser.py`](/C:/Users/chris/Documents/Dupla/processors/bc3_parser.py) now exposes `parse_bc3(path: str)` with no hardcoded local file paths.
- [`processors/json_processor.py`](/C:/Users/chris/Documents/Dupla/processors/json_processor.py) now emits normalized CAD facts instead of discipline-mapped budget output.
- [`agents/vision_agent.py`](/C:/Users/chris/Documents/Dupla/agents/vision_agent.py) now targets normalized building inventory instead of final Presto disciplines.
- [`agents/quantifier_agent.py`](/C:/Users/chris/Documents/Dupla/agents/quantifier_agent.py) now converts normalized inventory into deterministic takeoffs with formulas.
- [`rules_engine/__init__.py`](/C:/Users/chris/Documents/Dupla/rules_engine/__init__.py) introduces a conservative rules scaffold for derived items.
- [`core/schemas.py`](/C:/Users/chris/Documents/Dupla/core/schemas.py) centralizes the shared typed models.

## Updated File Tree

```text
Dupla/
├── agents/
├── aps_integration/
├── core/
├── processors/
├── rules_engine/
├── tests/
├── requirements.txt
├── requirements-legacy.txt
└── _legacy/
```

## Remaining TODOs

- Expand BC3 hierarchy parsing for more edge cases in the FIEBDC decomposition grammar.
- Add first-class domain rules for finishes, assemblies, and opening deductions.
- Improve BC3 candidate matching with synonyms and multilingual normalization.
