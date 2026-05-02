# Coordination Report Human - SERENA 18 — registro provisional de niveles para coordinacion 2.5D

- Run: `analysis_06`
- Generated: `2026-05-02T12:49:40.059323+00:00`
- Status: `completed`

## Resumen ejecutivo
- Se revisaron `2` pares comparativos sobre `3` archivos fuente.
- El run consolidó `6` hallazgos defendibles y `47` casos que requieren validación manual.
- La salida técnica separó `179` conflictos debug y `596` elementos suprimidos fuera del mensaje principal.

## Que se comparó y por que si fue comparable
- El readiness documental no fue suficiente por sí solo para explicar la comparabilidad real del run.
- El coordinate audit confirmó archivos `eligible`, nivel canónico común y bandas de coordenadas compatibles, lo que habilitó pares útiles para clash 2.5D.

| Pair | Selection reason | Levels | Score |
| --- | --- | --- | ---: |
| `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg` | `promoted_from_coordinate_audit` | `NPT_P1 / NPT_P1` | 0.850 |
| `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg` | `promoted_from_coordinate_audit` | `NPT_P1 / NPT_P1` | 0.850 |

| File | Discipline | Level | Status | Coordinate band |
| --- | --- | --- | --- | --- |
| `Serena 18 -PLANTA PISOS 10-10-2022.dwg` | ARQUITECTURA | `NPT_P1` | `eligible` | `X~168.82M, Y~624.64M` |
| `EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg` | ESTRUCTURA | `NPT_P1` | `eligible` | `X~168.81M, Y~624.65M` |
| `EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg` | ESTRUCTURA | `NPT_P1` | `eligible` | `X~168.82M, Y~624.64M` |

## Hallazgos defendibles
- `incident_0026` | `P2` | `high` | `medium`
  nivel: `NPT_P1`
  disciplinas: `ARQUITECTURA / ESTRUCTURA`
  ubicacion: `NPT_P1; (168,817,815, 624,648,464) mm`
  layers: `MARCO / EST_PROYECCION`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego escalar en la siguiente ronda de coordinacion.
- `incident_0021` | `P2` | `high` | `medium`
  nivel: `NPT_P1`
  disciplinas: `ARQUITECTURA / ESTRUCTURA`
  ubicacion: `NPT_P1; (168,812,817, 624,648,464) mm`
  layers: `MARCO / EST - BORDE EXTERIOR`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego escalar en la siguiente ronda de coordinacion.
- `incident_0034` | `P2` | `high` | `medium`
  nivel: `NPT_P1`
  disciplinas: `ARQUITECTURA / ESTRUCTURA`
  ubicacion: `NPT_P1; (168,832,736, 624,649,470) mm`
  layers: `MARCO / TITULOS`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego escalar en la siguiente ronda de coordinacion.
- `incident_0051` | `P2` | `high` | `medium`
  nivel: `NPT_P1`
  disciplinas: `ARQUITECTURA / ESTRUCTURA`
  ubicacion: `NPT_P1; (168,826,979, 624,644,583) mm`
  layers: `MARCO / EST_PROYECCION`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego escalar en la siguiente ronda de coordinacion.
- `incident_0005` | `P2` | `high` | `medium`
  nivel: `NPT_P1`
  disciplinas: `ARQUITECTURA / ESTRUCTURA`
  ubicacion: `NPT_P1; (168,802,950, 624,651,070) mm`
  layers: `Solares / EST. MADERA`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego escalar en la siguiente ronda de coordinacion.
- `incident_0035` | `P2` | `medium` | `medium`
  nivel: `NPT_P1`
  disciplinas: `ARQUITECTURA / ESTRUCTURA`
  ubicacion: `NPT_P1; (168,833,404, 624,651,010) mm`
  layers: `MUROS / TITULOS`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada.

## Casos que requieren validacion manual
- `incident_0029` | razon: low confidence signal
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  layers: `MARCO / EST_PROYECCION`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada.
- `incident_0020` | razon: low confidence signal
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  layers: `MARCO / EST - EJE DE VIGA`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada.
- `incident_0017` | razon: low confidence signal
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  layers: `MARCO / piso`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada.
- `incident_0008` | razon: low confidence signal
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  layers: `MARCO / EST - BORDE INTERIOR`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada.
- `incident_0016` | razon: low confidence signal
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  layers: `MARCO / EST - BORDE INTERIOR`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada.
- `incident_0022` | razon: low confidence signal
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  layers: `MARCO / EST - BORDE EXTERIOR`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada.
- `incident_0024` | razon: low confidence signal
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  layers: `MARCO / piso`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada.
- `incident_0039` | razon: low confidence signal
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg`
  layers: `MARCO / ESCALA_HUMANA`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada.
- `incident_0003` | razon: low confidence signal
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  layers: `MARCO / EST. MADERA`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada.
- `incident_0036` | razon: low confidence signal
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg`
  layers: `MARCO / EST. MUROS DE BLOQUE BAJO NIVEL DE PISO`
  accion: Validar si la geometria arquitectonica invade espacio estructural o si solo traza un contorno, y luego revisar con validacion acotada.

## Lectura por perfil
- Arquitectura: `direct`
- Electrico: `not_in_run`
- Sanitario: `not_in_run`

## Ruido tecnico y limites del run
- Debug conflicts: `179`
- Hotspots agrupados: `162`
- Blocked pairs: `0`
- Este reporte no eleva nombres de elementos constructivos reales si no existe mapeo semántico confiable.

## Proximos pasos
- Mantener el coordinate audit como criterio superior cuando la cohorte documental no capture comparabilidad real.
- Priorizar revisión interdisciplinaria sobre los hallazgos defendibles antes de reinterpretar ruido técnico.
- Preparar una fase posterior de `clash -> elemento semantico` si entra un inventario DWG con geometría utilizable.
