# Prompt para ChatGPT - analysis_08_TECHO - SERENA 18

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
- run_label: analysis_08_TECHO
- generated_at: 2026-05-05T22:58:23.251530+00:00
- analysis_profile: fast_compare
- status: completed
- selected_candidates: 7
- audited_files: 7
- eligible_files: 7
- scheduled_pairs: 6
- elements: 2450
- primary_incidents: 157
- defendable_incidents: 131
- validation_incidents: 26
- debug_conflicts: 1262
- suppressed_elements: 1328
- confidence_mix: medium=98, high=59
- severity_mix: medium=57, high=48, critical=26, low=26

Contexto estructurado adicional:
- Usa `analysis_bot_context.json` como fuente factual primaria para conteos, cobertura, pares y limitaciones.
- Si el readiness documental contradice el run final, explica que el coordinate audit promovio la comparabilidad real.
- No conviertas layers en nombres de elementos constructivos reales si no existe mapeo semantico.
- Solo usa nombres de elementos si el contexto estructurado indica `mapping_confidence` medium o high.

Resumen por pares:
- 2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E18 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. I).dwg | incidents=30 | members=192 | top_priority=P1 | confidence_mix=medium=19, high=11 | severity_mix=high=10, medium=10, low=7, critical=3
- 2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg | incidents=29 | members=190 | top_priority=P1 | confidence_mix=medium=19, high=10 | severity_mix=medium=11, high=9, low=5, critical=4
- 2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg | incidents=29 | members=208 | top_priority=P1 | confidence_mix=medium=19, high=10 | severity_mix=medium=12, high=9, critical=5, low=3
- 2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg | incidents=28 | members=196 | top_priority=P1 | confidence_mix=medium=17, high=11 | severity_mix=medium=11, high=7, critical=6, low=4
- 2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E19 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. II).dwg | incidents=22 | members=156 | top_priority=P1 | confidence_mix=medium=13, high=9 | severity_mix=medium=8, high=7, critical=4, low=3
- 2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E17 - PLANTA EST.DE TECHOS T2 EN MADERA Y DETALLES - MOD, VIGAS VY-13, VY-26, VY-25.dwg | incidents=19 | members=136 | top_priority=P1 | confidence_mix=medium=11, high=8 | severity_mix=high=6, medium=5, critical=4, low=4

Hallazgos defendibles top:
- incident_0076 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg | location=TECHO; (168,841,135, 624,666,914) mm | layers=I-FURN / PARCELS | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0036 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg | location=TECHO; (168,835,779, 624,670,611) mm | layers=I-FURN / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0043 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg | location=TECHO; (168,839,897, 624,668,453) mm | layers=I-FURN / plano 1 | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0046 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg | location=TECHO; (168,841,274, 624,666,898) mm | layers=I-FURN / PARCELS | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0124 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E18 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. I).dwg | location=TECHO; (168,841,116, 624,666,915) mm | layers=I-FURN / PARCELS | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0092 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E17 - PLANTA EST.DE TECHOS T2 EN MADERA Y DETALLES - MOD, VIGAS VY-13, VY-26, VY-25.dwg | location=TECHO; (168,837,924, 624,669,135) mm | layers=I-FLOR-FIN / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0091 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E17 - PLANTA EST.DE TECHOS T2 EN MADERA Y DETALLES - MOD, VIGAS VY-13, VY-26, VY-25.dwg | location=TECHO; (168,837,924, 624,666,277) mm | layers=I-FLOR-FIN / Solares | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0035 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg | location=TECHO; (168,835,779, 624,663,350) mm | layers=I-FURN / PARCELS | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0006 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg | location=TECHO; (168,835,818, 624,663,352) mm | layers=I-FURN / PARCELS | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0112 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E18 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. I).dwg | location=TECHO; (168,835,818, 624,663,352) mm | layers=I-FURN / PARCELS | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0018 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg | location=TECHO; (168,841,116, 624,666,915) mm | layers=I-FURN / PARCELS | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0146 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E19 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. II).dwg | location=TECHO; (168,841,073, 624,666,920) mm | layers=I-FURN / PARCELS | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.

Casos con validacion manual top:
- incident_0016 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg | layers=I-FLOR-FIN / PARCELS
- incident_0122 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E18 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. I).dwg | layers=I-FLOR-FIN / PARCELS
- incident_0144 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E19 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. II).dwg | layers=I-FLOR-FIN / PARCELS
- incident_0079 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg | layers=I-FURN / Solares
- incident_0149 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E19 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. II).dwg | layers=I-WALL / Solares
- incident_0073 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg | layers=I-WALL / Solares
- incident_0028 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg | layers=I-FURN / TITULOS
- incident_0057 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg | layers=I-FURN / TITULOS
- incident_0085 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg | layers=I-FURN / TITULOS
- incident_0104 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E17 - PLANTA EST.DE TECHOS T2 EN MADERA Y DETALLES - MOD, VIGAS VY-13, VY-26, VY-25.dwg | layers=I-FURN / TITULOS

Ruido tecnico y limites:
- noise_debug_conflicts=1262
- noise_suppression_reasons=bounds_fallback=1228, container_bbox=100
- noise_audit_status=eligible=7
- noise_blocked_pairs=0
- noise_block_reasons=none
- hotspots_grouped=769

Devuelveme solo el informe final en markdown, no expliques tu proceso.
```
