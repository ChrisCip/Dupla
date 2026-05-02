# Prompt para ChatGPT - analysis_07_CIMENTACION - SERENA 18

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
- run_label: analysis_07_CIMENTACION
- generated_at: 2026-05-02T13:06:08.271509+00:00
- analysis_profile: fast_compare
- status: completed
- selected_candidates: 3
- scheduled_pairs: 2
- elements: 1050
- primary_incidents: 1
- defendable_incidents: 1
- validation_incidents: 0
- debug_conflicts: 706
- suppressed_elements: 635
- confidence_mix: medium=1
- severity_mix: medium=1

Resumen por pares:
- 2208-Serena18-ID-Base.dwg vs EST. SERENA 18 - E06 - PLANTA EST. CIMIENTOS Y DETALLES  CASA.dwg | incidents=1 | members=1 | top_priority=P2 | confidence_mix=medium=1 | severity_mix=medium=1

Hallazgos defendibles top:
- incident_0000 | priority=P2 | severity=medium | confidence=medium | level=CIMENTACION | pair=2208-Serena18-ID-Base.dwg vs EST. SERENA 18 - E06 - PLANTA EST. CIMIENTOS Y DETALLES  CASA.dwg | location=CIMENTACION; (168,816,577, 624,649,583) mm | layers=I-FURN / Planos | action=Revisar el par directamente y revisar con validacion acotada.

Casos con validacion manual top:

Ruido tecnico y limites:
- noise_debug_conflicts=706
- noise_suppression_reasons=bounds_fallback=467, container_bbox=168
- noise_audit_status=eligible=3
- noise_blocked_pairs=0
- noise_block_reasons=none
- hotspots_grouped=445

Devuelveme solo el informe final en markdown, no expliques tu proceso.
```
