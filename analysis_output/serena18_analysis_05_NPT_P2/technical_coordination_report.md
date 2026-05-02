# Technical Coordination Report - SERENA 18 — registro provisional de niveles para coordinacion 2.5D

- Root: `C:/Users/Enrique Casanova/Dupla/repositorios/SERENA 18`
- Profile: `fast_compare`
- Status: `completed`
- Generated: `2026-04-25T03:36:44.740925+00:00`

## Executive Summary
- Scheduled pairs reviewed: `3` across `4` source files.
- Defendable findings today: `46` of `66` primary incidents.
- Technical noise held outside the main report: `769` debug conflicts and `823` suppressed elements.
- Confidence mix on primary incidents: medium=50, high=16.

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
| `incident_0019` | P1 | critical | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,832,051, 624,560,950) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |
| `incident_0050` | P1 | critical | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,832,051, 624,560,950) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |
| `incident_0027` | P1 | high | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,835,479, 624,569,513) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |
| `incident_0058` | P1 | high | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,835,479, 624,569,513) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |
| `incident_0010` | P1 | high | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,827,059, 624,562,963) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |
| `incident_0039` | P1 | high | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,827,059, 624,562,963) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |
| `incident_0009` | P1 | high | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,824,639, 624,568,338) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |
| `incident_0036` | P1 | high | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,824,639, 624,568,338) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |
| `incident_0014` | P1 | high | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,829,204, 624,563,188) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |
| `incident_0045` | P1 | high | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,829,204, 624,563,188) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |
| `incident_0020` | P1 | high | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,833,387, 624,563,658) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |
| `incident_0051` | P1 | high | high | `NPT_P2` | ARQUITECTURA / ESTRUCTURA | NPT_P2; (168,833,387, 624,563,658) mm | Arquitectura + Estructura | Validate whether the architectural geometry invades structural space or only traces a contour, then escalate in the next coordination round. |

## Findings Requiring Manual Validation
| ID | Reason | Level | Layers | Suggested handling |
| --- | --- | --- | --- | --- |
| `incident_0023` | line-based geometry needs manual confirmation | `NPT_P2` | `I-FURN / ESCALA_HUMANA` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |
| `incident_0054` | line-based geometry needs manual confirmation | `NPT_P2` | `I-FURN / ESCALA_HUMANA` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |
| `incident_0028` | line-based geometry needs manual confirmation | `NPT_P2` | `I-FURN / ESCALA_HUMANA` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |
| `incident_0059` | line-based geometry needs manual confirmation | `NPT_P2` | `I-FURN / ESCALA_HUMANA` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |
| `incident_0029` | line-based geometry needs manual confirmation | `NPT_P2` | `2 / PARCELS` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |
| `incident_0060` | line-based geometry needs manual confirmation | `NPT_P2` | `2 / PARCELS` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |
| `incident_0012` | line-based geometry needs manual confirmation | `NPT_P2` | `I-FURN-RUGS / EST - ACERO` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |
| `incident_0041` | line-based geometry needs manual confirmation | `NPT_P2` | `I-FURN-RUGS / EST - ACERO` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |
| `incident_0043` | line-based geometry needs manual confirmation | `NPT_P2` | `I-WALL / plano 2` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |
| `incident_0032` | line-based geometry needs manual confirmation | `NPT_P2` | `I-MILLWORK / TITULOS` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |
| `incident_0063` | line-based geometry needs manual confirmation | `NPT_P2` | `I-MILLWORK / TITULOS` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |
| `incident_0004` | line-based geometry needs manual confirmation | `NPT_P2` | `I-WALL / EST - EJE DE VIGA` | Validate whether the architectural geometry invades structural space or only traces a contour, then review with scoped validation. |

## Reader Sections

### Arquitectura
- Coverage in this run: `direct`
- Current focus: review top defendable conflicts first

| ID | Priority | Level | Pair | Why this reader should care |
| --- | --- | --- | --- | --- |
| `incident_0019` | P1 | `NPT_P2` | `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg` | architectural decision can create or resolve a structural conflict |
| `incident_0050` | P1 | `NPT_P2` | `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg` | architectural decision can create or resolve a structural conflict |
| `incident_0027` | P1 | `NPT_P2` | `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg` | architectural decision can create or resolve a structural conflict |
| `incident_0058` | P1 | `NPT_P2` | `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg` | architectural decision can create or resolve a structural conflict |
| `incident_0010` | P1 | `NPT_P2` | `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg` | architectural decision can create or resolve a structural conflict |
| `incident_0039` | P1 | `NPT_P2` | `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg` | architectural decision can create or resolve a structural conflict |
| `incident_0009` | P1 | `NPT_P2` | `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg` | architectural decision can create or resolve a structural conflict |
| `incident_0036` | P1 | `NPT_P2` | `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg` | architectural decision can create or resolve a structural conflict |

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
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg` | 31 | 115 | P1 | medium=13, low=9, high=8, critical=1 | medium=23, high=8 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg` | 27 | 102 | P1 | medium=10, high=8, low=8, critical=1 | medium=19, high=8 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E10 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (1).dwg` | 8 | 23 | P2 | medium=5, low=3 | medium=8 |

## Noise and Technical Support
- Debug conflicts kept outside the executive list: `769`.
- Suppressed geometry count: `823`; main reasons: bounds_fallback=713, container_bbox=110.
- Audit status mix: eligible=4.
- Unscheduled or blocked pairs: `0`; main reasons: none.
- Hotspots are kept as concentration zones only: `494` grouped cases.

## Output Files
- `technical_coordination_report.md`: executive and interdisciplinary reading.
- `primary_incidents.md`: defendable incident register with pair-level detail.
- `hotspot_incidents.md`: concentration zones and technical clustering, not final verdicts.
- `coordinate_audit.md`: source eligibility and extraction quality.
- `debug_candidates.json`: suppressed geometry and debug-only clashes.
