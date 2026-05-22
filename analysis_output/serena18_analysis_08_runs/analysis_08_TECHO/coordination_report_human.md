# Coordination Report Human - SERENA 18 — registro provisional de niveles para coordinacion 2.5D

- Run: `analysis_08_TECHO`
- Generated: `2026-05-05T22:58:22.381782+00:00`
- Status: `completed`

## Resumen ejecutivo
- Se revisaron `6` pares comparativos sobre `7` archivos fuente.
- El run consolidó `131` hallazgos defendibles y `26` casos que requieren validación manual.
- La salida técnica separó `1262` conflictos debug y `1328` elementos suprimidos fuera del mensaje principal.

## Que se comparó y por que si fue comparable
- El readiness documental no fue suficiente por sí solo para explicar la comparabilidad real del run.
- El coordinate audit confirmó archivos `eligible`, nivel canónico común y bandas de coordenadas compatibles, lo que habilitó pares útiles para clash 2.5D.

| Pair | Selection reason | Levels | Score |
| --- | --- | --- | ---: |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg` | `same_cohort_schedule` | `TECHO / TECHO` | 1.000 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg` | `same_cohort_schedule` | `TECHO / TECHO` | 1.000 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg` | `same_cohort_schedule` | `TECHO / TECHO` | 1.000 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E17 - PLANTA EST.DE TECHOS T2 EN MADERA Y DETALLES - MOD, VIGAS VY-13, VY-26, VY-25.dwg` | `same_cohort_schedule` | `TECHO / TECHO` | 1.000 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E18 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. I).dwg` | `same_cohort_schedule` | `TECHO / TECHO` | 1.000 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E19 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. II).dwg` | `same_cohort_schedule` | `TECHO / TECHO` | 1.000 |

| File | Discipline | Level | Status | Coordinate band |
| --- | --- | --- | --- | --- |
| `2208-Serena18-ID-Base-UpperFloor.dwg` | ARQUITECTURA | `TECHO` | `eligible` | `X~168.83M, Y~624.67M` |
| `EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg` | ESTRUCTURA | `TECHO` | `eligible` | `X~168.83M, Y~624.67M` |
| `EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg` | ESTRUCTURA | `TECHO` | `eligible` | `X~168.83M, Y~624.67M` |
| `EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg` | ESTRUCTURA | `TECHO` | `eligible` | `X~168.83M, Y~624.67M` |
| `EST. SERENA 18 - E17 - PLANTA EST.DE TECHOS T2 EN MADERA Y DETALLES - MOD, VIGAS VY-13, VY-26, VY-25.dwg` | ESTRUCTURA | `TECHO` | `eligible` | `X~168.83M, Y~624.67M` |
| `EST. SERENA 18 - E18 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. I).dwg` | ESTRUCTURA | `TECHO` | `eligible` | `X~168.83M, Y~624.67M` |
| `EST. SERENA 18 - E19 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. II).dwg` | ESTRUCTURA | `TECHO` | `eligible` | `X~168.83M, Y~624.67M` |

## Hallazgos defendibles
- `incident_0076` | `P1` | `critical` | `high`
  nivel: `TECHO`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `TECHO; (168,841,135, 624,666,914) mm`
  evidencia: `I-FURN / PARCELS`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0036` | `P1` | `critical` | `high`
  nivel: `TECHO`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `TECHO; (168,835,779, 624,670,611) mm`
  evidencia: `I-FURN / Solares`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0043` | `P1` | `critical` | `high`
  nivel: `TECHO`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `TECHO; (168,839,897, 624,668,453) mm`
  evidencia: `I-FURN / plano 1`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0046` | `P1` | `critical` | `high`
  nivel: `TECHO`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `TECHO; (168,841,274, 624,666,898) mm`
  evidencia: `I-FURN / PARCELS`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0124` | `P1` | `critical` | `high`
  nivel: `TECHO`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `TECHO; (168,841,116, 624,666,915) mm`
  evidencia: `I-FURN / PARCELS`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0092` | `P1` | `critical` | `high`
  nivel: `TECHO`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `TECHO; (168,837,924, 624,669,135) mm`
  evidencia: `I-FLOR-FIN / Solares`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0091` | `P1` | `critical` | `high`
  nivel: `TECHO`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `TECHO; (168,837,924, 624,666,277) mm`
  evidencia: `I-FLOR-FIN / Solares`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0035` | `P1` | `critical` | `high`
  nivel: `TECHO`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `TECHO; (168,835,779, 624,663,350) mm`
  evidencia: `I-FURN / PARCELS`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0006` | `P1` | `critical` | `high`
  nivel: `TECHO`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `TECHO; (168,835,818, 624,663,352) mm`
  evidencia: `I-FURN / PARCELS`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0112` | `P1` | `critical` | `high`
  nivel: `TECHO`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `TECHO; (168,835,818, 624,663,352) mm`
  evidencia: `I-FURN / PARCELS`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.

## Casos que requieren validacion manual
- `incident_0016` | razon: line-based geometry needs manual confirmation
  nivel: `TECHO`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg`
  layers: `I-FLOR-FIN / PARCELS`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0122` | razon: line-based geometry needs manual confirmation
  nivel: `TECHO`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E18 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. I).dwg`
  layers: `I-FLOR-FIN / PARCELS`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0144` | razon: line-based geometry needs manual confirmation
  nivel: `TECHO`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E19 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. II).dwg`
  layers: `I-FLOR-FIN / PARCELS`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0079` | razon: line-based geometry needs manual confirmation
  nivel: `TECHO`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg`
  layers: `I-FURN / Solares`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0149` | razon: line-based geometry needs manual confirmation
  nivel: `TECHO`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E19 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. II).dwg`
  layers: `I-WALL / Solares`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0073` | razon: line-based geometry needs manual confirmation
  nivel: `TECHO`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg`
  layers: `I-WALL / Solares`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0028` | razon: line-based geometry needs manual confirmation
  nivel: `TECHO`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg`
  layers: `I-FURN / TITULOS`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0057` | razon: line-based geometry needs manual confirmation
  nivel: `TECHO`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg`
  layers: `I-FURN / TITULOS`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0085` | razon: line-based geometry needs manual confirmation
  nivel: `TECHO`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg`
  layers: `I-FURN / TITULOS`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0104` | razon: line-based geometry needs manual confirmation
  nivel: `TECHO`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E17 - PLANTA EST.DE TECHOS T2 EN MADERA Y DETALLES - MOD, VIGAS VY-13, VY-26, VY-25.dwg`
  layers: `I-FURN / TITULOS`
  accion: Revisar el par directamente y revisar con validacion acotada.

## Lectura por perfil
- Arquitectura: `direct`
- Electrico: `not_in_run`
- Sanitario: `not_in_run`

## Ruido tecnico y limites del run
- Debug conflicts: `1262`
- Hotspots agrupados: `769`
- Blocked pairs: `0`
- Este reporte no eleva nombres de elementos constructivos reales si no existe mapeo semántico confiable.

## Proximos pasos
- Mantener el coordinate audit como criterio superior cuando la cohorte documental no capture comparabilidad real.
- Priorizar revisión interdisciplinaria sobre los hallazgos defendibles antes de reinterpretar ruido técnico.
- Preparar una fase posterior de `clash -> elemento semantico` si entra un inventario DWG con geometría utilizable.
