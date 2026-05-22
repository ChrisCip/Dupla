# Prompt para ChatGPT - analysis_08_NPT_P1 - SERENA 18

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
- run_label: analysis_08_NPT_P1
- generated_at: 2026-05-05T22:51:09.388077+00:00
- analysis_profile: fast_compare
- status: completed
- selected_candidates: 3
- audited_files: 3
- eligible_files: 3
- scheduled_pairs: 2
- elements: 1050
- primary_incidents: 53
- defendable_incidents: 6
- validation_incidents: 47
- debug_conflicts: 179
- suppressed_elements: 596
- confidence_mix: low=47, medium=6
- severity_mix: low=36, medium=12, high=5

Contexto estructurado adicional:
- Usa `analysis_bot_context.json` como fuente factual primaria para conteos, cobertura, pares y limitaciones.
- Si el readiness documental contradice el run final, explica que el coordinate audit promovio la comparabilidad real.
- No conviertas layers en nombres de elementos constructivos reales si no existe mapeo semantico.
- Solo usa nombres de elementos si el contexto estructurado indica `mapping_confidence` medium o high.

Resumen por pares:
- Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | incidents=36 | members=253 | top_priority=P2 | confidence_mix=low=31, medium=5 | severity_mix=low=23, medium=9, high=4
- Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg | incidents=17 | members=70 | top_priority=P2 | confidence_mix=low=16, medium=1 | severity_mix=low=13, medium=3, high=1

Hallazgos defendibles top:
- incident_0026 | priority=P2 | severity=high | confidence=medium | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | location=NPT_P1; (168,817,815, 624,648,464) mm | layers=MARCO / EST_PROYECCION | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0021 | priority=P2 | severity=high | confidence=medium | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | location=NPT_P1; (168,812,817, 624,648,464) mm | layers=MARCO / EST - BORDE EXTERIOR | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0034 | priority=P2 | severity=high | confidence=medium | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | location=NPT_P1; (168,832,736, 624,649,470) mm | layers=MARCO / TITULOS | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0051 | priority=P2 | severity=high | confidence=medium | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg | location=NPT_P1; (168,826,979, 624,644,583) mm | layers=MARCO / EST_PROYECCION | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0005 | priority=P2 | severity=high | confidence=medium | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | location=NPT_P1; (168,802,950, 624,651,070) mm | layers=Solares / EST. MADERA | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
- incident_0035 | priority=P2 | severity=medium | confidence=medium | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | location=NPT_P1; (168,833,404, 624,651,010) mm | layers=MUROS / TITULOS | action=Revisar el par directamente y revisar con validacion acotada.

Casos con validacion manual top:
- incident_0029 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | layers=MARCO / EST_PROYECCION
- incident_0020 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | layers=MARCO / EST - EJE DE VIGA
- incident_0017 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | layers=MARCO / piso
- incident_0008 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | layers=MARCO / EST - BORDE INTERIOR
- incident_0016 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | layers=MARCO / EST - BORDE INTERIOR
- incident_0022 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | layers=MARCO / EST - BORDE EXTERIOR
- incident_0024 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | layers=MARCO / piso
- incident_0039 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg | layers=MARCO / ESCALA_HUMANA
- incident_0003 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | layers=MARCO / EST. MADERA
- incident_0036 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg | layers=MARCO / EST. MUROS DE BLOQUE BAJO NIVEL DE PISO

Ruido tecnico y limites:
- noise_debug_conflicts=179
- noise_suppression_reasons=bounds_fallback=430, container_bbox=166
- noise_audit_status=eligible=3
- noise_blocked_pairs=0
- noise_block_reasons=none
- hotspots_grouped=162

Devuelveme solo el informe final en markdown, no expliques tu proceso.
```
