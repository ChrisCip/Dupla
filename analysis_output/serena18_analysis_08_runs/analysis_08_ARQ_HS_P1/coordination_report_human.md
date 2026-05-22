# Coordination Report Human - SERENA 18 — registro provisional de niveles para coordinacion 2.5D

- Run: `analysis_08_ARQ_HS_P1`
- Generated: `2026-05-05T23:00:04.453552+00:00`
- Status: `completed`

## Resumen ejecutivo
- Se revisaron `1` pares comparativos sobre `2` archivos fuente.
- El run consolidó `0` hallazgos defendibles y `0` casos que requieren validación manual.
- La salida técnica separó `66` conflictos debug y `167` elementos suprimidos fuera del mensaje principal.

## Que se comparó y por que si fue comparable
- El readiness documental no fue suficiente por sí solo para explicar la comparabilidad real del run.
- El coordinate audit confirmó archivos `eligible`, nivel canónico común y bandas de coordenadas compatibles, lo que habilitó pares útiles para clash 2.5D.

| Pair | Selection reason | Levels | Score |
| --- | --- | --- | ---: |
| `2208-Serena18-ID-Base.dwg vs 5.7.2025 SERENA 18 PLANOS AS-BUILT.dwg` | `same_cohort_schedule` | `NPT_P1 / NPT_P1` | 1.000 |

| File | Discipline | Level | Status | Coordinate band |
| --- | --- | --- | --- | --- |
| `2208-Serena18-ID-Base.dwg` | ARQUITECTURA | `NPT_P1` | `eligible` | `X~1.61M, Y~1.91M` |
| `5.7.2025 SERENA 18 PLANOS AS-BUILT.dwg` | FONTANERIA | `NPT_P1` | `eligible` | `X~1.61M, Y~1.91M` |

## Hallazgos defendibles
- No hubo hallazgos defendibles en esta corrida.

## Casos que requieren validacion manual
- No quedaron incidencias abiertas para validación manual.

## Lectura por perfil
- Arquitectura: `direct`
- Electrico: `not_in_run`
- Sanitario: `not_in_run`

## Ruido tecnico y limites del run
- Debug conflicts: `66`
- Hotspots agrupados: `0`
- Blocked pairs: `0`
- Este reporte no eleva nombres de elementos constructivos reales si no existe mapeo semántico confiable.

## Proximos pasos
- Mantener el coordinate audit como criterio superior cuando la cohorte documental no capture comparabilidad real.
- Priorizar revisión interdisciplinaria sobre los hallazgos defendibles antes de reinterpretar ruido técnico.
- Preparar una fase posterior de `clash -> elemento semantico` si entra un inventario DWG con geometría utilizable.
