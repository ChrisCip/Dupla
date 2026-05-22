# Coordination Report Human - SERENA 18 — registro provisional de niveles para coordinacion 2.5D

- Run: `analysis_08_NPT_P2`
- Generated: `2026-05-05T22:52:37.861247+00:00`
- Status: `completed`

## Resumen ejecutivo
- Se revisaron `3` pares comparativos sobre `4` archivos fuente.
- El run consolidó `46` hallazgos defendibles y `20` casos que requieren validación manual.
- La salida técnica separó `769` conflictos debug y `823` elementos suprimidos fuera del mensaje principal.

## Que se comparó y por que si fue comparable
- El readiness documental no fue suficiente por sí solo para explicar la comparabilidad real del run.
- El coordinate audit confirmó archivos `eligible`, nivel canónico común y bandas de coordenadas compatibles, lo que habilitó pares útiles para clash 2.5D.

| Pair | Selection reason | Levels | Score |
| --- | --- | --- | ---: |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E10 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (1).dwg` | `same_cohort_schedule` | `NPT_P2 / NPT_P2` | 1.000 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg` | `same_cohort_schedule` | `NPT_P2 / NPT_P2` | 1.000 |
| `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg` | `same_cohort_schedule` | `NPT_P2 / NPT_P2` | 1.000 |

| File | Discipline | Level | Status | Coordinate band |
| --- | --- | --- | --- | --- |
| `2208-Serena18-ID-Base-UpperFloor.dwg` | ARQUITECTURA | `NPT_P2` | `eligible` | `X~168.82M, Y~624.56M` |
| `EST. SERENA 18 - E10 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (1).dwg` | ESTRUCTURA | `NPT_P2` | `eligible` | `X~168.82M, Y~624.56M` |
| `EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg` | ESTRUCTURA | `NPT_P2` | `eligible` | `X~168.82M, Y~624.56M` |
| `EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg` | ESTRUCTURA | `NPT_P2` | `eligible` | `X~168.82M, Y~624.56M` |

## Hallazgos defendibles
- `incident_0019` | `P1` | `critical` | `high`
  nivel: `NPT_P2`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `NPT_P2; (168,832,051, 624,560,950) mm`
  evidencia: `I-FURN / PARCELS`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0050` | `P1` | `critical` | `high`
  nivel: `NPT_P2`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `NPT_P2; (168,832,051, 624,560,950) mm`
  evidencia: `I-FURN / PARCELS`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0027` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `NPT_P2; (168,835,479, 624,569,513) mm`
  evidencia: `I-WALL / Solares`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0058` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `NPT_P2; (168,835,479, 624,569,513) mm`
  evidencia: `I-WALL / Solares`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0010` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `NPT_P2; (168,827,059, 624,562,963) mm`
  evidencia: `I-FURN / Solares`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0039` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `NPT_P2; (168,827,059, 624,562,963) mm`
  evidencia: `I-FURN / Solares`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0009` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `NPT_P2; (168,824,639, 624,568,338) mm`
  evidencia: `I-EQUIPMENT / Solares`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0036` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `NPT_P2; (168,824,639, 624,568,338) mm`
  evidencia: `I-EQUIPMENT / Solares`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0014` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `NPT_P2; (168,829,204, 624,563,188) mm`
  evidencia: `I-FLOR-FIN / Solares`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0045` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  disciplinas: `Discipline.ARCH / Discipline.STRUC`
  ubicacion: `NPT_P2; (168,829,204, 624,563,188) mm`
  evidencia: `I-FLOR-FIN / Solares`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.

## Casos que requieren validacion manual
- `incident_0023` | razon: line-based geometry needs manual confirmation
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg`
  layers: `I-FURN / ESCALA_HUMANA`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0054` | razon: line-based geometry needs manual confirmation
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg`
  layers: `I-FURN / ESCALA_HUMANA`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0028` | razon: line-based geometry needs manual confirmation
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg`
  layers: `I-FURN / ESCALA_HUMANA`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0059` | razon: line-based geometry needs manual confirmation
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg`
  layers: `I-FURN / ESCALA_HUMANA`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0029` | razon: line-based geometry needs manual confirmation
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg`
  layers: `2 / PARCELS`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0060` | razon: line-based geometry needs manual confirmation
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg`
  layers: `2 / PARCELS`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0012` | razon: line-based geometry needs manual confirmation
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg`
  layers: `I-FURN-RUGS / EST - ACERO`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0041` | razon: line-based geometry needs manual confirmation
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg`
  layers: `I-FURN-RUGS / EST - ACERO`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0043` | razon: line-based geometry needs manual confirmation
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg`
  layers: `I-WALL / plano 2`
  accion: Revisar el par directamente y revisar con validacion acotada.
- `incident_0032` | razon: line-based geometry needs manual confirmation
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg`
  layers: `I-MILLWORK / TITULOS`
  accion: Revisar el par directamente y revisar con validacion acotada.

## Lectura por perfil
- Arquitectura: `direct`
- Electrico: `not_in_run`
- Sanitario: `not_in_run`

## Ruido tecnico y limites del run
- Debug conflicts: `769`
- Hotspots agrupados: `494`
- Blocked pairs: `0`
- Este reporte no eleva nombres de elementos constructivos reales si no existe mapeo semántico confiable.

## Proximos pasos
- Mantener el coordinate audit como criterio superior cuando la cohorte documental no capture comparabilidad real.
- Priorizar revisión interdisciplinaria sobre los hallazgos defendibles antes de reinterpretar ruido técnico.
- Preparar una fase posterior de `clash -> elemento semantico` si entra un inventario DWG con geometría utilizable.
