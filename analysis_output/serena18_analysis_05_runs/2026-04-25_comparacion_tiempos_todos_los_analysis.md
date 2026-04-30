# SERENA 18 - Comparacion de Tiempos de Todos los Analysis

- Fecha: `2026-04-25`
- Proyecto: `SERENA 18`
- Alcance: comparacion de tiempos persistidos para los runs `analysis_01` a `analysis_05`

## Nota importante

- `analysis_01_core_mixed`
- `analysis_01_latest_mixed`
- `analysis_02_core_mixed_native`

No dejaron un `summary.json` con tiempos por etapa, asi que no se pueden comparar con el mismo nivel de detalle que `analysis_03` a `analysis_05`.

## Runs con tiempos persistidos

| Run | Estado | Audit (s) | Schedule (s) | Extract (s) | Clash (s) | Total (s) | Pares programados | Incidencias primarias |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `analysis_03_coordinate_audit_arq_est` | `no_scheduled_pairs` | `2.619` | `0.000` | `0.000` | `0.000` | `2.619` | `0` | `0` |
| `analysis_03_speed_probe` | `no_scheduled_pairs` | `249.181` | `0.001` | `0.000` | `0.000` | `249.182` | `0` | `0` |
| `analysis_03_speed_probe_isolated` | `no_scheduled_pairs` | `2.927` | `0.001` | `0.000` | `0.000` | `2.928` | `0` | `0` |
| `analysis_04_dominant_cluster` | `no_scheduled_pairs` | `2.420` | `0.000` | `0.000` | `0.000` | `2.420` | `0` | `0` |
| `analysis_05_manual_alignment` | `completed` | `0.639` | `0.000` | `8.654` | `0.401` | `9.694` | `2` | `53` |
| `analysis_05_NPT_P1` | `completed` | `0.889` | `0.000` | `9.688` | `0.387` | `10.964` | `2` | `53` |
| `analysis_05_NPT_P2` | `completed` | `0.708` | `0.000` | `7.600` | `0.758` | `9.066` | `3` | `66` |
| `analysis_05_CIMENTACION` | `completed` | `64.791` | `0.000` | `6.311` | `0.368` | `71.470` | `2` | `1` |
| `analysis_05_SOTANO` | `completed` | `33.700` | `0.000` | `5.239` | `0.384` | `39.323` | `2` | `0` |
| `analysis_05_TECHO` | `completed` | `2735.744` | `0.001` | `16.952` | `1.928` | `2754.625` | `4` | `108` |

## Lectura rapida

- El run mas lento fue `analysis_05_TECHO` con `2754.625 s`.
  - completo si produjo resultado, pero con una auditoria fria extraordinariamente costosa.

- Entre los runs que si completaron extraccion y clash, el mas rapido sigue siendo `analysis_05_NPT_P2` con `9.066 s`.

- `analysis_05_CIMENTACION` y `analysis_05_SOTANO` ya corrieron, pero fueron bastante mas lentos en audit que `NPT_P1/NPT_P2`.
  - `CIMENTACION`: `71.470 s`
  - `SOTANO`: `39.323 s`

- En los runs que completaron clash, el cuello de botella normalmente sigue siendo `extract`.
  - `analysis_05_manual_alignment`: `8.654 s` de `9.694 s`
  - `analysis_05_NPT_P1`: `9.688 s` de `10.964 s`
  - `analysis_05_NPT_P2`: `7.600 s` de `9.066 s`
  - `analysis_05_TECHO` es la excepcion: ahi el cuello de botella fue claramente `audit`

- `analysis_04_dominant_cluster` es el mas rapido de los runs serios de comparabilidad sin alineacion, con `2.420 s`, pero termino en `0` pares programados.

## Comparacion util por tipo de run

### Solo audit / scheduler

- `analysis_04_dominant_cluster`: `2.420 s`
- `analysis_03_coordinate_audit_arq_est`: `2.619 s`
- `analysis_03_speed_probe_isolated`: `2.928 s`
- `analysis_03_speed_probe`: `249.182 s`

### Runs completos con clash

- `analysis_05_NPT_P2`: `9.066 s`
- `analysis_05_manual_alignment`: `9.694 s`
- `analysis_05_NPT_P1`: `10.964 s`
- `analysis_05_SOTANO`: `39.323 s`
- `analysis_05_CIMENTACION`: `71.470 s`
- `analysis_05_TECHO`: `2754.625 s`

## Conclusiones

- Si la comparabilidad ya esta resuelta y el set es pequeno, los runs `analysis_05_*` pueden quedar en el orden de `9-11 s`.
- Los nuevos niveles `CIMENTACION`, `SOTANO` y sobre todo `TECHO` muestran que ese tiempo solo aplica a cohortes pequenas y bien cacheadas.
- Si no hay pares programables, el pipeline actual corta rapido en ~`2.4-2.9 s` cuando el cache esta sano.
- `analysis_03_speed_probe` no debe usarse como referencia normal de operacion; sirve como probe frio historico, no como tiempo representativo.

## Referencias

- [analysis_05 runs](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs:1)
- [index general](C:/Users/Enrique Casanova/Dupla/analysis_output/2026-04-25_analysis_05_SERENA_18_runs_index.md:1)
