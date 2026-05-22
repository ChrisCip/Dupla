# Coordination Report Human - SERENA 18 — registro provisional de niveles para coordinacion 2.5D

- Run: `analysis_08_CIMENTACION`
- Generated: `2026-05-05T22:54:39.218310+00:00`
- Status: `completed`

## Resumen ejecutivo
- Se revisaron `2` pares comparativos sobre `3` archivos fuente.
- El run consolidó `1` hallazgos defendibles y `0` casos que requieren validación manual.
- La salida técnica separó `706` conflictos debug y `635` elementos suprimidos fuera del mensaje principal.

## Que se comparó y por que si fue comparable
- El readiness documental no fue suficiente por sí solo para explicar la comparabilidad real del run.
- El coordinate audit confirmó archivos `eligible`, nivel canónico común y bandas de coordenadas compatibles, lo que habilitó pares útiles para clash 2.5D.

| Pair | Selection reason | Levels | Score |
| --- | --- | --- | ---: |
| `2208-Serena18-ID-Base.dwg vs EST. SERENA 18 - E04 - PLANTA GENERAL DE CIMIENTOS.dwg` | `same_cohort_schedule` | `CIMENTACION / CIMENTACION` | 1.000 |
| `2208-Serena18-ID-Base.dwg vs EST. SERENA 18 - E06 - PLANTA EST. CIMIENTOS Y DETALLES  CASA.dwg` | `same_cohort_schedule` | `CIMENTACION / CIMENTACION` | 1.000 |

| File | Discipline | Level | Status | Coordinate band |
| --- | --- | --- | --- | --- |
| `2208-Serena18-ID-Base.dwg` | ARQUITECTURA | `CIMENTACION` | `eligible` | `X~168.80M, Y~624.63M` |
| `EST. SERENA 18 - E04 - PLANTA GENERAL DE CIMIENTOS.dwg` | ESTRUCTURA | `CIMENTACION` | `eligible` | `X~168.80M, Y~624.62M` |
| `EST. SERENA 18 - E06 - PLANTA EST. CIMIENTOS Y DETALLES  CASA.dwg` | ESTRUCTURA | `CIMENTACION` | `eligible` | `X~168.81M, Y~624.64M` |

## Hallazgos defendibles
- `incident_0000` | `P2` | `medium` | `medium`
  nivel: `CIMENTACION`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `CIMENTACION; (168,816,577, 624,649,583) mm`
  evidencia: `I-FURN / Planos`
  accion: Revisar el par directamente y revisar con validacion acotada.

## Casos que requieren validacion manual
- No quedaron incidencias abiertas para validación manual.

## Lectura por perfil
- Arquitectura: `direct`
- Electrico: `not_in_run`
- Sanitario: `not_in_run`

## Ruido tecnico y limites del run
- Debug conflicts: `706`
- Hotspots agrupados: `445`
- Blocked pairs: `0`
- Este reporte no eleva nombres de elementos constructivos reales si no existe mapeo semántico confiable.

## Proximos pasos
- Mantener el coordinate audit como criterio superior cuando la cohorte documental no capture comparabilidad real.
- Priorizar revisión interdisciplinaria sobre los hallazgos defendibles antes de reinterpretar ruido técnico.
- Preparar una fase posterior de `clash -> elemento semantico` si entra un inventario DWG con geometría utilizable.
