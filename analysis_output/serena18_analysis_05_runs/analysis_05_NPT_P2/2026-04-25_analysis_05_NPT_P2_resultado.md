# Analysis 05 NPT_P2 - SERENA 18

- Fecha: `2026-04-25`
- Perfil: `fast_compare`
- Alcance: `ARQ NPT_P2 vs EST NPT_P2`
- Estado: `completed`

## Alineacion aplicada

Archivo alineado:

- `PLANOS RECIBIDOS/ARQUITECTONICOS/06. JUNIO 2024/2208-Serena18-ID-Base-UpperFloor.dwg`

Transformacion manual aplicada:

- `translate_mm = (+168,737,102.0343, +624,500,058.7463)`

Criterio:

- llevar el cluster dominante ARQ `UpperFloor` al promedio de centroides dominantes de:
  - `EST. SERENA 18 - E10 - PLANTA EST. DE ENTREPISO Y DETALLES CASA (1).dwg`
  - `EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y DETALLES CASA (MOD.I).dwg`
  - `EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y DETALLES CASA (MOD. II).dwg`

## Resultado

- `4` archivos seleccionados
- `3` pares programados
- `1400` elementos 2.5D
- `66` incidencias primarias
- `769` conflictos debug
- `823` elementos suprimidos

## Pares con incidencias primarias

- `2208-Serena18-ID-Base-UpperFloor.dwg` vs `EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg`
  - `31` incidencias
- `2208-Serena18-ID-Base-UpperFloor.dwg` vs `EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg`
  - `27` incidencias
- `2208-Serena18-ID-Base-UpperFloor.dwg` vs `EST. SERENA 18 - E10 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (1).dwg`
  - `8` incidencias

## Lectura

- Esta corrida dejó la mejor fidelidad relativa hasta ahora:
  - todas las incidencias primarias quedaron en confianza `high`
  - domina `polyline/polyline`
- El volumen debug (`769`) sigue alto, sobre todo por repetición estructural entre `E11` y `E12`.
- La comparación `NPT_P2` ya quedó desbloqueada y sirve para revisión manual dirigida de entrepiso.

## Archivos principales

- Resumen: [summary.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_NPT_P2/summary.json:1)
- Audit: [coordinate_audit.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_NPT_P2/coordinate_audit.json:1)
- Scheduler: [pair_schedule.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_NPT_P2/pair_schedule.json:1)
- Incidencias primarias: [primary_incidents.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_NPT_P2/primary_incidents.md:1)
- Alineacion usada: [alignment_manifest.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_NPT_P2/alignment_manifest.json:1)
