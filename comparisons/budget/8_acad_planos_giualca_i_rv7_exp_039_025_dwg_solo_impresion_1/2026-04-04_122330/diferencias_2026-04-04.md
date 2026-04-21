# Comparación presupuesto — 8- ACAD-PLANOS GIUALCA I - RV7 - EXP.039-025.dwg SOLO IMPRESION (1)

- **Fecha de corrida:** 2026-04-04
- **Etiqueta de corrida:** `2026-04-04_122330`
- **Generado (Dupla):** `C:\Users\Enrique Casanova\Dupla\comparisons\budget\8_acad_planos_giualca_i_rv7_exp_039_025_dwg_solo_impresion_1\2026-04-04_122330\dupla_presupuesto_generado.xlsx`
- **Referencia (PRES):** `C:\Users\Enrique Casanova\Dupla\comparisons\budget\8_acad_planos_giualca_i_rv7_exp_039_025_dwg_solo_impresion_1\2026-04-04_122330\PRES_referencia.xlsx`

## Contexto y limitaciones

- **Modo de corrida:** solo extracción APS + reglas/cubicación sobre hechos CAD; **sin** análisis GPT-4o por imágenes (no se pasó PDF/planos raster en esta corrida).
- El PRES se usó como fuente de *few-shot* para el matcher BC3 cuando la plantilla es legible por `extract_training_pairs`.
- Los totales pueden diferir fuerte si el PRES incluye capítulos no inferibles solo desde el DWG arquitectónico.

## Resumen ejecutivo

| Métrica | Generado | PRES (real) |
| --- | ---: | ---: |
| Partidas | 6 | 1565 |
| Capítulos (filas Nat) | 10 | 296 |
| Códigos coincidentes | 2 | — |
| Cobertura códigos PRES con equivalente generado | 0.80% | — |
| Precisión cantidad (solo códigos coincidentes) | 0.00% | — |
| Precisión precio unitario (solo coincidentes) | 0.00% | — |
| Suma Importe (ImpPres) | 0.00 | 4,404,786.41 |
| Delta (generado − real) | -4,404,786.41 | — |

### Completitud de precios en generado

- Filas partida con PrPres > 0: **6** / 6
- Filas partida con ImpPres > 0: **0** / 6

## Disciplinas (heurística por texto del resumen)

- Etiquetas presentes en PRES y no detectadas en generado: **acero_refuerzo, ebanisteria, electrico, equipos_electricos, escaleras, herreria, impermeabilizacion, miscelaneos, movimiento_tierra, pisos, preliminares, puertas, sanitario, techos_cubierta, ventanas**

## Mayores diferencias de importe (códigos en ambos)

| Código | ImpPres real | ImpPres gen | Delta | Cant. real | Cant. gen | Resumen (PRES) |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| P0501101 | 1,500.91 | 0.00 | -1,500.91 | 178.68 | 22893.95359999995 | Pañete en muros Interiores e=1.75cm |
| P1801101 | 839.39 | 0.00 | -839.39 | 192.08 | 22893.95359999995 | Pintura Acrílica Interior |

## Códigos solo en PRES (no aparecen en generado)

- `%MOELEC`
- `A.0040BP3`
- `A.0043AC`
- `A.0043BD3`
- `A.0043BD4`
- `A.0043BD6`
- `A.0045CPPR1`
- `A.0045CPPR15`
- `A.0045CPPR2`
- `A.0045CPPR3`
- `A.0050PPR1`
- `A.0050PPR3`
- `A.0050PPR3A`
- `A.0050PPR75`
- `A.0055DP2`
- `A.0055DP4`
- `A.0059`
- `A.0065`
- `A.0067`
- `A.0071`
- `A.0072`
- `A.0073`
- `A.0080`
- `A.0081`
- `A.0101`
- `A.0102`
- `A.0103`
- `A.0105`
- `A.0150`
- `A.0162`
- `A.0163`
- `A.0164`
- `A.0164.1`
- `A.0165`
- `A.0166`
- `A.0167`
- `A.0175`
- `A.0177`
- `A.0180`
- `A.0188`
- `A.0192`
- `A.0202A`
- `A.02103`
- `A.02104`
- `A.02106`
- `A.02107`
- `A.0210PVC2`
- `A.0210PVC3`
- `A.0210PVC4`
- `A.0215APVC2.1`
- `A.0215APVC3`
- `A.0215APVC4`
- `A.0215APVC6`
- `A.0228`
- `A.0240`
- `A.0241`
- `A.0243`
- `A.0263`
- `A.0301`
- `A.0302`
- `A.0304`
- `AC1123`
- `BOMB2`
- `BOTIMB`
- `BoteMat`
- `CAL`
- `CD3`
- `DENSG`
- `DENSG2`
- `DESR`
- `DUCH`
- `EI02.01.01`
- `EI02.01.02`
- `EI02.01.03`
- `EI02.01.04`
- `EI02.01.05`
- `EI02.01.06`
- `EI02.01.07`
- `EI02.01.08`
- `EI02.01.09`
- … y **168** más.

## Códigos solo en generado (no están en PRES)

- `H0502195`
- `M040108`

## Top 20 partidas PRES por importe vs generado

- **P32011000**: real **250,100.00** — generado _no encontrado_ — Suministro - Instalacion Ascensor 6 Pasajeros
- **P0303150**: real **75,044.67** — generado _no encontrado_ — Zapata Z5 (21.80 x 6.85) e=1.20 Ø1"@0.10 Inf - Ø3/4"@0.10 Sup
- **P0100015**: real **49,602.14** — generado _no encontrado_ — Winche de Plataforma Electrico (2,200 lb)
- **EI02.02.01**: real **41,772.00** — generado _no encontrado_ — Generador electrico similar a Caterpillar 225 kW, 3f,
- **P3201300**: real **39,682.54** — generado _no encontrado_ — Estructura Metalica en Fachada Frontal
- **P01121002**: real **36,305.52** — generado _no encontrado_ — DIAS/H Subida y Acarreo Interno de Materiales
- **P0303590**: real **36,048.78** — generado _no encontrado_ — Losa Aligerada H.A. e=0.28m
- **P0303591**: real **34,610.72** — generado _no encontrado_ — Losa Aligerada H.A. e=0.28m
- **P0303595**: real **33,413.30** — generado _no encontrado_ — Losa Aligerada H.A. e=0.25m
- **P0203010**: real **33,259.23** — generado _no encontrado_ — Extraccion y bote de Mat de excavacion
- **P0303163**: real **32,685.17** — generado _no encontrado_ — Muro de Contención 0.20m Ø1/2"@0.20 Vert-AC, Ø3/8"@0.20 Hor-AC
- **SAN02.1**: real **32,497.18** — generado _no encontrado_ — Construcción de Septico
- **P0303595**: real **30,669.58** — generado _no encontrado_ — Losa Aligerada H.A. e=0.25m
- **P0303596**: real **24,135.04** — generado _no encontrado_ — Losa Aligerada H.A. e=0.25m N5
- **P0303596**: real **22,363.30** — generado _no encontrado_ — Losa Aligerada H.A. e=0.25m N5
- **P0303596**: real **22,363.30** — generado _no encontrado_ — Losa Aligerada H.A. e=0.25m N5
- **P0303596**: real **22,363.30** — generado _no encontrado_ — Losa Aligerada H.A. e=0.25m N5
- **P0303596**: real **22,363.30** — generado _no encontrado_ — Losa Aligerada H.A. e=0.25m N5
- **P0303596**: real **22,363.30** — generado _no encontrado_ — Losa Aligerada H.A. e=0.25m N5
- **P0303596**: real **21,821.93** — generado _no encontrado_ — Losa Aligerada H.A. e=0.25m N5
