# Re-auditoría post-fix — Bloqueantes B4, B1, B3, B2 y pricing

**Alcance:** Verificación estática del código (sin ejecutar `dupla_run_gebsa.py`, sin modificar archivos en el momento del análisis).  
**Referencia previa:** `audit_pre_e2e_discipline_report.md`  
**Runner:** `dupla_run_gebsa.py` — GEBSA IV, 4 disciplinas (`arquitectura`, `estructura`, `sanitario`, `electrico`).

---

## V1 — B4: `discipline_id` cableado

| Verificación | Estado |
|--------------|--------|
| `dupla_run_gebsa.py` pasa `upload_discipline_id=disc_id` a `run_full_vision_analysis()` | **Sí** (~líneas 278–284). |
| `agents/vision_agent.py` recibe `upload_discipline_id` y lo usa | **Sí:** alias `_UPLOAD_DISCIPLINE_ALIASES` y párrafo `_UPLOAD_DISCIPLINE_PROMPT` inyectado en `_build_simple_user_prompt` (~451–456, 336–363). |
| `knowledge/prompts/{disciplina}/user_prompt.md` por disciplina | **Existen** los cuatro. El preflight de Gebsa **exige** que el archivo exista (~140–146), pero **`run_full_vision_analysis` no lee** el contenido de esos `.md` en la llamada al modelo: usa prompt construido en código + metodología de oficina. |
| `agents/quantifier_agent.py` — `runner_source_discipline` | **Sí** vía `build_budget_from_inventory` en `core/pipeline.py` (~147). |
| `source_discipline` en takeoffs | `_stamp_takeoffs_source_discipline` asigna la **misma** etiqueta canónica de corrida a **todos** los takeoffs (~55–62 en `pipeline.py`). |
| `agents/classifier_agent.py` — `project_discipline_id` | **Sí** en prompt por capítulo (~394–399). |
| `disciplines/*/domain_rules.yaml` (×4) | **Sí.** |
| `disciplines/domain_validator.py` — `validate_vision_output` | Usa reglas cargadas por `load_domain_rules_for_discipline`. |

**Score B4:** **7/10** — Implementación real de contexto por corrida y hints en Vision; **parcial** respecto a “un prompt por archivo `user_prompt.md`” y a `source_discipline` homogénea por corrida.

**Delta estimado (separación disciplinaria):** +2 a +3 vs auditoría previa.

---

## V2 — B1: Partidas específicas

| Verificación | Estado |
|--------------|--------|
| Prompt Vision (código) | Pide muros por tipo, puertas/ventanas detalladas, eléctrico/sanitario enumerado (~475–502 en `vision_agent.py`). |
| Adapter → inventario | Depende de salida Vision y `_simple_to_level_inventory`; no sustituye ausencia de múltiples `Wall` por tipo en el JSON. |
| Quantifier — takeoffs separados por tipo (ej. C1 vs C2 en un solo agregado) | **No** como regla general: sigue **`wall_net_area` por entidad muro** (`quantifier_agent.py` ~734–738), no partición automática “701 m² → C1 + C2” sin que Vision devuelva paredes distintas. |
| Descripción para BC3 | Classifier envía `takeoff_description` como `desc` cuando existe (`classifier_agent.py` ~377–379, 414–416). |
| Excel “Resumen” | Viene del flujo de composición (`build_budget_summary` / capítulos); coherente con takeoff + candidato. |

**Score B1:** **4/10** — Mejora de descripción y matching; **no** garantiza separación física por tipo como en el ejemplo ideal del informe previo.

**Delta estimado (generación / cuantificación):** +1 cada uno (techo sin E2E).

---

## V3 — B3: `wet_area_fixture_count`

| Verificación | Estado |
|--------------|--------|
| Emisión en `quantifier_agent.py` | **Sí:** `_wet_area_fixture_takeoffs`, `item_type="wet_area_fixture_count"` (~1140–1189). |
| Deduplicación vs `fixture_count` | `_SKIP_FIXTURE_COUNT_IF_WET_AREAS` + tests en `tests/test_quantifier_wet_area_fixtures.py`. |
| `source_discipline="sanitaria"` en trazabilidad | El takeoff puede llevar `trace.metadata["source_discipline": "sanitaria"]` en emisión (~1184–1186), pero **`_stamp_takeoffs_source_discipline`** **sobrescribe** `source_discipline` con la disciplina de la corrida (p. ej. arquitectura → `arquitectonica`). |

**Score B3:** **7/10** — Emisión y dedupe **correctas**; criterio literal “siempre sanitaria en metadata final” **parcial**.

**Delta estimado (generación sanitaria):** +3 a +4.

---

## V4 — B2: Defaults vs plano + fuente de cantidad

| Verificación | Estado |
|--------------|--------|
| Rules engine — preferir inputs del takeoff | **Sí** en `rules_engine/registry.py` (estrategias `count_area_or_default`, `beam_length_derived`, `column_*`, `slab_area_thickness_derived`, `wall_length_finish_derived`, etc.). Ejecución vía `RulesEngine.apply` en `rules_engine/__init__.py`. |
| Metadata de origen | Clave **`quantity_source`** (`plan_measurement`, `default_estimate`, `mixed_measurement`, etc.), no el nombre `source` del ejemplo del prompt original, pero **equivalente**. |
| Excel — fuente de cantidad | Columna **`Fuente Cantidad`** (+ **`Fuente Precio`**) en `budget/export_excel.py` HEADERS. |
| Acero por ratio | `_rebar_takeoffs` con `quantity_source` / `quantity_source_note` (~1332–1374 en `quantifier_agent.py`). |

**Score B2:** **8/10**

**Delta estimado (cuantificación):** +2 a +3.

---

## V5 — Pricing: ConstruCosto primario

| Verificación | Estado |
|--------------|--------|
| Parser / loader CSV | `processors/construcosto_parser.py` reexporta `pricing/construcosto_loader.py`; lectura con **latin-1**; precios tipo `RD$1,710.00` vía `_parse_rdprice`. |
| Orden en `_extract_unit_price` (`budget/composer.py`) | **APU (analisis) → materiales → equipos → BC3 catálogo → `PRECIO_PENDIENTE`** (~160–205). **No** hay paso explícito para **`mano_obra`** en ese bucle (el loader sí ingiere MO). |
| Columna “Fuente Precio” | **Sí** en export (junto a “Fuente Cantidad”). |
| Etiqueta fallback BC3 | Texto fijo **"BC3 TGIU (fallback)"** aunque el catálogo activo en Gebsa sea **GIV** — convendría alinear el nombre con el archivo real. |

**Score PRICING:** **7/10**

**Delta estimado (catalogación):** +2.

---

## V6 — Pipeline GEBSA completo (estático)

- Disciplinas en orden configurado; `ProjectContext.metadata["discipline_id"]` por iteración.
- Salidas por disciplina: `RunOutputDir` (`discipline_excel`, `discipline_bc3`, `quality_report`, etc. en `core/output_structure.py`).
- Riesgo de contaminación **entre** disciplinas: **bajo** (corridas separadas). Dentro de una corrida, mismo stamp de `source_discipline` para todos los takeoffs.

**Ejecución real:** no verificada en este informe; depende de rutas PDF/DWG, `.env`, BC3 y servicios externos.

---

## V7 — Scorecard comparativo (estimación sin E2E)

| Disciplina | Gen | Cuant | Cat | Sep | Total | Delta aprox. |
|------------|-----|-------|-----|-----|-------|----------------|
| Arquitectónica | 6 | 6 | 7 | 7 | **26** | +7 |
| Estructural | 5 | 6 | 6 | 7 | **24** | +9 |
| Eléctrica | 4 | 5 | 6 | 7 | **22** | +8 |
| Sanitaria | 5 | 6 | 6 | 7 | **24** | +10 |
| **Promedio** | | | | | **24** | **+8.5** |

*Nota: celdas “DESPUÉS” son juicio de ingeniería sobre cierre de gaps en código; una corrida E2E puede subir o bajar estos números.*

### Bloqueantes — veredicto

| ID | Resuelto | Parcial | No resuelto |
|----|----------|---------|-------------|
| B4 | | ✓ | |
| B1 | | ✓ | |
| B3 | | ✓ | |
| B2 | ✓ (casi) | | |
| Pricing | | ✓ | |

### Nuevos riesgos / pendientes detectados

1. **Multi-BC3** (ver V8): no reflejado en `dupla_run_gebsa.py` actual.
2. **Few-shot PRES.xlsx (Giualca)** vs **códigos GEBSA (GIV)**: posible acoplamiento de códigos TGIU en entrenamiento/embeddings; requiere validación con datos reales.

### Veredicto E2E GEBSA IV

- **PARCIAL:** conviene ejecutar `python dupla_run_gebsa.py` o `python dupla_run_gebsa.py --only arquitectura` y revisar Excel/BC3 por disciplina antes de declarar listo para producción.

---

## V8 — Múltiples BC3 como catálogo acumulativo

| Verificación | Estado |
|--------------|--------|
| `load_or_build_embeddings` | Acepta **un** diccionario `bc3_catalog`; fingerprint sobre `items` (`knowledge/bc3_embeddings.py`). |
| `dupla_run_gebsa.py` | Un solo `parse_bc3` sobre `BC3_PATH` (p. ej. GIV); **no** merge con `data/TGIU.bc3` en el análisis estático. |
| `parse_bc3` | Una ruta por invocación (`processors/bc3_parser.py`); sin API documentada de merge multi-archivo en el flujo Gebsa. |
| Metadata de procedencia por partida en match | No cubierto de extremo a extremo en el diseño actual del runner Gebsa. |

**CAPACIDAD MULTI-BC3:** **No soportada** en el runner analizado — cambios mínimos típicos: merge de conceptos (dedupe por código), un solo catálogo pasado a embeddings, opcionalmente `bc3_origin` por ítem, y carga de dos rutas en `dupla_run_gebsa.py`.

---

## Archivos clave citados

1. `dupla_run_gebsa.py` — Vision, contexto, BC3 único, exports.
2. `agents/vision_agent.py` — `_UPLOAD_DISCIPLINE_PROMPT`, `_build_simple_user_prompt`.
3. `core/pipeline.py` — `_stamp_takeoffs_source_discipline`, `build_budget_from_inventory`.
4. `agents/quantifier_agent.py` — muros, `wet_area_fixture_count`, rebar, estructura.
5. `agents/classifier_agent.py` — `project_discipline_id`, `desc` desde takeoff.
6. `rules_engine/registry.py` + `rules_engine/__init__.py` — B2.
7. `budget/composer.py` — `_extract_unit_price`.
8. `budget/export_excel.py` — columnas Fuente Cantidad / Fuente Precio.
9. `pricing/construcosto_loader.py` — CSV latin-1, fuentes analisis/materiales/mano_obra/equipos.
10. `knowledge/bc3_embeddings.py` — índice sobre un catálogo.

---

*Documento generado como entregable de re-auditoría post-fix; no sustituye prueba de campo con planos y presupuesto real.*
