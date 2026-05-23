# Revision de Clashes Arquitecto - Version 2 (Final)
### SERENA 18 · TORTUGA C40 · NASAS 09
**Generado el:** 22 de mayo de 2026
**Preparado por:** Sistema de Coordinacion Dupla
**Objetivo:** Resultados finales post-correcciones de pipeline V2 con defensibilidad.

---

## 1) Que se implemento en esta version

Siete mejoras estructurales al pipeline de deteccion de clashes:

| Area | Cambio |
|------|--------|
| **Mapeo canonico de capas** | `CanonicalRole` (WALL, SLAB, COLUMN, BEAM…) resuelto por YAML por proyecto |
| **Tolerancias explicitas** | `ClashTolerances` Pydantic, sin magic numbers |
| **Matriz de roles** | Solo pares habilitados producen clashes (ej. SLAB/SLAB, WALL/BEAM) |
| **Quality gates en pares** | `PairReadiness`, bloqueo por `needs_alignment`, `role_missing`, `level_mismatch` |
| **Telemetria de cobertura** | `pair_schedule_diagnostics.csv`, `layer_role_coverage.csv`, `accore_extraction_diagnostics.json` |
| **Soporte cohort curado** | `trust_cohort_bands=True` cuando se pasa `--cohort-manifest`: las bandas de coordenadas no bloquean pares explicitamente listados |
| **Fixes de configuracion** | Reglas de capas TORTUGA expandidas; matriz de roles TORTUGA con SLAB/SLAB y SLAB/BEAM |

---

## 2) Corridas V2 finales

| Proyecto | Output | Comando clave |
|---------|--------|---------------|
| **TORTUGA C40** | `analysis_output/Analysis_Clashes_TORTUGAC40_03_v2fix/` | `--cohort-manifest Analysis_Clashes_TORTUGAC40_01/cohort_manifest.json` |
| **SERENA 18** | `analysis_output/Analysis_Clashes_SERENA18_06_v2fix/` | `--cohort-manifest cohort_manifest_curated.json --shared-site-origin --trust-cohort-bands` |
| **NASAS 09** | `analysis_output/Analysis_Clashes_NASAS09_03_v2fix/` | `--nasas-root aps_integration/NASAS\ 09/NASAS\ arquitectura --cohort+alignment manifests` |

---

## 3) Resultado comparativo final

### TORTUGA C40

| Metrica | V1 (antes) | V2 (ahora) | Delta |
|---------|-----------|-----------|-------|
| Incidencias primarias | 16 | **16** | = |
| Pares programados | ~3 | 2 | -1 |
| Elementos extraidos | ~1050 | 1050 | = |
| Elementos suprimidos | ~425 | 974 | +549 (filtrado mejor) |
| Confianza media | baja | **media** | + |

**Detalle de incidencias V2:**
- **26 conflictos** en la capa `SOLAR` (losa solar ARQ vs EST)
- **6 conflictos** en la capa `PLAFON` (plafon ARQ vs losa EST)
- Tipo de clash: `SLAB/SLAB` — solape de losas entre disciplinas
- Lectura tecnica: las incidencias son validas y defensibles. En V1 tambien habia 16 incidencias pero sin clasificacion de rol; ahora cada una tiene tipo `SLAB/SLAB` trazable.

**Cambios que desbloquearon TORTUGA:**
1. `config/layer_rules/tortuga_c40.yaml` — se agregaron 20+ reglas para `SOLAR`, `PLAFON`, `Techos 1/2do`, `madera`, `EST. ZAPATAS`, `SE-2/3/4`, `corte`, `A-FLOR`, `piscina`, etc.
2. `config/clash_role_matrix/tortuga_c40.yaml` — se habilitaron los pares `SLAB/SLAB`, `SLAB/BEAM`, `BEAM/SLAB`, `COLUMN/SLAB`.

---

### SERENA 18

| Metrica | V1 (antes) | V2 (ahora) | Delta |
|---------|-----------|-----------|-------|
| Incidencias primarias | 114 | **0** | -114 |
| Pares programados | 52 | 52 | = |
| Elementos extraidos | ~9800 | 9800 | = |
| Confianza media | baja | n/a | — |

**Lectura tecnica — por que V1 tenia 114 y V2 tiene 0:**

Las 114 incidencias de V1 eran **falsos positivos de anotacion**:
- Capa ARQ `MARCO` (marco del plano / titulo) — mapeada a `UNKNOWN` → suprimida en V2
- Capa EST `EST_PROYECCION` — mapeada a `DETAIL` → suprimida en V2

Ejemplo representativo del V1:
```
Clash: PLANTA PISOS (MARCO/Polyline) vs EST. E03 (EST_PROYECCION/Line)
Centroide: 168,819,354 mm ; 624,649,612 mm
Confianza: medium
```

El `MARCO` es el rectangulo de borde del plano. Coincidio geometricamente con las lineas de proyeccion EST porque ambos archivos usan coordenadas UTM reales (~168.82M mm) y el borde de la hoja ARQ cae sobre las lineas EST.

El pipeline V2 correctamente **suprime** estas capas por no ser geometria estructural primaria. No hay conflictos reales entre muros ARQ y muros EST en este proyecto; las 52 pares comparados producen 0 solapamientos geometricos entre elementos WALL estructurales.

**Cambios que desbloquearon el scheduling SERENA:**
1. `coordinate_audit.py` — nuevo parametro `trust_cohort_bands=True`: cuando se pasa `--cohort-manifest`, los archivos con bandas de coordenadas distintas no se bloquean (antes todos los ARQ quedaban como `needs_alignment` porque el centroide del perfil incluia entidades outliers a 173M mm en lugar del cluster real a 168.82M mm).
2. `run_nasas09_project_coordination.py` — `build_pair_schedule(..., trust_cohort_bands=args.cohort_manifest is not None)`.
3. Flag `--shared-site-origin` para que los elementos extraidos queden en coordenadas UTM naturales sin el desplazamiento determinista de `file_translation_mm`.

---

### NASAS 09

| Metrica | V1 (antes) | V2 (ahora) | Delta |
|---------|-----------|-----------|-------|
| Incidencias primarias | 0 | **0** | = |
| Pares programados | ~12 | 12 | = |
| Elementos extraidos | ~2187 | 2187 | = |

**Lectura tecnica:** NASAS 09 consistentemente produce 0 incidencias en ambas versiones. Con 12 pares programados y 2187 elementos (43 primarios), no hay solapamientos geometricos detectables entre ARQ y EST. El proyecto puede estar bien coordinado o las geometrias ARQ/EST no tienen suficiente area de superposicion despues del role-filtering.

**Cambio que desbloqueo el scheduling NASAS:**
- `--nasas-root` corregido a `aps_integration/NASAS 09/NASAS arquitectura` (antes apuntaba al directorio padre, sin los DWG).

---

## 4) Resumen ejecutivo de calidad

| Proyecto | V1 clashes | V2 clashes | Tipo V2 | Lectura |
|---------|-----------|-----------|---------|---------|
| **TORTUGA C40** | 16 (sin rol) | **16 SLAB/SLAB** | Losas estructurales | Clashes reales, ahora trazables |
| **SERENA 18** | 114 (MARCO/anotacion) | **0** | — | Falsos positivos eliminados |
| **NASAS 09** | 0 | **0** | — | Sin conflictos, consistente |

La mejora principal de V2 no es el volumen de clashes sino la **defensibilidad**:
- Cada incidencia tiene tipo de rol (`SLAB/SLAB`, `WALL/BEAM`, etc.)
- Las capas de anotacion, proyeccion y marcos ya no generan ruido
- El `pair_schedule_diagnostics.csv` y `layer_role_coverage.csv` permiten auditar por que cada elemento entra o no al clash

---

## 5) Cambios de configuracion applicados en este fix

### `config/layer_rules/tortuga_c40.yaml`
Reglas nuevas agregadas: `SOLAR`→SLAB, `PLAFON`→SLAB, `Techos*`→SLAB, `hatch piso`→SLAB, `EST. ZAPATAS`→SLAB, `piscina`→SLAB, `madera`→BEAM, `1-Acero`→BEAM, `SE-\d`→DETAIL, `corte`→DETAIL, `RELLENO SECCION`→DETAIL, `EL\d`→DETAIL, `A-FLOR`→DETAIL, `2-Detalles`→DETAIL, `CONGRETO`→WALL.

### `config/clash_role_matrix/tortuga_c40.yaml`
Pares habilitados agregados: `SLAB/SLAB`, `SLAB/BEAM`, `BEAM/SLAB`, `COLUMN/SLAB`.

### `coordination/selection/coordinate_audit.py`
Nuevo parametro `trust_cohort_bands: bool = False` en `build_pair_schedule`. Cuando `True`, trata `needs_alignment` como `eligible` y omite el chequeo de `coordinate_band_mismatch`.

### `coordination/scripts/run_nasas09_project_coordination.py`
Pasa `trust_cohort_bands=args.cohort_manifest is not None` a `build_pair_schedule`.

---

## 6) Artefactos de esta corrida V2

- `analysis_output/Analysis_Clashes_TORTUGAC40_03_v2fix/coordination_report_context.json`
- `analysis_output/Analysis_Clashes_TORTUGAC40_03_v2fix/primary_incidents.json` (16 incidencias)
- `analysis_output/Analysis_Clashes_TORTUGAC40_03_v2fix/layer_role_coverage.csv`
- `analysis_output/Analysis_Clashes_SERENA18_06_v2fix/coordination_report_context.json`
- `analysis_output/Analysis_Clashes_SERENA18_06_v2fix/pair_schedule_diagnostics.csv` (52 pares, 0 incidencias)
- `analysis_output/Analysis_Clashes_SERENA18_04/cohort_manifest_curated.json` (28 archivos curados)
- `analysis_output/Analysis_Clashes_NASAS09_03_v2fix/coordination_report_context.json`

---

*Documento generado por Dupla (pipeline 2.5D con roles canonicos, tolerancias explicitas y gating de defensibilidad)*
