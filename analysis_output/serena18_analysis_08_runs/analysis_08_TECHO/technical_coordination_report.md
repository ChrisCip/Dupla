# Technical Coordination Report - SERENA 18 — registro provisional de niveles para coordinacion 2.5D

- Root: `C:/Users/Enrique Casanova/Dupla/repositorios/SERENA 18`
- Profile: `fast_compare`
- Status: `completed`
- Generated: `2026-05-05T22:58:22.381782+00:00`

## Executive Summary
- Scheduled pairs reviewed: `6` across `7` source files.
- Defendable findings today: `131` of `157` primary incidents.
- Technical noise held outside the main report: `1262` debug conflicts and `1328` suppressed elements.
- Confidence mix on primary incidents: medium=98, high=59.

## Report Logic
- `Defendable findings` come from `primary` incidents only; they already passed comparability, level, and geometry gating.
- `Noise / technical signal` stays outside the executive list and is fed by debug conflicts, suppressed geometry, blocked pairs, or audit statuses.
- `Severity` estimates coordination impact. `Priority` defines the recommended review order. `Confidence` estimates how defendable the finding is with the current extraction quality.

## Severity and Priority Criteria
| Label | Meaning |
| --- | --- |
| `critical` | Large or repeated conflict with strong geometry and high review urgency. |
| `high` | Strong coordination issue that should enter the next interdisciplinary review round. |
| `medium` | Usable finding, but likely needs scoped validation or pair-level discussion. |
| `low` | Weak signal or isolated case; keep visible but do not sell as a final clash. |

| Priority | Use |
| --- | --- |
| `P1` | Review immediately in the next coordination session. |
| `P2` | Review after the main blockers, still within the current cycle. |
| `P3` | Track as low urgency or manual validation only. |

## Defendable Findings
| ID | Priority | Severity | Confidence | Level | Disciplines | Location | Action owner | Recommended action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `incident_0076` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,841,135, 624,666,914) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |
| `incident_0036` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,835,779, 624,670,611) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |
| `incident_0043` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,839,897, 624,668,453) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |
| `incident_0046` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,841,274, 624,666,898) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |
| `incident_0124` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,841,116, 624,666,915) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |
| `incident_0092` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,837,924, 624,669,135) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |
| `incident_0091` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,837,924, 624,666,277) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |
| `incident_0035` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,835,779, 624,663,350) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |
| `incident_0006` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,835,818, 624,663,352) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |
| `incident_0112` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,835,818, 624,663,352) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |
| `incident_0018` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,841,116, 624,666,915) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |
| `incident_0146` | P1 | critical | high | `TECHO` | Discipline.ARCH / Discipline.STRUC | TECHO; (168,841,073, 624,666,920) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y escalar en la siguiente ronda de coordinacion. |

## Findings Requiring Manual Validation
| ID | Reason | Level | Layers | Suggested handling |
| --- | --- | --- | --- | --- |
| `incident_0016` | line-based geometry needs manual confirmation | `TECHO` | `I-FLOR-FIN / PARCELS` | Revisar el par directamente y revisar con validacion acotada. |
| `incident_0122` | line-based geometry needs manual confirmation | `TECHO` | `I-FLOR-FIN / PARCELS` | Revisar el par directamente y revisar con validacion acotada. |
| `incident_0144` | line-based geometry needs manual confirmation | `TECHO` | `I-FLOR-FIN / PARCELS` | Revisar el par directamente y revisar con validacion acotada. |
| `incident_0079` | line-based geometry needs manual confirmation | `TECHO` | `I-FURN / Solares` | Revisar el par directamente y revisar con validacion acotada. |
| `incident_0149` | line-based geometry needs manual confirmation | `TECHO` | `I-WALL / Solares` | Revisar el par directamente y revisar con validacion acotada. |
| `incident_0073` | line-based geometry needs manual confirmation | `TECHO` | `I-WALL / Solares` | Revisar el par directamente y revisar con validacion acotada. |
| `incident_0028` | line-based geometry needs manual confirmation | `TECHO` | `I-FURN / TITULOS` | Revisar el par directamente y revisar con validacion acotada. |
| `incident_0057` | line-based geometry needs manual confirmation | `TECHO` | `I-FURN / TITULOS` | Revisar el par directamente y revisar con validacion acotada. |
| `incident_0085` | line-based geometry needs manual confirmation | `TECHO` | `I-FURN / TITULOS` | Revisar el par directamente y revisar con validacion acotada. |
| `incident_0104` | line-based geometry needs manual confirmation | `TECHO` | `I-FURN / TITULOS` | Revisar el par directamente y revisar con validacion acotada. |
| `incident_0134` | line-based geometry needs manual confirmation | `TECHO` | `I-FURN / TITULOS` | Revisar el par directamente y revisar con validacion acotada. |
| `incident_0156` | line-based geometry needs manual confirmation | `TECHO` | `I-FURN / TITULOS` | Revisar el par directamente y revisar con validacion acotada. |

## Reader Sections

### Arquitectura
- Coverage in this run: `direct`
- Current focus: no direct pair for this profile in the current run
- No direct incidents were mapped to this reader profile in the current run.

### Electrico
- Coverage in this run: `not_in_run`
- Current focus: no direct pair for this profile in the current run
- No direct incidents were mapped to this reader profile in the current run.

### Sanitario
- Coverage in this run: `not_in_run`
- Current focus: no direct pair for this profile in the current run
- No direct incidents were mapped to this reader profile in the current run.

## Pair Summary
| Pair | Incidents | Members | Priority focus | Severity mix | Confidence mix |
| --- | ---: | ---: | --- | --- | --- |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E18 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. I).dwg` | 30 | 192 | P1 | high=10, medium=10, low=7, critical=3 | medium=19, high=11 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg` | 29 | 190 | P1 | medium=11, high=9, low=5, critical=4 | medium=19, high=10 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg` | 29 | 208 | P1 | medium=12, high=9, critical=5, low=3 | medium=19, high=10 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg` | 28 | 196 | P1 | medium=11, high=7, critical=6, low=4 | medium=17, high=11 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E19 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. II).dwg` | 22 | 156 | P1 | medium=8, high=7, critical=4, low=3 | medium=13, high=9 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E17 - PLANTA EST.DE TECHOS T2 EN MADERA Y DETALLES - MOD, VIGAS VY-13, VY-26, VY-25.dwg` | 19 | 136 | P1 | high=6, medium=5, critical=4, low=4 | medium=11, high=8 |

## Noise and Technical Support
- Debug conflicts kept outside the executive list: `1262`.
- Suppressed geometry count: `1328`; main reasons: bounds_fallback=1228, container_bbox=100.
- Audit status mix: eligible=7.
- Unscheduled or blocked pairs: `0`; main reasons: none.
- Hotspots are kept as concentration zones only: `769` grouped cases.

## Output Files
- `technical_coordination_report.md`: executive and interdisciplinary reading.
- `primary_incidents.md`: defendable incident register with pair-level detail.
- `hotspot_incidents.md`: concentration zones and technical clustering, not final verdicts.
- `coordinate_audit.md`: source eligibility and extraction quality.
- `debug_candidates.json`: suppressed geometry and debug-only clashes.
