# Prompt para ChatGPT - analysis_08_ARQ_HS_P1 - SERENA 18

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
- run_label: analysis_08_ARQ_HS_P1
- generated_at: 2026-05-05T23:00:04.705111+00:00
- analysis_profile: fast_compare
- status: completed
- selected_candidates: 2
- audited_files: 2
- eligible_files: 2
- scheduled_pairs: 1
- elements: 416
- primary_incidents: 0
- defendable_incidents: 0
- validation_incidents: 0
- debug_conflicts: 66
- suppressed_elements: 167
- confidence_mix: none
- severity_mix: none

Contexto estructurado adicional:
- Usa `analysis_bot_context.json` como fuente factual primaria para conteos, cobertura, pares y limitaciones.
- Si el readiness documental contradice el run final, explica que el coordinate audit promovio la comparabilidad real.
- No conviertas layers en nombres de elementos constructivos reales si no existe mapeo semantico.
- Solo usa nombres de elementos si el contexto estructurado indica `mapping_confidence` medium o high.

Resumen por pares:

Hallazgos defendibles top:

Casos con validacion manual top:

Ruido tecnico y limites:
- noise_debug_conflicts=66
- noise_suppression_reasons=container_bbox=155, bounds_fallback=12
- noise_audit_status=eligible=2
- noise_blocked_pairs=0
- noise_block_reasons=none
- hotspots_grouped=0

Devuelveme solo el informe final en markdown, no expliques tu proceso.
```
