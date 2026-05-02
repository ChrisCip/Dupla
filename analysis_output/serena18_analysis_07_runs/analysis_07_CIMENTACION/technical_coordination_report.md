# Technical Coordination Report - SERENA 18 — registro provisional de niveles para coordinacion 2.5D

- Root: `C:/Users/Enrique Casanova/Dupla/repositorios/SERENA 18`
- Profile: `fast_compare`
- Status: `completed`
- Generated: `2026-05-02T13:06:08.267622+00:00`

## Executive Summary
- Scheduled pairs reviewed: `2` across `3` source files.
- Defendable findings today: `1` of `1` primary incidents.
- Technical noise held outside the main report: `706` debug conflicts and `635` suppressed elements.
- Confidence mix on primary incidents: medium=1.

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
| `incident_0000` | P2 | medium | medium | `CIMENTACION` | Discipline.ARCH / Discipline.STRUC | CIMENTACION; (168,816,577, 624,649,583) mm | Discipline.Arch + Discipline.Struc | Revisar el par directamente y revisar con validacion acotada. |

## Findings Requiring Manual Validation
| ID | Reason | Level | Layers | Suggested handling |
| --- | --- | --- | --- | --- |
| - | No primary incidents fell into the manual-validation bucket. | - | - | - |

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
| `2208-Serena18-ID-Base.dwg vs EST. SERENA 18 - E06 - PLANTA EST. CIMIENTOS Y DETALLES  CASA.dwg` | 1 | 1 | P2 | medium=1 | medium=1 |

## Noise and Technical Support
- Debug conflicts kept outside the executive list: `706`.
- Suppressed geometry count: `635`; main reasons: bounds_fallback=467, container_bbox=168.
- Audit status mix: eligible=3.
- Unscheduled or blocked pairs: `0`; main reasons: none.
- Hotspots are kept as concentration zones only: `445` grouped cases.

## Output Files
- `technical_coordination_report.md`: executive and interdisciplinary reading.
- `primary_incidents.md`: defendable incident register with pair-level detail.
- `hotspot_incidents.md`: concentration zones and technical clustering, not final verdicts.
- `coordinate_audit.md`: source eligibility and extraction quality.
- `debug_candidates.json`: suppressed geometry and debug-only clashes.
