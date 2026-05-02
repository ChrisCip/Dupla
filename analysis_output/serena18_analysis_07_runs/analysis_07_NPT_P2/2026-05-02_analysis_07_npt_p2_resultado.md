# analysis_07_NPT_P2 - SERENA 18

- Fecha: `2026-05-02`
- Perfil: `fast_compare`
- Estado: `completed`
- Carpeta: `C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_07_runs/analysis_07_NPT_P2`

## Resultado ejecutivo
- `4` archivos seleccionados
- `3` pares programados
- `1400` elementos 2.5D
- `66` incidencias primarias
- `46` hallazgos defendibles
- `20` incidencias que requieren validacion manual
- `769` conflictos debug
- `823` elementos suprimidos

## Lectura corta
- Readiness automatico comparable: `no`.
- Mix de audit: `eligible=4`.
- Mix de confianza del primario: `medium=50, high=16`.
- Mix de severidad del primario: `medium=28, low=20, high=16, critical=2`.

## Pares principales
- `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg`
  incidencias: `31`
  miembros: `115`
  prioridad dominante: `P1`
  confianza: `medium=23, high=8`
- `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg`
  incidencias: `27`
  miembros: `102`
  prioridad dominante: `P1`
  confianza: `medium=19, high=8`
- `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E10 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (1).dwg`
  incidencias: `8`
  miembros: `23`
  prioridad dominante: `P2`
  confianza: `medium=8`

## Hallazgos defendibles mas fuertes
- `incident_0019` | `P1` | `critical` | `high`
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg`
  ubicacion: `NPT_P2; (168,832,051, 624,560,950) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0050` | `P1` | `critical` | `high`
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg`
  ubicacion: `NPT_P2; (168,832,051, 624,560,950) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0027` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg`
  ubicacion: `NPT_P2; (168,835,479, 624,569,513) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0058` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg`
  ubicacion: `NPT_P2; (168,835,479, 624,569,513) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0010` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg`
  ubicacion: `NPT_P2; (168,827,059, 624,562,963) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0039` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg`
  ubicacion: `NPT_P2; (168,827,059, 624,562,963) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0009` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg`
  ubicacion: `NPT_P2; (168,824,639, 624,568,338) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- `incident_0036` | `P1` | `high` | `high`
  nivel: `NPT_P2`
  par: `2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg`
  ubicacion: `NPT_P2; (168,824,639, 624,568,338) mm`
  accion: Revisar el par directamente y escalar en la siguiente ronda de coordinacion.

## Vista por perfil
- Arquitectura: `direct`
- Electrico: `not_in_run`
- Sanitario: `not_in_run`

## Ruido tecnico separado
- Debug conflicts: `769`
- Suppression reasons: `bounds_fallback=713, container_bbox=110`
- Blocked pairs: `0`
- Block reasons: `none`
- Hotspots agrupados: `494`

## Archivos principales
- Resumen: [summary.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_07_runs/analysis_07_NPT_P2/summary.json:1)
- Informe tecnico: [technical_coordination_report.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_07_runs/analysis_07_NPT_P2/technical_coordination_report.md:1)
- Registro primario: [primary_incidents.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_07_runs/analysis_07_NPT_P2/primary_incidents.md:1)
- Audit: [coordinate_audit.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_07_runs/analysis_07_NPT_P2/coordinate_audit.md:1)
- Hotspots: [hotspot_incidents.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_07_runs/analysis_07_NPT_P2/hotspot_incidents.md:1)
- Prompt ChatGPT: [2026-05-02_analysis_07_npt_p2_chatgpt_prompt.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_07_runs/analysis_07_NPT_P2/2026-05-02_analysis_07_npt_p2_chatgpt_prompt.md:1)
