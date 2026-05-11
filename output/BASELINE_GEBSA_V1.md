# BASELINE GEBSA IV - V1

Comparacion automatica del output del pipeline Dupla contra el BC3 real de GEBSA IV.
Matching por similitud de descripcion + unidad compatible (no por codigo).

## Fuentes

- **Real:** `data/GIV00001 (1).bc3` (604 partidas con precio > 0)
- **Output:**
  - `C:/Users/chris/Downloads/dupla1/20260425_094350_residencial_gebsa_iv/arquitectura/presupuesto_arquitectura.bc3`
  - `C:/Users/chris/Downloads/dupla1/20260425_094350_residencial_gebsa_iv/estructura/presupuesto_estructura.bc3`
  - `C:/Users/chris/Downloads/dupla1/20260425_094350_residencial_gebsa_iv/electrico/presupuesto_electrico.bc3`
  - `C:/Users/chris/Downloads/dupla1/20260425_094350_residencial_gebsa_iv/sanitario/presupuesto_sanitario.bc3`
- **Threshold de similitud:** 0.35

## Cobertura

| Metrica | Valor |
|---|---:|
| Partidas output | 240 |
| Partidas real | 604 |
| Matcheadas | 69 (11.4% del real) |
| Solo en output | 171 |
| Solo en real | 535 |

## Precision de precios (sobre matcheadas)

| Banda | Partidas | % |
|---|---:|---:|
| Dentro de +/-10% | 1 | 1.4% |
| Dentro de +/-25% | 3 | 4.3% |
| Dentro de +/-50% | 8 | 11.6% |
| Fuera de +/-50% | 61 | 88.4% |

## Precision de cantidades (sobre 69 matcheadas con qty>0)

| Banda | Partidas | % |
|---|---:|---:|
| Dentro de +/-10% | 9 | 13.0% |
| Dentro de +/-25% | 11 | 15.9% |
| Dentro de +/-50% | 14 | 20.3% |
| Fuera de +/-50% | 55 | 79.7% |

## Top 10 partidas con mayor delta de importe

| # | Score | Descripcion (real) | Output (p x q) | Real (p x q) | Delta |
|---:|---:|---|---|---|---:|
| 1 | 0.54 | M.O. pañete muro Interior | 4,659.83 x 18,641.39 m2 | 140.00 x 1.00 m² | 86,865,577.68 |
| 2 | 0.54 | M.O. pañete muro Exterior | 4,659.83 x 18,641.39 m2 | 175.00 x 1.00 m² | 86,865,542.68 |
| 3 | 0.44 | Muro bloques 15x20x40 SNP Ø3/8"@60 sin MO | 2,945.55 x 5,329.26 m2 | 1,105.08 x 4.00 m² | 15,693,172.64 |
| 4 | 0.48 | Muro Bloques 15x20x40 BNP Sin MO | 4,659.83 x 3,334.40 m2 | 804.68 x 1.92 m² | 15,536,178.19 |
| 5 | 0.50 | Muro Bloques 20x20x40 MR-2 | 4,659.83 x 3,334.40 m2 | 1,685.96 x 324.89 m² | 14,989,971.63 |
| 6 | 0.42 | Muro Bloques 20x20x40 SNP Ø3/8"@40 + 2Ø3/8"@0.60 | 2,945.55 x 5,329.26 m2 | 2,015.86 x 1,025.97 m² | 13,629,381.07 |
| 7 | 0.46 | M.O. Encofrado Muro HA TC 2C | 4,659.83 x 1,435.45 m2 | 750.00 x 1.00 m² | 6,688,221.61 |
| 8 | 0.48 | Muro de Escalera H.A. e=0.15m | 4,659.83 x 1,398.10 m3 | 41,943.84 x 0.38 m³ | 6,498,988.30 |
| 9 | 0.45 | Muro Bloques 15x20x40 BNP Ø3/8"@20 | 4,659.83 x 1,258.29 m2 | 1,643.48 x 22.27 m² | 5,826,798.55 |
| 10 | 0.45 | Muro Bloques 15x20x40 SNP Ø3/8"@40 | 4,659.83 x 1,435.45 m2 | 1,266.35 x 742.33 m² | 5,748,922.02 |

## Solo en output (primeras 20)

- [arquitectura] Muro tipo json-wall-muross (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-muro (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-muros (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-cocina (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-mb3 (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-mb (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-closet (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-escalera (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-a-genm (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-vuelo (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-targeta (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-tarjeta2 (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-1 (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-hoja (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-0 (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-mverde (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-vuelos (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-cristal (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-grdutiy (`m3` @ 4,659.83)
- [arquitectura] Muro tipo json-wall-relleno (`m3` @ 4,659.83)

