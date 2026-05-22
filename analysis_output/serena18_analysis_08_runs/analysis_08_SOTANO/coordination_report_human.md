# Coordination Report Human - SERENA 18 — registro provisional de niveles para coordinacion 2.5D

- Run: `analysis_08_SOTANO`
- Generated: `2026-05-05T22:55:52.054474+00:00`
- Status: `completed`

## Resumen ejecutivo
- Se revisaron `2` pares comparativos sobre `3` archivos fuente.
- El run consolidó `0` hallazgos defendibles y `0` casos que requieren validación manual.
- La salida técnica separó `429` conflictos debug y `748` elementos suprimidos fuera del mensaje principal.

## Que se comparó y por que si fue comparable
- El readiness documental no fue suficiente por sí solo para explicar la comparabilidad real del run.
- El coordinate audit confirmó archivos `eligible`, nivel canónico común y bandas de coordenadas compatibles, lo que habilitó pares útiles para clash 2.5D.

| Pair | Selection reason | Levels | Score |
| --- | --- | --- | ---: |
| `2208-Serena18-ID-Base.dwg vs EST. SERENA 18 - E05 - PLANTA EST. CIMIENTOS Y DETALLES  SOTANO.dwg` | `same_cohort_schedule` | `SOTANO / SOTANO` | 1.000 |
| `2208-Serena18-ID-Base.dwg vs EST. SERENA 18 - E08 - PLANTA EST. LOSAS DE TECHO SOTANO Y DETALLES.dwg` | `same_cohort_schedule` | `SOTANO / SOTANO` | 1.000 |

| File | Discipline | Level | Status | Coordinate band |
| --- | --- | --- | --- | --- |
| `2208-Serena18-ID-Base.dwg` | ARQUITECTURA | `SOTANO` | `eligible` | `X~168.81M, Y~624.64M` |
| `EST. SERENA 18 - E05 - PLANTA EST. CIMIENTOS Y DETALLES  SOTANO.dwg` | ESTRUCTURA | `SOTANO` | `eligible` | `X~168.82M, Y~624.63M` |
| `EST. SERENA 18 - E08 - PLANTA EST. LOSAS DE TECHO SOTANO Y DETALLES.dwg` | ESTRUCTURA | `SOTANO` | `eligible` | `X~168.81M, Y~624.65M` |

## Hallazgos defendibles
- No hubo hallazgos defendibles en esta corrida.

## Casos que requieren validacion manual
- No quedaron incidencias abiertas para validación manual.

## Lectura por perfil
- Arquitectura: `direct`
- Electrico: `not_in_run`
- Sanitario: `not_in_run`

## Ruido tecnico y limites del run
- Debug conflicts: `429`
- Hotspots agrupados: `0`
- Blocked pairs: `0`
- Este reporte no eleva nombres de elementos constructivos reales si no existe mapeo semántico confiable.

## Proximos pasos
- Mantener el coordinate audit como criterio superior cuando la cohorte documental no capture comparabilidad real.
- Priorizar revisión interdisciplinaria sobre los hallazgos defendibles antes de reinterpretar ruido técnico.
- Preparar una fase posterior de `clash -> elemento semantico` si entra un inventario DWG con geometría utilizable.
