# Technical Coordination Report - SERENA 18 — registro provisional de niveles para coordinacion 2.5D

- Root: `C:/Users/Enrique Casanova/Dupla/repositorios/SERENA 18`
- Profile: `fast_compare`
- Status: `completed`
- Generated: `2026-05-02T12:49:40.059323+00:00`

## Executive Summary
- Scheduled pairs reviewed: `2` across `3` source files.
- Defendable findings today: `6` of `53` primary incidents.
- Technical noise held outside the main report: `179` debug conflicts and `596` suppressed elements.
- Confidence mix on primary incidents: low=47, medium=6.

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
| `incident_0026` | P2 | high | medium | `NPT_P1` | ARQUITECTURA / ESTRUCTURA | NPT_P1; (168,817,815, 624,648,464) mm | Arquitectura + Estructura | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego escalar en la siguiente ronda de coordinacion. |
| `incident_0021` | P2 | high | medium | `NPT_P1` | ARQUITECTURA / ESTRUCTURA | NPT_P1; (168,812,817, 624,648,464) mm | Arquitectura + Estructura | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego escalar en la siguiente ronda de coordinacion. |
| `incident_0034` | P2 | high | medium | `NPT_P1` | ARQUITECTURA / ESTRUCTURA | NPT_P1; (168,832,736, 624,649,470) mm | Arquitectura + Estructura | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego escalar en la siguiente ronda de coordinacion. |
| `incident_0051` | P2 | high | medium | `NPT_P1` | ARQUITECTURA / ESTRUCTURA | NPT_P1; (168,826,979, 624,644,583) mm | Arquitectura + Estructura | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego escalar en la siguiente ronda de coordinacion. |
| `incident_0005` | P2 | high | medium | `NPT_P1` | ARQUITECTURA / ESTRUCTURA | NPT_P1; (168,802,950, 624,651,070) mm | Arquitectura + Estructura | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego escalar en la siguiente ronda de coordinacion. |
| `incident_0035` | P2 | medium | medium | `NPT_P1` | ARQUITECTURA / ESTRUCTURA | NPT_P1; (168,833,404, 624,651,010) mm | Arquitectura + Estructura | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |

## Findings Requiring Manual Validation
| ID | Reason | Level | Layers | Suggested handling |
| --- | --- | --- | --- | --- |
| `incident_0029` | low confidence signal | `NPT_P1` | `MARCO / EST_PROYECCION` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |
| `incident_0020` | low confidence signal | `NPT_P1` | `MARCO / EST - EJE DE VIGA` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |
| `incident_0017` | low confidence signal | `NPT_P1` | `MARCO / piso` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |
| `incident_0008` | low confidence signal | `NPT_P1` | `MARCO / EST - BORDE INTERIOR` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |
| `incident_0016` | low confidence signal | `NPT_P1` | `MARCO / EST - BORDE INTERIOR` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |
| `incident_0022` | low confidence signal | `NPT_P1` | `MARCO / EST - BORDE EXTERIOR` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |
| `incident_0024` | low confidence signal | `NPT_P1` | `MARCO / piso` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |
| `incident_0039` | low confidence signal | `NPT_P1` | `MARCO / ESCALA_HUMANA` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |
| `incident_0003` | low confidence signal | `NPT_P1` | `MARCO / EST. MADERA` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |
| `incident_0036` | low confidence signal | `NPT_P1` | `MARCO / EST. MUROS DE BLOQUE BAJO NIVEL DE PISO` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |
| `incident_0045` | low confidence signal | `NPT_P1` | `MARCO / EST.  COLUMNAS` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |
| `incident_0015` | low confidence signal | `NPT_P1` | `MARCO / EST - EJE DE VIGA` | Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada. |

## Reader Sections

### Arquitectura
- Coverage in this run: `direct`
- Current focus: review top defendable conflicts first

| ID | Priority | Level | Pair | Why this reader should care |
| --- | --- | --- | --- | --- |
| `incident_0026` | P2 | `NPT_P1` | `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg` | una decision arquitectonica puede crear o resolver un conflicto estructural |
| `incident_0021` | P2 | `NPT_P1` | `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg` | una decision arquitectonica puede crear o resolver un conflicto estructural |
| `incident_0034` | P2 | `NPT_P1` | `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg` | una decision arquitectonica puede crear o resolver un conflicto estructural |
| `incident_0051` | P2 | `NPT_P1` | `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg` | una decision arquitectonica puede crear o resolver un conflicto estructural |
| `incident_0005` | P2 | `NPT_P1` | `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg` | una decision arquitectonica puede crear o resolver un conflicto estructural |
| `incident_0029` | P2 | `NPT_P1` | `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg` | la geometria arquitectonica o la reserva espacial estan implicadas |
| `incident_0020` | P2 | `NPT_P1` | `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg` | la geometria arquitectonica o la reserva espacial estan implicadas |
| `incident_0017` | P2 | `NPT_P1` | `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg` | la geometria arquitectonica o la reserva espacial estan implicadas |

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
| `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg` | 36 | 253 | P2 | low=23, medium=9, high=4 | low=31, medium=5 |
| `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg` | 17 | 70 | P2 | low=13, medium=3, high=1 | low=16, medium=1 |

## Noise and Technical Support
- Debug conflicts kept outside the executive list: `179`.
- Suppressed geometry count: `596`; main reasons: bounds_fallback=430, container_bbox=166.
- Audit status mix: eligible=3.
- Unscheduled or blocked pairs: `0`; main reasons: none.
- Hotspots are kept as concentration zones only: `162` grouped cases.

## Output Files
- `technical_coordination_report.md`: executive and interdisciplinary reading.
- `primary_incidents.md`: defendable incident register with pair-level detail.
- `hotspot_incidents.md`: concentration zones and technical clustering, not final verdicts.
- `coordinate_audit.md`: source eligibility and extraction quality.
- `debug_candidates.json`: suppressed geometry and debug-only clashes.
