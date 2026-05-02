# Prompt para ChatGPT - analysis_07_NPT_P2 - SERENA 18

Copia y pega el siguiente prompt en ChatGPT para que te devuelva un informe mas humano, legible y orientado a revision interdisciplinaria.

```text
Actua como un coordinador tecnico senior de proyectos AEC.
Quiero que redactes un informe profesional, natural y humano, en espanol neutro, a partir de los datos estructurados de una corrida de coordinacion 2.5D.

Objetivo del informe:
- que sea facil de leer por arquitectura, estructura y, cuando aplique, especialidades MEP
- que separe claramente hallazgos defendibles vs ruido tecnico
- que priorice accionabilidad y lectura ejecutiva antes que detalle crudo
- que no suene a salida automatica ni a log tecnico

Reglas de redaccion:
- no inventes datos, recintos, ejes, habitaciones ni decisiones que no aparezcan en la informacion
- cuando la confianza sea baja o el caso requiera validacion manual, dilo explicitamente
- no presentes hotspots ni debug como si fueran clashes finales
- usa lenguaje profesional y claro, no marketing, no exageraciones
- si hay hallazgos defendibles, abre con ellos
- si no hay cobertura real para electrico o sanitario, dilo en vez de forzar una lectura

Estructura requerida:
1. Resumen ejecutivo
2. Hallazgos defendibles prioritarios
3. Hallazgos que requieren validacion manual
4. Lectura por perfil de revisor
5. Ruido tecnico y limites del run
6. Recomendaciones para la siguiente ronda de coordinacion

Datos del run:
- run_label: analysis_07_NPT_P2
- generated_at: 2026-05-02T13:06:43.905397+00:00
- analysis_profile: fast_compare
- status: completed
- selected_candidates: 4
- scheduled_pairs: 3
- elements: 1400
- primary_incidents: 66
- defendable_incidents: 46
- validation_incidents: 20
- debug_conflicts: 769
- suppressed_elements: 823
- confidence_mix: medium=50, high=16
- severity_mix: medium=28, low=20, high=16, critical=2

Resumen por pares:
- 2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | incidents=31 | members=115 | top_priority=P1 | confidence_mix=medium=23, high=8 | severity_mix=medium=13, low=9, high=8, critical=1
- 2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | incidents=27 | members=102 | top_priority=P1 | confidence_mix=medium=19, high=8 | severity_mix=medium=10, high=8, low=8, critical=1
- 2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E10 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (1).dwg | incidents=8 | members=23 | top_priority=P2 | confidence_mix=medium=8 | severity_mix=medium=5, low=3

Hallazgos defendibles top:
- incident_0019 | priority=P1 | severity=critical | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | location=NPT_P2; (168,832,051, 624,560,950) mm | layers=I-FURN / PARCELS | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0050 | priority=P1 | severity=critical | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | location=NPT_P2; (168,832,051, 624,560,950) mm | layers=I-FURN / PARCELS | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0027 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | location=NPT_P2; (168,835,479, 624,569,513) mm | layers=I-WALL / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0058 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | location=NPT_P2; (168,835,479, 624,569,513) mm | layers=I-WALL / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0010 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | location=NPT_P2; (168,827,059, 624,562,963) mm | layers=I-FURN / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0039 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | location=NPT_P2; (168,827,059, 624,562,963) mm | layers=I-FURN / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0009 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | location=NPT_P2; (168,824,639, 624,568,338) mm | layers=I-EQUIPMENT / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0036 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | location=NPT_P2; (168,824,639, 624,568,338) mm | layers=I-EQUIPMENT / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0014 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | location=NPT_P2; (168,829,204, 624,563,188) mm | layers=I-FLOR-FIN / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0045 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | location=NPT_P2; (168,829,204, 624,563,188) mm | layers=I-FLOR-FIN / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0020 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | location=NPT_P2; (168,833,387, 624,563,658) mm | layers=I-FURN / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0051 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | location=NPT_P2; (168,833,387, 624,563,658) mm | layers=I-FURN / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.

Casos con validacion manual top:
- incident_0023 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | layers=I-FURN / ESCALA_HUMANA
- incident_0054 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | layers=I-FURN / ESCALA_HUMANA
- incident_0028 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | layers=I-FURN / ESCALA_HUMANA
- incident_0059 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | layers=I-FURN / ESCALA_HUMANA
- incident_0029 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | layers=2 / PARCELS
- incident_0060 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | layers=2 / PARCELS
- incident_0012 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | layers=I-FURN-RUGS / EST - ACERO
- incident_0041 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | layers=I-FURN-RUGS / EST - ACERO
- incident_0043 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | layers=I-WALL / plano 2
- incident_0032 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | layers=I-MILLWORK / TITULOS

Ruido tecnico y limites:
- noise_debug_conflicts=769
- noise_suppression_reasons=bounds_fallback=713, container_bbox=110
- noise_audit_status=eligible=4
- noise_blocked_pairs=0
- noise_block_reasons=none
- hotspots_grouped=494

Devuelveme solo el informe final en markdown, no expliques tu proceso.
```
