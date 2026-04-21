# Plan NASAS 09 — validación de presupuestos y corridas (presentación pre-viernes)

## Idea mejorada (antes de escalar a más proyectos)

### Objetivo
Demostrar que Dupla puede generar presupuestos comparables con un presupuesto preliminar real, midiendo brechas por disciplina y documentando qué aporta cada tipo de entrada (planos, pliego, revisión).

### Qué se fija y qué queda explícito como límite
- **Comparación numérica**: el Excel generado (layout Dupla) se compara con el «Preliminary Budget» NASAS (varias hojas, códigos tipo `1.01`). Muchas partidas no comparten el mismo esquema de códigos que el BC3 interno: la **cobertura por código** puede ser baja aunque el **análisis por disciplina** y los **totales** sigan siendo útiles. El informe lo declara para no sobreinterpretar el porcentaje de cobertura.
- **Pliego en Excel**: en este proyecto el pliego llegó como `.xlsx`. Para no bloquear la visión, se genera un **PDF de texto** con el contenido tabular del pliego (no es maquetación original). Próximo paso recomendable: exportar el pliego oficial a PDF para alinear con lo que revisa el cliente.
- **Reglamentos**: viven en `knowledge/reglamentos_mived/` (fuera de la carpeta del proyecto) y se usan como extracto de texto para el **informe de calidad con IA**, no como sustituto de revisión profesional ni de cumplimiento normativo certificado.
- **Web**: el modelo no navega internet en tiempo real en esta implementación. El informe IA incluye **temas sugeridos** para búsqueda en fuentes oficiales (MIVED, etc.).

### Tres corridas
| Carpeta | Entradas de visión (PDF fusionado) |
| --- | --- |
| `corrida_PPR` | Planos + texto del pliego (desde xlsx) + PDFs de revisión |
| `corrida_PP` | Planos + pliego |
| `corrida_P` | Solo planos |

El **merge CAD (DWG)** es común: se guarda en `outputs/corridas/_cad_merge/` y se reutiliza con `--reuse-cad` para ahorrar tiempo y costo APS.

### Salidas por corrida
- `excel/` — copia del presupuesto generado Dupla  
- `presto/` — export BC3 (FIEBDC) cuando el JSON de presupuesto es válido  
- `informes/` — comparación automática, Markdown, JSON de métricas, JSON de calidad IA, **PDF final** (`informe_final_<tag>.pdf`)  
- `inputs/` — metadatos y PDF fusionado usado en visión  

### Roadmap corto (post-demo)
1. Mapear códigos NASAS ↔ BC3 por capítulo para subir cobertura por código.  
2. Presupuesto **por disciplina** en Excel separados (reutilizar pipeline de split por disciplina cuando el PDF esté clasificado).  
3. Conector opcional a **búsqueda web restringida** (dominios oficiales) para citas actualizadas.  
4. Entrenamiento / few-shot con más proyectos validados del mismo cliente.
