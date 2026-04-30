# SERENA 18 - analysis_05_TECHO

- Fecha: `2026-04-25`
- Proyecto: `SERENA 18`
- Nivel: `TECHO`
- Estado: `completed`

## Resumen

- `7` archivos seleccionados
- `4` pares programados
- `1750` elementos 2.5D
- `108` incidencias primarias
- `842` debug

## Lectura

`TECHO` es el run nuevo con mejor senal util despues de `NPT_P1` y `NPT_P2`.

- pares programados:
  - `UpperFloor` vs `E14`
  - `UpperFloor` vs `E15`
  - `UpperFloor` vs `E16`
  - `UpperFloor` vs `E19`
- archivos no programados por `extract_failed`:
  - `E17`
  - `E18`

Pares dominantes en incidencias primarias:

- `UpperFloor` vs `E14`: `39`
- `UpperFloor` vs `E19`: `39`
- `UpperFloor` vs `E16`: `30`
- `UpperFloor` vs `E15`: `21`

La geometria util quedo mayormente en `polyline / line` y `polyline / polyline`, con confianza `high`. Si es un resultado presentable.

## Nota operativa

La auditoria de `TECHO` fue muy costosa y duro mucho mas que los otros runs del grupo. El pipeline si termino y escribio todos los artefactos, aunque el shell de ejecucion agoto su timeout despues.

## Archivos de apoyo

- [summary.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_TECHO/summary.json:1)
- [primary_incidents.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_TECHO/primary_incidents.md:1)
- [pair_schedule.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_TECHO/pair_schedule.json:1)
