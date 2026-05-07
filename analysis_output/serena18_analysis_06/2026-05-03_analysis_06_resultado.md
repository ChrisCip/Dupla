# analysis_06 - SERENA 18

- Fecha: `2026-05-03`
- Perfil: `fast_compare`
- Estado: `completed`
- Carpeta: `C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_06`

## Resultado ejecutivo
- `3` archivos seleccionados
- `2` pares programados
- `1050` elementos 2.5D
- `53` incidencias primarias
- `6` hallazgos defendibles
- `47` incidencias que requieren validacion manual
- `179` conflictos debug
- `596` elementos suprimidos

## Lectura corta
- Readiness automatico comparable: `no`.
- Mix de audit: `eligible=3`.
- Mix de confianza del primario: `low=47, medium=6`.
- Mix de severidad del primario: `low=36, medium=12, high=5`.

## Pares principales
- `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  incidencias: `36`
  miembros: `253`
  prioridad dominante: `P2`
  confianza: `low=31, medium=5`
- `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg`
  incidencias: `17`
  miembros: `70`
  prioridad dominante: `P2`
  confianza: `low=16, medium=1`

## Hallazgos defendibles mas fuertes
- `incident_0026` | `P2` | `high` | `medium`
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  ubicacion: `NPT_P1; (168,817,815, 624,648,464) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0021` | `P2` | `high` | `medium`
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  ubicacion: `NPT_P1; (168,812,817, 624,648,464) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0034` | `P2` | `high` | `medium`
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  ubicacion: `NPT_P1; (168,832,736, 624,649,470) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0051` | `P2` | `high` | `medium`
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg`
  ubicacion: `NPT_P1; (168,826,979, 624,644,583) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0005` | `P2` | `high` | `medium`
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  ubicacion: `NPT_P1; (168,802,950, 624,651,070) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0035` | `P2` | `medium` | `medium`
  nivel: `NPT_P1`
  par: `Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`
  ubicacion: `NPT_P1; (168,833,404, 624,651,010) mm`
  accion: Revisar el par directamente y revisar con validacion acotada.

## Vista por perfil
- Arquitectura: `direct`
- Electrico: `not_in_run`
- Sanitario: `not_in_run`

## Ruido tecnico separado
- Debug conflicts: `179`
- Suppression reasons: `bounds_fallback=430, container_bbox=166`
- Blocked pairs: `0`
- Block reasons: `none`
- Hotspots agrupados: `162`

## Archivos principales
- Resumen: [summary.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_06/summary.json:1)
- Informe tecnico: [technical_coordination_report.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_06/technical_coordination_report.md:1)
- Contexto bot: [analysis_bot_context.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_06/analysis_bot_context.json:1)
- Reporte humano: [coordination_report_human.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_06/coordination_report_human.md:1)
- Registro primario: [primary_incidents.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_06/primary_incidents.md:1)
- Audit: [coordinate_audit.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_06/coordinate_audit.md:1)
- Hotspots: [hotspot_incidents.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_06/hotspot_incidents.md:1)
- Prompt ChatGPT: [2026-05-03_analysis_06_chatgpt_prompt.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_06/2026-05-03_analysis_06_chatgpt_prompt.md:1)
- Elementos por DWG: [elements_by_dwg.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_06/elements_by_dwg.json:1)
- Links clash-element: [clash_element_links.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_06/clash_element_links.json:1)
