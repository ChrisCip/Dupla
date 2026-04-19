# Auditoría de completitud por disciplina (pre-E2E)

**Alcance:** Análisis estático del repo Dupla (código + muestreo de `data/PRES.xlsx` y catálogo BC3). **No** se ejecutó el pipeline completo ni se comparó línea a línea el presupuesto real contra un output generado.

**Referencias numéricas verificadas:** `PRES.xlsx` — 296 filas `Capítulo`, 1565 filas `Partida` (1861 filas de datos desde la fila 4); columnas `Código, Nat, Ud, Resumen, CanPres, PrPres, ImpPres`. `TGIU.bc3` — 684 ítems en lista `items`, 884 entradas en `concepts_by_code` (parser).

---

## SECCIÓN 1: Inventario de partidas generadas por disciplina

### DISCIPLINA: Arquitectónica

**PARTIDAS QUE EL SISTEMA PUEDE GENERAR HOY (vía takeoffs base + reglas en `rules_engine/default_rules.json`):**

| # | Tipo / item_type (representativo) | Origen | Capítulo Dupla (clasificador) |
|---|-------------------------------------|--------|-------------------------------|
| 1 | `wall_net_area`, `wall_volume`, `wall_length`, `wall_gross_area` | Inventario CAD/híbrido → `agents/quantifier_agent.py` | 03 (`_ITEM_TYPE_TO_CHAPTER`) |
| 2 | `wall_finish_plaster`, `wall_finish_paint` | Reglas `wall_finish_*`, `wall_length_finish_standard` | 03 / 08 (pintura → 08) |
| 3 | `wall_waterproofing`, `wall_finish_tile` | Reglas muro húmedo | 03 |
| 4 | `floor_area`, `floor_screed`, `floor_finish`, `floor_finish_tile`, `floor_waterproofing` | Reglas `floor_finish_*`, `floor_finish_wet_area_standard` | 04; **`floor_waterproofing` → 07** en mapa estático |
| 5 | `ceiling_area`, `ceiling_finish_plaster`, `ceiling_finish_paint` | Reglas techo | 08 |
| 6 | `door_count`, `door_leaf_*`, `door_frame_count`, `door_hardware_set` | Reglas `door_assembly_*` | 05 |
| 7 | `window_count`, `window_installation_count`, `window_sealant_area`, `window_area` | Reglas ventana | 05 |
| 8 | `wet_area_count`, `wet_area_area`, `wet_area_waterproofing`, `wet_area_finish` | Conteo áreas húmedas + reglas | 07 |
| 9 | `kitchen_count`, `kitchen_area` + derivados `wet_area_waterproofing` vía `kitchen_count_standard` | Quantifier + reglas | 07 (impermeabilización cocina) |
|10 | `stair_count` | Quantifier escaleras | 02 |
|11 | `fixture_count` (si `discipline` eléctrica o tipos en `_ELECTRICAL_FIXTURE_TYPES`) | Vision/fixtures | 06 |

**PARTIDAS QUE PRES TIENE Y EL SISTEMA NO GENERA COMO PARTIDAS ESPECÍFICAS (brecha nominal):**

- Partidas **nombradas** tipo PRES: *“Muro Bloques 15x20x40 SNP …”*, *“Columna C1 0.50 x 0.50 - 16 ø1" …”*, *“Salida de tomacorrientes doble 110V …”*, *“Inodoro ECO”*, acabados de losa/viga con espesor de pañete, etc. El sistema hoy emite **takeoffs genéricos** (`wall_net_area`, `fixture_count`, …) salvo que Vision/CAD rellenen `inputs` (espesor, rotulo C1, tipo de aparato). No hay expansión automática a “Muro C1 bloque 15 cm” sin ese dato en inventario.
- **`wet_area_fixture_count`:** aparece en `agents/classifier_agent.py`, `knowledge/training_data.py` y filtros de disciplina, pero **`agents/quantifier_agent.py` no emite** este `item_type` (grep sin matches). Es un **gap de generación** frente al modelo mental del clasificador/entrenamiento.

**COBERTURA:** No calculable como “X de 1565” sin alinear semánticamente PRES con takeoffs (no existe herramienta en repo para ese diff). **Cualquier porcentaje sería especulativo;** lo honesto es asumir cobertura **baja** en partidas **específicas** y **moderada** solo en **familias** (m2 muro, m2 piso, ud puerta, etc.).

---

### DISCIPLINA: Estructural

**PARTIDAS QUE EL SISTEMA PUEDE GENERAR HOY:**

| # | Tipo | Origen | Capítulo |
|---|------|--------|----------|
| 1 | `structural_count`, `structural_length`, `structural_area`, `structural_volume` | `StructuralElement` en quantifier | 02 |
| 2 | `beam_length` → `beam_concrete_volume`, `beam_formwork_area_hint` | Regla `beam_length_concrete_standard` (sección **asumida** 0.30×0.50) | 02 |
| 3 | `column_length` / `structural_count`+`column` → `column_concrete_volume`, `column_formwork_area_hint` | Reglas con **sección/piso asumidos** (0.40×0.40, 2.80 m) | 02 |
| 4 | `slab_area` → `slab_concrete_volume`, `slab_formwork_area_hint` | Espesor losa **asumido** 0.20 m | 02 |
| 5 | `{beam,column,slab,footing}_reinforcement_kg` | **Ratios kg/m³** en `_REBAR_KG_PER_M3` cuando hay volumen/hints | 02 |
| 6 | `footing_*` (volumen, encofrado, acero) | Solo si el inventario tiene `StructuralElement` `element_type=="footing"` con geometría; **no** hay regla JSON tipo “zapata estándar” en el trozo auditado de `default_rules.json` | 02 |
| 7 | `stair_count` | Escaleras como entidad; **sin** pack estructural automático de hormigón/encofrado de escalera en las mismas reglas que vigas | 02 (capítulo) pero **detalle estructural limitado** |

**PARTIDAS PRES vs sistema:**

- PRES incluye columnas con **armadura explícita** (ej. *Columna C1 … 16 ø1", estribos*). El sistema **no reproduce** esa descomposición salvo que Vision/`ReinforcementDetail` alimente el quantifier; si no, solo hay **concreto/encofrado por defectos** y **kg acero estimado** por ratio.
- Zapatas, plateas, muros HA (MH1, MH2), muros de contención con armadura: **parcialmente** cubiertos solo si aparecen como elementos estructurales en inventario; no como catálogo de tipos MH1/MH2.

**COBERTURA:** Misma reserva que arquitectura; además, muchas líneas PRES son **cuantía + especificación** acoplada; el pipeline separa **cantidad genérica** y **match BC3** que puede ser aproximado.

---

### DISCIPLINA: Eléctrica

**PARTIDAS QUE EL SISTEMA PUEDE GENERAR HOY:**

- Principalmente `fixture_count` con `fixture_type` en el conjunto de `disciplines/electrico/quantifier.py` (tomacorrientes, interruptores, luminarias, panel, etc.) **o** `discipline == "electrical"` en inputs.
- Origen: entidades `Fixture` en `LevelInventory`, pobladas desde Vision (`agents/vision_agent.py`: bloque `fixtures` + listas eléctricas adicionales en el adaptador).

**PARTIDAS PRES vs sistema:**

- PRES tiene partidas finas (*Salida de tomacorrientes doble 110V*, *220V*, *208V 3f*, etc.). El sistema depende de que Vision asigne `fixture_type` y recuentos; **no** hay en `default_rules.json` expansión por calibre/circuito.
- Canalización, cable por m, tableros detallados: **no** vistos como takeoffs dedicados en quantifier (solo vía `fixture_count` genérico o ausentes).

**COBERTURA:** Esperable **muy baja** frente a 1565 partidas PRES sin calibración fuerte de Vision; a nivel **familia** (puntos eléctricos) puede haber algo si los planos etiquetan bien.

---

### DISCIPLINA: Sanitaria / plomería

**PARTIDAS QUE EL SISTEMA PUEDE GENERAR HOY:**

- `wet_area_*`, `floor_waterproofing` (áreas húmedas), `kitchen_*` impermeabilización.
- `fixture_count` con `fixture_type` plomería (`toilet`, `sink`, …) o `discipline == "plumbing"` (`disciplines/sanitario/quantifier.py`).

**PARTIDAS PRES vs sistema:**

- Tubería por diámetro (1/2", 3/4", drenaje 4"): **no** hay `item_type` dedicado en quantifier auditado.
- Piezas sanitarias específicas en PRES (*Inodoro ECO*): requieren match BC3 desde `fixture_count` genérico; descripción presupuestal puede quedar **genérica** en `build_budget_summary`.

**COBERTURA:** Similar a eléctrica — baja a nivel partida PRES, salvo mojones por baño/cocina.

---

## SECCIÓN 2: Auditoría de cuantificación

**Nota:** No se compararon cantidades numéricas con PRES (prohibición de ejecutar pipeline + ausencia de diff). Los casos siguientes son **por diseño de código**.

### Grupo A — Superficies y acabados arquitectónicos

**PARTIDA:** `wall_net_area` (y derivados yeso/pintura)  
- **¿De dónde sale la cantidad?** JSON/híbrido: geometría de muros en inventario; a veces Vision refuerza. **Reglas** duplican caras (factor 2 para yeso/pintura en estrategias `conditional_faces`).  
- **Unidad:** m2 — alineada con BC3 típico de muros/acabados.  
- **Plausible vs PRES:** Depende de medición APS vs método PRES; **no auditado numéricamente**.

**PARTIDA:** `wall_length` → yeso/pintura con factor **5.6**  
- **¿De dónde sale?** Longitud medida + **altura 2.80 m hardcoded** (`wall_length_finish_standard`).  
- **Unidad:** m2 resultante — OK.  
- **Plausible:** **Parcial** si altura real ≠ 2.80 m (error sistemático).

**PARTIDA:** `wet_area_count` → `wet_area_waterproofing` / `wet_area_finish`  
- **¿De dónde sale?** Conteo de baños × **5.0 m² promedio hardcoded** (`wet_area_count_standard`).  
- **Unidad:** m2 — OK.  
- **Plausible:** **Bajo/riesgo alto** si baños reales difieren del promedio.

**PARTIDA:** `kitchen_count` → impermeabilización × **4.0 m²**  
- **Hardcoded** (`kitchen_count_standard`). Misma advertencia.

### Grupo B — Estructura

**PARTIDA:** `beam_concrete_volume` desde `beam_length`  
- **Factor 0.15 m²** (0.30×0.50 **asumido**).  
- **Unidad:** m3 — OK.  
- **Plausible:** **No** si la viga real no es 0.30×0.50.

**PARTIDA:** `column_concrete_volume` desde `structural_count`+`column`  
- **0.448 m³ por columna** (0.40×0.40×2.80).  
- **Plausible:** **No** para columnas C1/C2 PRES con secciones distintas (ej. 0.50×0.50 en muestra PRES).

**PARTIDA:** `{element}_reinforcement_kg`  
- **Derivada** de volumen × **ratio fijo** por tipo (beam 100, column 120, … kg/m³).  
- **Unidad:** kg — típica BC3 acero.  
- **Plausible:** **Parcial** sin despiece; **no** sustituye armado del plano.

### Grupo C — Instalaciones

**PARTIDA:** `fixture_count`  
- **¿De dónde sale?** `fixture.count` en inventario (Vision).  
- **Unidad:** `fixture.unit` (a menudo `unit`).  
- **BC3:** puede exigir `ud` vs `ml` — posible **mismatch** si catálogo y takeoff difieren (flag opcional `budget_bc3_strict_units` en compositor).

---

## SECCIÓN 3: Auditoría de catalogación BC3

**Flujo:** `match_takeoffs_to_bc3` (`agents/classifier_agent.py`) agrupa por capítulo `_assign_chapter`, filtra ítems BC3 por tokens o **embeddings**, y con API usa GPT-4o para elegir código. Sin API: ranking determinista.

**Para cada takeoff:**

- **¿Match en BC3?** Si hay candidato fuerte (`select_strong_candidate`) y pasa `_guard_budget_candidate` (código existe en catálogo). Si no: `default_bc3_code_for_takeoff` o **`DUP-xxxx`** (`budget/composer.py`).
- **Precio:** En clasificador, si `catalog_price > 0`, se **fuerza** al precio catálogo (no confiar en modelo). Si precio catálogo es 0: `sin_precio_bc3` en rationale; `unit_price` queda 0 en esa ruta.
- **Composición:** `_extract_unit_price` usa rationale → catálogo por código → **ConstruCosto** fuzzy sobre resumen. Eso puede **asignar precio no-BC3** si hay snapshot ConstruCosto — no es “inventar” en sentido aleatorio, pero **sí** fuente externa al BC3 del proyecto.
- **¿Match semántico correcto?** **No verificable** estáticamente; depende de embeddings + prompt + calidad del resumen del takeoff (suele ser **genérico**).
- **Capítulo vs disciplina BC3:** Mapa estático incluye anomalías (ej. `floor_waterproofing` → capítulo **07**), coherente con “impermeabilización tipo sanitario” en la taxonomía interna, pero puede **chocar** con expectativa de usuario (pisos cap. 04).

---

## SECCIÓN 4: Verificación de separación disciplinaria

### Contaminación cruzada

1. **`fixture_count` sin `discipline` en inputs:**  
   - `_assign_chapter` → capítulo **06** vía `_ITEM_TYPE_TO_CHAPTER["fixture_count"]`.  
   - `infer_source_discipline` → **`arquitectonica`** si no hay `discipline` en takeoff ni `discipline_id` global útil.  
   → **Incoherencia:** línea bajo capítulo eléctrico con metadata `source_discipline` arquitectónica. `run_budget_validation` (V1) puede marcar **capítulo vs disciplina** si se activa.

2. **`floor_waterproofing` en reglas de piso húmedo** clasificado en **07**: mezcla lógica “piso” con capítulo sanitario; puede ser intencional pero es **difícil de explicar** frente a PRES jerárquico.

3. **Muros estructura vs arquitectura:**  
   - Muros en CAD pueden tener `structural` y alimentar volumen muro; elementos `StructuralElement` generan hormigón cap. 02. **Riesgo de doble conteo** si el mismo muro existe como `Wall` y como elemento estructural sin deduplicación explícita (depende de `build_hybrid_inventory` / fuentes).

4. **Sanitario vs arquitectura:** Baños como `WetArea` + fixtures plomería; puertas de baño como `door_count`. Riesgo de solapamiento **bajo** si reglas no duplican “acabado baño” y “área húmeda” con la misma superficie (posible **doble m2** conceptual).

### Duplicados

- **Rules engine:** un `wall_net_area` puede generar **yeso + pintura** (dos líneas) — no es error, es desglose.
- **Derivados:** trazas con `derived_from` y exclusiones en `budget_filter_sets` intentan evitar doble presupuestación de volúmenes derivados; requiere E2E para validar que no queden **dos capas de encofrado** por la misma viga desde rutas distintas.
- **PRES template:** `pres_template_takeoffs` puede **inyectar** takeoffs sintéticos además de medidos — duplicación **si se activa** sin cuidado.

**`classifier_agent.py`:** No contiene validación dura “disciplina → capítulo” antes de GPT; la separación depende de `_assign_chapter` + prompts + validación posterior opcional.

---

## SECCIÓN 5: Auditoría de jerarquía de capítulos (Excel)

**Export:** `budget/export_excel.py` — hoja principal `Presupuesto` (por defecto), columnas alineadas a PRES (`Código, Nat, Ud, Resumen, CanPres, PrPres, ImpPres`). Capítulos como filas `Nat == "Capítulo"`; jerarquía interna viene de `compose_budget_rows` (`chapter_path`).

| Pregunta | Hallazgo |
|----------|----------|
| ¿Sub-capítulos? | Sí, si `chapter_path` tiene varios segmentos; con `use_bc3_catalog_chapters` puede reflejar descomposición del BC3. |
| ¿Partidas específicas? | A menudo **genéricas** en resumen si el takeoff no lleva rotulo/espesor (problema producto). |
| ¿Código BC3? | Sí si candidato válido o default map; si no, `DUP-xxxx`. |
| ¿Precio BC3? | Sí si catálogo tiene precio; 0 si no; ConstruCosto puede rellenar. |
| Pestañas VALIDACIÓN / PENDIENTES | **No** implementadas en `export_excel.py` auditado; existe `Quality_Report` opcional si se pasa `quality_report`. |

---

## SECCIÓN 6: Elementos faltantes por disciplina (frente a PRES como referencia)

### ARQUITECTÓNICA — FALTANTES (nominal)

- Revestimientos cerámicos **por tipo y altura** (más allá de `wall_finish_tile` genérico).
- Cielos rasos **por sistema** y áreas no genéricas.
- Cocina: tope granito, gabinetes (ml o ud) — no vistos como takeoffs dedicados.
- Terminación de escaleras (huella/contrahuella, barandas) salvo lo que Vision enumere.
- Partidas PRES de **exterior / misc** y capítulos intermedios (PRES usa muchos capítulos TGIU además de 01–09 Dupla).

### ESTRUCTURAL — FALTANTES

- Zapatas y plateas con **tipología PRES** (excavación + hormigón + acero por elemento).
- Columnas/vigas/losas con **armadura como en PRES** (sin Vision estructural fuerte → solo defaults).
- Muros HA y muros de contención con **doble capa** arq/est si no se deduplica.
- Encofrados y losas especiales más allá de factores fijos.

### ELÉCTRICA — FALTANTES

- Tomacorrientes por **voltaje/tipo** como partidas separadas automáticas.
- Luminarias por tipo, canalización por m, cable por calibre, tableros detallados, acometida.
- Salidas datos/TV/teléfono salvo fixture types que Vision rellene.

### SANITARIA — FALTANTES

- Tubería por diámetro y longitud.
- Registros, válvulas, cisterna, bombeo, fuego — salvo aparición como fixtures genéricos.
- `wet_area_fixture_count` **no generado** por quantifier principal (gap).

---

## SECCIÓN 7: Resumen ejecutivo con puntuación

**SCORECARD (subjetivo, escala evidencia en código; no validación numérica PRES):**

| Disciplina | Generación | Cuantificación | Catalogación | Separación | Total |
|------------|------------|----------------|--------------|------------|-------|
| Arquitectónica | 5/10 | 4/10 | 5/10 | 5/10 | **19/40** |
| Estructural | 4/10 | 3/10 | 4/10 | 4/10 | **15/40** |
| Eléctrica | 3/10 | 3/10 | 4/10 | 4/10 | **14/40** |
| Sanitaria | 3/10 | 3/10 | 4/10 | 4/10 | **14/40** |

**BLOQUEANTES PARA E2E “de señal útil” (no necesariamente bloquean *ejecutar* código):**

1. **Ausencia de criterio de éxito cuantitativo** vs PRES (diff por capítulo/código).
2. **`upload_discipline_id` no cableado** en `dupla_run_full_analysis_local.py` → Vision sin verdad de disciplina en corrida local típica.
3. **Defaults agresivos** (áreas húmedas 5 m², cocina 4 m², secciones viga/columna) → E2E puede dar **órdenes de magnitud incorrectos** si se interpretan como presupuesto final.

**WARNINGS:**

1. **`wet_area_fixture_count`** referenciado pero no producido por el quantifier monolítico.
2. **Metadata `source_discipline` vs capítulo asignado** en fixtures sin `discipline`.
3. **ConstruCosto** puede mezclar precios fuera del BC3 del cliente.
4. **Capítulo 09** como comodín para item_types no mapeados → riesgo de mezclar residuos con “Gastos generales” reales.

**VEREDICTO:** ¿Listo para E2E? **SÍ para E2E técnico** (el pipeline corre); **NO para E2E como validación de negocio frente a PRES** sin: corrida acotada, métricas, revisión manual de `DUP-*`, y activación consciente de flags (`run_budget_validation`, `use_bc3_catalog_chapters`, disciplina explícita).

---

## Tabla de acciones priorizadas (impacto / esfuerzo estimado)

| Prioridad | Acción | Impacto | Esfuerzo |
|-----------|--------|---------|----------|
| P0 | Definir **subset de páginas + disciplina** y pasar **`upload_discipline_id`** en el script local usado para E2E | Coherencia Vision/reglas | Bajo |
| P0 | Script o notebook de **diff PRES vs output** (por código BC3 y por familia de resumen) | Saber si E2E sirve | Medio |
| P1 | Corregir **emisión o eliminación** de `wet_area_fixture_count` (quantifier vs clasificador) | Alineación sanitario | Bajo–medio |
| P1 | Unificar **fixture_count: disciplina inferida vs capítulo** (clasificador o `infer_source_discipline`) | Menos falsos V1 | Medio |
| P2 | Sustituir promedios **5 m² / 4 m²** por áreas Vision o CAD cuando existan | Cuantías húmedas | Medio |
| P2 | Enriquecer resúmenes con **rotulos estructurales** (`schedule_row_text`, etc.) ya previstos en Vision | Partidas menos genéricas | Medio |
| P3 | Pestañas Excel **VALIDACIÓN / PENDIENTES** desde `budget_validation` y `DUP-*` | Revisión humana | Medio |

---

*Generado según `cursor_prompt_audit_pre_e2e.md` — solo lectura de código y datos; sin modificación de archivos de implementación.*
