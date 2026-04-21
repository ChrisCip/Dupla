# Plan: verificar que el análisis es correcto (extracción + IA)

Objetivo: **no confiar en una sola métrica** (p. ej. similitud con PRES), sino validar por capas qué es **determinístico**, qué es **heurístico** y qué es **IA**.

## Parte 1 — Trazabilidad y auditoría reproducible (este entregable)

- Leer `dupla_full_budget_output.json` de una corrida.
- Resumir:
  - **Modo de pipeline** (CAD-only vs visión: rutas en `metadata`).
  - **Inventario híbrido**: recuentos por `source` (`json` / `vision` / `hybrid`) y notas de conflicto (CAD vs visión).
  - **Takeoffs**: cantidad, fórmula, `trace.source_entity_sources`, supuestos.
  - **Compositor**: `budget_diagnostics` (cuántos takeoffs entran al presupuesto y por qué se excluyen otros).
  - **Clasificador BC3**: por cada takeoff, si el candidato elegido viene de `gpt4o`, `embedding`+GPT o `keyword_match` (fallback).
- Salida: `auditoria_extraccion_parte1.md` junto al JSON (o ruta indicada).

**Cómo interpretar:** si la Parte 1 está completa y coherente, sabés *de dónde sale cada número* antes de juzgar si “parece” el PRES.

## Parte 2 — Calidad del clasificador (muestra manual)

- Elegir **N takeoffs** (p. ej. 20) estratificados por capítulo.
- Etiqueta humana: código BC3 “correcto” o rango aceptable.
- Medir: precisión@1 del candidato top, tasa de uso GPT vs fallback.

## Parte 3 — Coherencia física y reglas

- Checks automáticos: unidades, no negativos, orden de magnitud (áreas vs perímetros), conflictos `conflict_notes` no vacíos sin revisión.

## Parte 4 — Validez frente a PRES (separada de Parte 1)

- Comparación PRES ya existente (`compare_budget`) + baseline estructural.
- Añadir en el futuro comparación **semántica** o por capítulo, no solo código exacto.

---

**Script Parte 1:** `python scripts/audit_extraction_part1.py --run-dir <carpeta_corrida>`
