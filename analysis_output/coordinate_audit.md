# Coordinate Audit - NASAS 09 — registro de niveles (cotas N extraídas del CAD normalizado)

- Root: `C:/Users/Enrique Casanova/Dupla/repositorios/SERENA 18`
- Files audited: 3
- Status mix: eligible=2, needs_alignment=1

## Reading Guide
- `eligible` can enter the scheduled clash flow.
- `needs_alignment`, `annotation_noise`, `bbox_only`, and `extract_failed` are technical blockers or low-trust inputs.

## Sources
| File | Discipline | Level | Drawing type | Status | Coordinate band | Raw primary | Raw annotation | Notes |
| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |
| `Serena 18 -PLANTA PISOS 10-10-2022.dwg` | ARQUITECTURA | `NPT_P1` | `floor_plan` | `needs_alignment` | `X~173.69M, Y~624.14M` | 10229 | 1207 | fuera de la banda dominante |
| `EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg` | ESTRUCTURA | `NPT_P1` | `formwork` | `eligible` | `X~168.81M, Y~624.65M` | 2178 | 306 | - |
| `EST. CASA SERENA  # 18 - E03 - PLANO DE ENCOFRADO.dwg` | ESTRUCTURA | `NPT_P1` | `formwork` | `eligible` | `X~168.81M, Y~624.65M` | 2186 | 305 | - |
