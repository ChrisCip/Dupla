# Prueba web 01 — análisis presupuesto Dupla vs PRES

- **Fecha de corrida:** 2026-04-06
- **Etiqueta de corrida:** `run_2026-04-06_151553`
- **Generado (Dupla):** `c:\Users\Enrique Casanova\Dupla\output\prueba_web_01\run_2026-04-06_151553\pdf_vision_complete\dupla_presupuesto_cad_pdf_vision.xlsx`
- **Referencia (PRES):** `c:\Users\Enrique Casanova\Dupla\PRES.xlsx`

## Contexto y limitaciones

- Proyecto **prueba_web_01** (sin relación con Giualca u otros).
- Generado con CAD fusionado BLCAD14001–14015 + visión GPT sobre el PDF batch.
- Excel principal: pdf_vision_complete/dupla_presupuesto_cad_pdf_vision.xlsx.

## Resumen ejecutivo

| Métrica | Generado | PRES (real) |
| --- | ---: | ---: |
| Partidas | 27 | 1565 |
| Capítulos (filas Nat) | 26 | 296 |
| Códigos coincidentes | 1 | — |
| Cobertura códigos PRES con equivalente generado | 0.40% | — |
| Precisión cantidad (solo códigos coincidentes) | 0.00% | — |
| Precisión precio unitario (solo coincidentes) | 0.00% | — |
| Suma Importe (ImpPres) | 0.00 | 4,404,786.41 |
| Delta (generado − real) | -4,404,786.41 | — |

### Completitud de precios en generado

- Filas partida con PrPres > 0: **23** / 27
- Filas partida con ImpPres > 0: **0** / 27

## Disciplinas (heurística por texto del resumen)

- Etiquetas presentes en PRES y no detectadas en generado: **acero_refuerzo, ebanisteria, electrico, equipos_electricos, herreria, miscelaneos, movimiento_tierra, muros_divisiones, panete_revestimiento, preliminares, sanitario, techos_cubierta**

## Mayores diferencias de importe (códigos en ambos)

| Código | ImpPres real | ImpPres gen | Delta | Cant. real | Cant. gen | Resumen (PRES) |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| P030322 | 0.00 | 0.00 | 0.00 | 0.0 | 0.448 | Columna C3  0.80 x 0.50 - 20 Ø1", 3 Est Ø3/8"@0.10 |

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
- … y **169** más.

## Códigos solo en generado (no están en PRES)

- `DUP-0001`
- `DUP-0002`
- `DUP-0003`
- `DUP-0004`
- `H0402200`
- `H0502195`
- `H0502291`
- `H08P1010`
- `H140900`
- `H4005078`
- `M0811170`
- `M1602008`
- `P0303105`

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
