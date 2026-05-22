# Delivery Readiness Report — SERENA 18 — registro provisional de niveles para coordinacion 2.5D
**Run:** `serena18_analysis_06`  |  **Generated:** 2026-05-07T21:47:17.779101+00:00

## Decision: `READY_FOR_CLIENT_REVIEW`

- Critical failures: `0`
- Warnings: `0`
- Checks passed: `23`

## 1. Estado general
- Required outputs all present: `True`
- Optional outputs: `elements_by_dwg` (si), `clash_element_links` (si), `semantic_elements_by_dwg` (si), `hotspot_incidents` (si), `debug_candidates` (si)

## 2. Archivos generados
- `summary.json` ✓
- `analysis_bot_context.json` ✓
- `technical_coordination_report.md` ✓
- `coordination_report_human.md` ✓
- `primary_incidents.md` ✓
- `coordinate_audit.md` ✓
- `elements_by_dwg.json` ✓
- `clash_element_links.json` ✓
- `semantic_elements_by_dwg.json` ✓
- `hotspot_incidents.md` ✓
- `debug_candidates.json` ✓

## 3. Consistencia de conteos
- ✓ `count_selected_candidates`: count_selected_candidates consistent: 3
- ✓ `count_scheduled_pairs`: count_scheduled_pairs consistent: 2
- ✓ `count_primary_incidents`: count_primary_incidents consistent: 53
- ✓ `count_elements`: count_elements consistent: 1050
- ✓ `count_defendable`: count_defendable consistent: 4
- ✓ `count_validation`: count_validation consistent: 49
- ✓ `count_debug_conflicts`: count_debug_conflicts consistent: 179
- ✓ `count_suppressed`: count_suppressed consistent: 596
- ✓ `count_pairs_schedule_vs_context`: Pair count consistent: 2
- ✓ `mapping_count_leq_incidents`: mapped=53 unmapped=0 total=53 <= incidents=53

## 4. Consistencia de incidentes
- ✓ `count_primary_incidents`: count_primary_incidents consistent: 53
- ✓ `incident_no_duplicate_ids`: No duplicate incident_ids (53 incidents)
- ✓ `incident_no_annotation_in_defendable`: No annotation layers in 4 defendable incidents
- ✓ `incident_all_have_level_id`: All incidents have level_id
- ✓ `mapping_count_leq_incidents`: mapped=53 unmapped=0 total=53 <= incidents=53

## 5. Estado de mapping CAD
- ✓ `mapping_count_leq_incidents`: mapped=53 unmapped=0 total=53 <= incidents=53
- ✓ `mapping_candidate_ids_exist`: All candidate element_ids exist in elements_by_dwg

## 6. Estado de semantic grouping / naming
- ✓ `semantic_candidate_ids_exist`: All semantic_group_ids (486) consistent
- ✓ `semantic_summaries_present`: semantic_grouping_summary=True, semantic_naming_summary=True

## 7. Riesgos abiertos
- Ninguno.

## 8. Decisión recomendada
**READY_FOR_CLIENT_REVIEW** (VERDE)

No hay failures críticos y los warnings (0) están dentro del umbral aceptable. El paquete puede presentarse al cliente con las advertencias documentadas.
