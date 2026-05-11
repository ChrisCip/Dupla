# Role: Caveman Engineer
- Brevity is mandatory.
- No filler words, no pleasantries.
- Code speaks for itself.
- If asked for code, give code. No explain unless asked.
- Minimize token output at all costs.
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Dupla turns construction plans (DWG + PDF) into traceable, exportable budget lines (Excel + BC3/FIEBDC for import into Presto). The production pipeline is **APS/Autodesk JSON-first** — it does NOT depend on COM/AutoCAD automation. Anything COM-based lives under `_legacy/` and is not part of the active path.

Python 3.10+.

## Common commands

Install:
```powershell
pip install -r requirements.txt              # active pipeline
pip install -r requirements-legacy.txt       # only if touching _legacy COM tooling
```

Run the full multi-discipline pipeline (GEBSA IV project):
```powershell
python dupla_run_gebsa.py                    # all 4 disciplines
python dupla_run_gebsa.py --only arquitectura
python dupla_run_gebsa.py --resume           # resume from run_state.json
```
Disciplines run in this order: `arquitectura`, `estructura`, `sanitario`, `electrico`. Each emits a partial Excel + BC3 plus validation reports.

Single-stage utilities:
```powershell
python processors/json_processor.py resultados_model_derivative.json --output resumen_procesado.json
python processors/bc3_parser.py data\catalog.bc3 --output data\catalog.json
```

Tests (pytest):
```powershell
pytest                                       # full suite
pytest tests/test_quantifier_agent.py        # single file
pytest tests/test_rules_engine_walls_v2.py::test_name   # single test
```

Required environment (`.env` at repo root, loaded via `python-dotenv`):
- `CLIENT_ID`, `CLIENT_SECRET` — Autodesk APS (Model Derivative must be enabled on the account)
- `OPENAI_API_KEY`, optionally `OPENAI_CHAT_MODEL`, `OPENAI_VISION_MODEL` (default `gpt-4o`)

`dupla_run_gebsa.py` runs a preflight that checks for these plus `pyyaml`, `pymupdf`, per-discipline `domain_rules.yaml`, and per-discipline `knowledge/prompts/<disc>/user_prompt.md`. Fix any preflight error before running.

## Pipeline architecture

End-to-end flow (driven by `core/pipeline.py:build_budget_from_sources`, orchestrated per-discipline by `dupla_run_gebsa.py`):

```
APS extraction (DWG -> Model Derivative JSON)
  -> processors/json_processor.py  -> normalized CAD facts (layers/texts/dims/hatches/blocks/geometry_hints)
PDF -> rendered page images (fitz / PyMuPDF)
  -> agents/vision_agent.py (GPT-4o)  -> LevelInventory (walls, doors, windows, wet areas, kitchens, stairs, fixtures, structural elements)
Merge CAD facts + vision inventory
  -> agents/quantifier_agent.py  -> deterministic QuantityTakeoff (every quantity carries a formula + trace)
  -> rules_engine/  -> expansion of derived items (conservative: only explicitly declared derivations)
  -> knowledge/bc3_embeddings + agents/classifier_agent.py  -> BC3 candidate matching
  -> budget/composer.py + consolidator.py  -> final budget
  -> budget/export_excel.py  -> dupla_budget_ready_full.xlsx
  -> budget/export_bc3.py    -> dupla_budget_ready_full.bc3 (Presto import)
```

### Disciplines

Each discipline (`disciplines/<name>/`) plugs in via `disciplines/registry.py` (`get_engine(disc_id)`) and ships its own `engine.py`, `quantifier.py`, `chapters.py`, and `domain_rules.yaml`. `disciplines/domain_validator.py` validates vision output against the discipline's rules and emits `missing_attributes` / `unclassified` reports. When adding or modifying a discipline, update all four files **and** ensure `knowledge/prompts/<disc>/user_prompt.md` exists — the preflight enforces this.

### Shared schemas

All typed models live in `core/schemas.py`: `ProjectContext`, `LevelInventory`, `Wall`, `Door`, `Window`, `WetArea`, `Kitchen`, `Stair`, `Fixture`, `StructuralElement`, `QuantityTakeoff`, `BudgetCandidate`. Treat these as the contract between stages — vision agent emits them, quantifier/rules_engine/classifier consume them.

### Output structure

Runs write into `OUTPUTS_DIR` (default `C:\Users\chris\Downloads\dupla1` in `dupla_run_gebsa.py`) via `core/output_structure.py:RunOutputDir`. State for `--resume` lives in `run_state.json` at the run root. Rendered PDF pages are cached by sha256 of the PDF path under `rendered_pages/p_<hash>/`.

## Design constraints (enforce when editing)

- **No project-specific calibration in active modules.** No hardcoded Torre Giualca floor heights, apartment counts, NPT tables, or fixed discipline mappings. Project-agnostic inference only.
- **Vision output is inventory-first, not Presto-discipline-first** — vision emits `LevelInventory`, mapping to BC3 chapters happens downstream.
- **Quantification is deterministic.** Every `QuantityTakeoff` must carry a formula and trace payload; no opaque numbers.
- **COM/AutoCAD code stays in `_legacy/`.** Don't reintroduce COM dependencies into the active path.

## Reference docs in repo

- `README.md` — install + entry-point examples
- `TECHNICAL_DOCS.md` — per-module responsibilities for the active APS/JSON-first path
- `PROJECT_OVERVIEW.md` — broader Spanish-language overview, pipeline diagram, module table
- `_legacy/README_LEGACY_COM.md` — retired COM assumptions