# Analysis 05 - SERENA 18 - Alineacion Manual ARQ vs EST

> Estado: este run queda reemplazado operativamente por [2026-04-25_analysis_05_NPT_P1_resultado.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_NPT_P1/2026-04-25_analysis_05_NPT_P1_resultado.md:1) como etiqueta formal `analysis_05_NPT_P1`.

- Fecha: `2026-04-25`
- Perfil: `fast_compare`
- Alcance: `ARQ P1 vs EST P1`

## Alineacion aplicada

Archivo alineado:

- `PLANOS RECIBIDOS/ARQUITECTONICOS/06. JUNIO 2024/Serena 18 -PLANTA PISOS 10-10-2022.dwg`

Transformacion manual aplicada:

- `translate_mm = (-4,871,358.9623, +500,416.0999)`

Criterio:

- llevar el cluster dominante del archivo arquitectonico al promedio de centroides dominantes de:
  - `EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  - `EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO Y DETALLES CASA.dwg`

## Resultado

- `3` archivos seleccionados
- `2` pares programados
- `1050` elementos 2.5D
- `53` incidencias primarias
- `179` conflictos debug
- `596` elementos suprimidos

## Pares con incidencias primarias

- `Serena 18 -PLANTA PISOS 10-10-2022.dwg` vs `EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  - `36` incidencias
  - `253` miembros agregados

- `Serena 18 -PLANTA PISOS 10-10-2022.dwg` vs `EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg`
  - `17` incidencias
  - `70` miembros agregados

## Lectura

- La alineacion manual desbloqueo el scheduler: pasamos de `0/45` pares programados a `2/2`.
- Ya no estamos en un caso de “no comparable”.
- El resultado sigue siendo de screening serio, no veredicto final BIM:
  - confianza dominante `medium`
  - mezcla fuerte de `polyline/polyline` y `polyline/line`
  - `179` casos quedaron en `debug`

## Archivos principales

- Resumen: [summary.json](C:/Users/Enrique%20Casanova/Dupla/analysis_output/serena18_analysis_05_manual_alignment/summary.json:1)
- Audit: [coordinate_audit.json](C:/Users/Enrique%20Casanova/Dupla/analysis_output/serena18_analysis_05_manual_alignment/coordinate_audit.json:1)
- Scheduler: [pair_schedule.json](C:/Users/Enrique%20Casanova/Dupla/analysis_output/serena18_analysis_05_manual_alignment/pair_schedule.json:1)
- Incidencias primarias: [primary_incidents.md](C:/Users/Enrique%20Casanova/Dupla/analysis_output/serena18_analysis_05_manual_alignment/primary_incidents.md:1)
- Alineacion usada: [alignment_manifest.json](C:/Users/Enrique%20Casanova/Dupla/analysis_output/serena18_analysis_05_manual_alignment/alignment_manifest.json:1)
