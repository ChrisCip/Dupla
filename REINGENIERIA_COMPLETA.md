# Reingeniería Completa — Sistema Dupla de Presupuestos de Construcción con IA

## 1. Resumen Ejecutivo

Dupla es un sistema en Python orientado a **presupuestos de obra** (República Dominicana y lógica de negocio alineada a flujos tipo Presto/FIEBDC). Toma como entrada principal **planimetría en DWG** (vía **Autodesk Platform Services**, APS) y **representación visual** de los planos (PDF rasterizado a imágenes o carpeta de imágenes). Extrae un inventario híbrido **CAD + visión (GPT-4o)**, lo convierte en **mediciones (takeoffs)** deterministas, empareja cada medición con **partidas de un catálogo BC3** (y opcionalmente ejemplos de un Excel de referencia tipo **PRES.xlsx**), y compone un **presupuesto** exportable a **Excel** y a **archivo BC3** para herramientas compatibles con FIEBDC.

El repositorio combina un **pipeline por etapas** (`core/stage.py` → `PipelineRunner`) con módulos especializados (`aps_integration`, `processors`, `agents`, `budget`, `knowledge`, `rules_engine`). Hay **código heredado** bajo `_legacy/` y **automatización CAD histórica** parcial; la arquitectura **activa** está documentada en comentarios de `dupla_run_full_analysis_local.py` y `core/pipeline.py` (APS/JSON-first).

**Estado actual (solo lectura de código y tests):** la suite `tests/` ejecutada con el intérprete del proyecto reportó **76 pruebas pasando** en ~50 s. **No se ejecutó** en este análisis una corrida completa contra APS ni OpenAI con credenciales reales; la descripción de APIs se basa en el código fuente.

---

## 2. Problema de Negocio

- **Qué proceso manual reemplaza:** lectura de planos (DWG/PDF), conteo y medición de elementos constructivos, desglose por capítulos/partidas, asignación de códigos y precios de un catálogo corporativo (BC3), y armado de una hoja de presupuesto revisable.
- **Quién es el usuario final:** presupuestista / ingeniero de costos / oficina técnica que trabaja con catálogo BC3 y Excel, y que puede importar resultados a **Presto** u otras herramientas FIEBDC.
- **Qué inputs tiene disponibles el usuario:** archivo **DWG**; **PDF** de planos o **imágenes** ya renderizadas; archivo **BC3** de precios; opcionalmente **PRES.xlsx** (presupuesto histórico) para *few-shot* y metodología automática; variables **`.env`** con credenciales APS y OpenAI.
- **Qué output espera recibir:** Excel con columnas tipo presupuesto (`budget/export_excel.py` → `HEADERS`: Código, Nat, Ud, Resumen, CanPres, PrPres, ImpPres), un Excel de **revisión** (`dupla_budget_for_review.xlsx`), JSON intermedio de presupuesto, **BC3** generado (`budget/export_bc3.py`), y artefactos de depuración (`pipeline_report.json`, `dupla_debug.log`, JSON de Autodesk normalizado, `vision_inventory_results.json`).
- **Qué valor genera la automatización:** reduce el tiempo de lectura de planos al combinar extracción geométrica/propiedades del DWG con interpretación visual; estandariza el inventario en esquemas (`core/schemas.py`); traza cantidades con fórmulas y evidencia; propone códigos BC3 con modelo de lenguaje acotado al catálogo.

---

## 3. Arquitectura General

### Diagrama de bloques (ASCII)

```
                    +------------------+
                    |  DWG (local)     |
                    +--------+---------+
                             |
              +--------------v--------------+
              |  APS: OSS upload +         |
              |  Model Derivative (SVF2)   |
              |  aps_integration/          |
              +--------------+--------------+
                             | raw JSON
              +--------------v--------------+
              |  process_autodesk_json()    |
              |  processors/json_processor  |
              +--------------+--------------+
                             | cad_facts (normalizado)
         +-------------------+-------------------+
         |                                       |
+--------v---------+                    +--------v---------+
| PDF / imágenes   |                    | Misma ruta       |
| PyMuPDF render   |                    | cad_facts inyect |
| dupla_run_*      |                    | en prompts       |
+--------+---------+                    +--------+---------+
         |                                       |
         +-------------------+-------------------+
                             |
              +--------------v--------------+
              |  run_full_vision_analysis() |
              |  agents/vision_agent.py      |
              |  GPT-4o visión → JSON       |
              |  → LevelInventory (adaptador)|
              +--------------+--------------+
                             | vision_results[]
              +--------------v--------------+
              |  build_hybrid_inventory()   |
              |  core/inventory_builder     |
              +--------------+--------------+
                             |
              +--------------v--------------+
              |  quantify_inventory()       |
              |  agents/quantifier_agent    |
              +--------------+--------------+
                             |
              +--------------v--------------+
              |  RulesEngine.apply()        |
              |  rules_engine/              |
              +--------------+--------------+
                             |
              +--------------v--------------+
              |  match_takeoffs_to_bc3()    |
              |  agents/classifier_agent    |
              |  (+ embeddings opcional)    |
              +--------------+--------------+
                             |
              +--------------v--------------+
              |  compose_budget()           |
              |  budget/composer.py          |
              +--------------+--------------+
                             |
         +-------------------+-------------------+
         |                                       |
+--------v---------+                    +--------v---------+
| export_budget_   |                    | export_budget_   |
| workbook()       |                    | bc3()            |
| budget/export_   |                    | budget/export_   |
| excel.py         |                    | bc3.py           |
+------------------+                    +------------------+
```

### Stack tecnológico

- **Lenguaje:** Python 3 (el repo usa tipado moderno `list[str]`, `|` union).
- **Librerías principales (requirements.txt):** `openai`, `python-dotenv`, `requests`, `pytest`, `openpyxl`, `pymupdf`, `pyyaml`.
- **NumPy:** usado en `knowledge/bc3_embeddings.py` (vectores).
- **APIs externas:** Autodesk APS (OAuth 2-legged, OSS v2, Model Derivative v2); OpenAI (Chat Completions `gpt-4o`, Embeddings `text-embedding-3-small` por defecto).
- **Bases de datos:** ninguna persistente en el núcleo; caché de embeddings en disco bajo `knowledge/cache/`.
- **Almacenamiento de archivos:** salidas bajo `output/` o rutas configuradas; buckets OSS **transient** (`aps_integration/oss_manager.py` → `policyKey: transient`).

### Patrón arquitectónico

**Monolito modular tipo pipeline batch:** un solo proceso Python orquesta etapas secuenciales con acoplamiento por archivos JSON/Excel y objetos en memoria. No hay servidor HTTP de producción en el núcleo analizado; los *runners* son scripts CLI.

### Decisiones de arquitectura clave (solo hechos)

- **Híbrido CAD + visión:** el merge explícito vive en `build_level_inventory()` (`core/inventory_builder.py`): JSON/CAD preferido en ciertos campos, visión priorizada en otros (p. ej. `floor_area_m2`, `area_m2` en muros).
- **Dos pasos en visión:** prompt “simple” + adaptador Python (`agents/vision_agent.py`) para no forzar al modelo a rellenar el esquema largo de `LevelInventory` directamente.
- **Clasificación BC3 por capítulos:** `agents/classifier_agent.py` agrupa takeoffs en 9 capítulos heurísticos y llama a GPT-4o **una vez por capítulo** con un subconjunto del catálogo filtrado.
- **Reglas deterministas post-cuantificación:** `rules_engine/` expande takeoffs base según `rules_engine/default_rules.json`.

---

## 4. Estructura del Repositorio

Árbol **anotado** (carpetas relevantes; **no** se listan aquí todos los binarios DWG/PDF/PNG del repo).

```
Dupla/
├── dupla_run_full_analysis_local.py   # Runner principal documentado (APS + visión + presupuesto)
├── compare_budget.py                  # CLI: comparar Excel generado vs PRES de referencia
├── requirements.txt                   # Dependencias del núcleo activo
├── requirements-legacy.txt            # Dependencias heredadas (si se usa _legacy)
├── .env                               # CLIENT_ID, CLIENT_SECRET, APS_BUCKET_NAME, OPENAI_API_KEY (no versionar secretos)
├── agents/
│   ├── vision_agent.py                # GPT-4o visión + adaptador a LevelInventory
│   ├── vision_profiles.py             # Perfiles structural|electrical|sanitary|finishes_architectural|general
│   ├── classifier_agent.py            # match_takeoffs_to_bc3 (GPT-4o por capítulo o fallback tokens)
│   └── quantifier_agent.py            # quantify_inventory: inventario → QuantityTakeoff
├── aps_integration/
│   ├── aps_auth.py                    # get_aps_token() → OAuth client_credentials
│   ├── oss_manager.py                 # create_bucket, upload_file_to_bucket, signed URLs
│   ├── model_derivative.py            # extract_dwg_data(): traducción + propiedades + ensamblado JSON
│   ├── da_manager.py, build_plugin.py # Utilidades/extensiones (no son el núcleo del runner principal)
│   └── DuplaExtractor/                # Proyecto .NET (extractor/plugin Autodesk) — conviven en repo
├── budget/
│   ├── composer.py                    # compose_budget() → chapters, lines, rows
│   ├── chapter_rules.py               # select_strong_candidate, chapter_path_for_takeoff, ...
│   ├── export_excel.py                # export_budget_workbook()
│   ├── export_bc3.py                  # export_budget_bc3() FIEBDC-3
│   ├── discipline_mapping.py        # Claves de disciplina y mapas a capítulos/heurísticas
│   └── presto_constants.py            # Constantes relacionadas Presto (tests dedicados)
├── core/
│   ├── pipeline.py                    # build_budget_from_sources, build_hybrid_inventory, bootstrap_pipeline_inputs
│   ├── stage.py                       # PipelineRunner, StageResult, PipelineReport
│   ├── schemas.py                     # Dataclasses: ProjectContext, LevelInventory, QuantityTakeoff, ...
│   ├── inventory_builder.py         # build_json_inventory, build_level_inventory, GPT capas CAD opcional
│   └── logging_config.py              # setup_logging()
├── knowledge/
│   ├── bc3_embeddings.py            # EmbeddingIndex, load_or_build_embeddings, search_bc3
│   ├── training_data.py             # TrainingPair, extract_training_pairs (PRES.xlsx)
│   ├── methodology_generator.py     # generate_methodology_context() para inyectar en visión
│   ├── pres_expansion.py            # synthetic_takeoffs_from_pres, inject_pres_reference_candidates
│   ├── few_shot_policy.py           # Políticas auxiliares few-shot (importado donde aplica)
│   ├── office_methodology.md        # Metodología manual opcional (ruta configurable)
│   └── cache/                       # Caché npz/json de embeddings BC3
├── processors/
│   ├── json_processor.py            # process_autodesk_json()
│   └── bc3_parser.py                # parse_bc3()
├── pipeline/
│   └── project_manifest.py          # ProjectManifest, load_project_manifest, validate_manifest
│   └── pdf_discipline_split.py      # Clasificación de páginas PDF por disciplina (GPT-4o)
├── rules_engine/
│   ├── __init__.py                  # RulesEngine, default_rules_engine
│   ├── registry.py                  # load_rule_registry, estrategias surface_multiplier, etc.
│   └── default_rules.json           # Reglas declarativas
├── scripts/                         # Runners especializados (BLCAD, auditorías, verificación APS)
├── tests/                           # Pytest (30 módulos)
├── inputs/projects/                 # YAML de proyecto (example_project.yaml, mi.yaml)
├── data/                            # RTF Presto de ejemplo; BC3 de ejemplo referenciado en YAML puede no estar presente
├── examples/                        # JSON de muestra (inventarios, salidas de motor de reglas)
├── output/                          # Salidas de corridas (históricas en el workspace)
├── comparisons/budget/              # Corridas de comparación y difs markdown/xlsx
├── config/                          # layer_mapping.py (mapeo capas)
├── analysis/, analysis_output/, api_results/  # Artefactos de análisis / resultados API
├── _legacy/                         # Scripts y CAD automation antiguos
├── cad_automation/                  # Carpeta presente en listado de directorio (vacía o sin archivos según glob)
├── BLCAD09/, BLCAD14/               # Lotes de DWG/PDF de prueba del usuario
└── Documentación markdown existente: README.md, TECHNICAL_DOCS.md, SRS.md, etc. (no son este documento)
```

---

## 5. Pipeline Principal — Flujo Completo Paso a Paso

**Runner de referencia:** `dupla_run_full_analysis_local.py` → función `main()` → `PipelineRunner("dupla_full_analysis")`.

**Orden real de etapas en `main()`** (importante: `knowledge_inputs` corre **antes** que `vision_analysis` para generar `auto_methodology`):

---

### 5.1 Etapa: `aps_extraction`

- **Archivo(s):** `dupla_run_full_analysis_local.py` → `stage_aps_extraction()`; `aps_integration/aps_auth.py`, `aps_integration/oss_manager.py`, `aps_integration/model_derivative.py`, `processors/json_processor.py`.
- **Función principal:**  
  `stage_aps_extraction(dwg_path: Path, outputs_dir: Path, bucket_name: str) -> dict`
- **Input:**
  - `dwg_path`: ruta al DWG local.
  - `outputs_dir`: directorio de corrida.
  - `bucket_name`: nombre de bucket OSS (desde `RUN.bucket_name` o `APS_BUCKET_NAME`).
  - Usa globales `RUN` (`SimpleNamespace`): `translation_views`, timeouts, `upload_object_name`, `auto_unique_object_name`, etc.
- **Procesamiento (lógica):**
  1. `get_aps_token()` — si faltan `CLIENT_ID`/`CLIENT_SECRET` en `.env`, lanza `ValueError`.
  2. `create_bucket(token, bucket_name)` — POST bucket transient; 409 si ya existe es aceptable.
  3. `upload_file_to_bucket(...)` — nombre de objeto con sufijo único opcional.
  4. `extract_dwg_data(token, bucket_name, object_name, views=..., translation_timeout_seconds=..., ...)` — traducción SVF2, lectura de manifiesto y propiedades; devuelve dict JSON grande.
  5. Escribe `{stem}.autodesk_raw.json`.
  6. `process_autodesk_json(str(raw_json_path))` — normaliza a hechos CAD; escribe `{stem}.normalized.json`.
- **Output (`dict`):**
  - `"cad_facts"`: resultado **completo** de `process_autodesk_json` (incluye `project`, `total_objects`, `cad_facts` anidado, `inventory_hints`).
  - `"raw_json_path"`, `"normalized_json_path"`: `Path`.
  - `"uploaded_object_name"`: `str`.
- **Efectos secundarios:** escritura de JSON; impresiones en consola desde APS (`print` en `model_derivative`, `oss_manager`, `aps_auth`).
- **Errores:** cualquier excepción no capturada hace que `PipelineRunner.run_stage` marque `status="error"` y guarde traceback en `StageResult.errors`; `main()` llama `_finish()` y termina sin etapas posteriores.
- **Decisiones de diseño en esta etapa:** traducción por defecto **2D** (`TRANSLATION_VIEWS = ("2d",)` en CONFIG) para DWGs grandes; bucket **transient**.

---

### 5.2 Etapa: `vision_pages`

- **Archivo(s):** `dupla_run_full_analysis_local.py` → `stage_resolve_pages(outputs_dir: Path) -> dict`; `render_pdf_to_images()` (PyMuPDF).
- **Input:** estado global `RUN` (`use_pdf`, `pdf_path`, `images_dir`, `vision_sources` multi-PDF multi-disciplina).
- **Procesamiento:**
  - Si `RUN.vision_sources` no vacío: por cada `VisionSourceSpec` renderiza PDF o usa `images_dir`; produce `bundles` con `pages_dir`, `discipline`, `page_count`.
  - Si no multi: con `USE_PDF` renderiza a `outputs_dir/rendered_pages/p_<sha256[:16]>/page_XXXX.png` (hash por ruta PDF para evitar MAX_PATH).
  - Sin PDF: cuenta imágenes en carpeta.
- **Output:** `dict` con claves `multi` (bool), `bundles` (lista), `page_count`, `source` (`"pdf"|"directory"|"multi_input"`), `pages_dir` (primera carpeta si multi).
- **Errores:** `FileNotFoundError` si falta PDF/carpeta; `ValueError` si entrada multi incompleta.

---

### 5.3 Etapa: `knowledge_inputs`

- **Archivo(s):** `dupla_run_full_analysis_local.py` → `stage_knowledge_inputs(outputs_dir: Path) -> dict`.
- **Funciones:** `parse_bc3`, `extract_training_pairs`, `load_or_build_embeddings`, `generate_methodology_context`.
- **Input:** `RUN.bc3_path`, `RUN.xlsx_training_path` (puede omitirse con convención `__no_pres_training*`).
- **Procesamiento:** carga BC3; pares de entrenamiento desde XLSX; embeddings si hay ítems BC3; genera texto `auto_methodology`.
- **Output:** `bc3_catalog`, `bc3_path_value`, `training_pairs`, `embedding_index`, `xlsx_training_path`, `auto_methodology`.
- **Errores:** `FileNotFoundError` si BC3 configurado pero ausente. Si no hay XLSX, continúa con lista vacía y *path* ficticio `_skipped_training.xlsx` para logging.

---

### 5.4 Etapa: `vision_analysis`

- **Archivo(s):** `dupla_run_full_analysis_local.py` → `stage_vision_analysis(pages_input, cad_facts, outputs_dir, *, auto_methodology=None) -> dict`; `agents/vision_agent.py` → `run_full_vision_analysis()`.
- **Función interna clave:**  
  `run_full_vision_analysis(pages_dir: str, cad_summary: dict[str, Any], *, office_methodology: str | None = None, vision_profile_key: str | None = None) -> list[dict[str, Any]]`  
  `analyze_plan(image_path: Path, cad_summary: dict[str, Any], level_name: str, *, office_methodology: str | None = None, vision_profile_key: str | None = None) -> dict[str, Any]`
- **Input:**
  - `pages_input`: `Path` o `dict` multi-bundle (desde etapa 5.2).
  - `cad_facts`: mismas estructuras que usa `format_cad_facts_for_prompt` (espera claves de primer nivel `cad_facts` e `inventory_hints` como en salida de `process_autodesk_json`).
  - Metodología: `_load_office_methodology(OFFICE_METHODOLOGY_PATH)` + `auto_methodology` de etapa 5.3.
- **Procesamiento:** por cada imagen, llamada OpenAI `client.chat.completions.create(model="gpt-4o", ...)`, parseo JSON, `_simple_to_level_inventory`, `level_inventory_from_dict`, *cross-checks*; en multi-disciplina añade `_metadata["source_discipline"]`.
- **Output:** dict con `vision_results` (lista), `vision_json_path`, conteos OK/error, `methodology_chars`. Escribe `vision_inventory_results.json` y opcionalmente `office_methodology_snapshot.md`.
- **Errores:** por imagen, excepciones capturadas en `run_full_vision_analysis` → elemento `{"error": "...", "file": "..."}` sin abortar toda la etapa. **Nota:** el pipeline **no** aborta si todas las páginas fallan; etapas posteriores pueden trabajar con listas vacías o con dicts con `"error"` (ver 5.5).

---

### 5.5 Etapa: `build_budget`

- **Archivo(s):** `dupla_run_full_analysis_local.py` → `stage_build_budget(...)`; `core/pipeline.py` → `build_budget_from_sources()`; `budget/composer.py`.
- **Función principal:**  
  `build_budget_from_sources(context: ProjectContext, cad_facts: dict[str, Any], vision_payloads: Iterable[LevelInventory | Mapping[str, Any]] | ..., bc3_catalog: dict[str, Any], rules_engine: RulesEngine | None = None, *, embedding_index: Any | None = None, training_pairs: list[Any] | None = None) -> dict[str, Any]`
- **Input (orden real de argumentos en `stage_build_budget`):**
  1. `cad_facts: dict`
  2. `vision_results: list`
  3. `bc3_catalog: dict`
  4. `embedding_index`
  5. `training_pairs: list`
  6. `raw_json_path: Path`
  7. `normalized_json_path: Path`
  8. `uploaded_object_name: str`
  9. `pages_resolution: Path | dict` (multi o simple)
  10. `xlsx_path: str | None`
  11. `outputs_dir: Path`
- **Procesamiento:**
  1. Construye `ProjectContext` con `metadata` rica (rutas DWG, JSON, directorio(s) de visión, flags APS, `pres_template_takeoffs`, `xlsx_path`).
  2. `build_budget_from_sources`:
     - `build_hybrid_inventory(cad_facts, vision_payloads)` → lista `LevelInventory`  
       - Si payload tiene `"error"`, **se omite** con warning (`core/pipeline.py`).
     - `build_expanded_takeoffs_from_inventory` → `quantify_inventory` + `RulesEngine.apply`.
     - `merge_pres_template_takeoffs` si metadata `pres_template_takeoffs`.
     - `match_takeoffs_to_bc3(...)`.
     - `build_final_budget` → `compose_budget`.
  3. Escribe `dupla_full_budget_output.json`.
- **Output:** dict con `budget` (estructura compuesta — ver §7), `context`, `budget_json_path`, `page_paths`.
- **Errores:** excepciones no manejadas → etapa en error. Si no hay vision válida, `build_hybrid_inventory` puede producir inventario solo CAD (`core/pipeline.py` ramas sin payloads).

---

### 5.6 Etapa: `excel_export`

- **Archivo(s):** `stage_excel_export(context: ProjectContext, budget: dict, outputs_dir: Path) -> dict`; `budget/export_excel.py` → `export_budget_workbook(context, rows=budget["rows"], output_path=...)`.
- **Output:** `saved_workbook_path`, `review_workbook_path` (`_save_for_review` crea hoja `Revision` con 12 columnas de revisión).

---

### 5.7 Etapa: `bc3_export`

- **Archivo(s):** `stage_bc3_export(...)`; `budget/export_bc3.py` → `export_budget_bc3(context, rows=budget["rows"], output_path=...)`.
- **Manejo de error en `main()`:** si falla, **solo** `logger.warning("BC3 export failed — continuing with Excel output only")` — el pipeline **no** considera esto error final automáticamente vía `PipelineRunner` salvo que `run_stage` capture excepción (sí marcaría error en esa etapa). El código actual registra advertencia implícitamente si la etapa devolviera error; revisar `main`: `if not s7.ok: logger.warning(...)`.

---

### 5.8 Cierre: `_finish`

- **Función:** `_finish(runner, outputs_dir, summary)` → `runner.report().save(outputs_dir / "pipeline_report.json")`; escribe `run_summary.json` antes desde `main`.

---

## 6. Módulos de Soporte

### 6.1 `core/`

- **Propósito:** orquestación, esquemas compartidos, merge inventario, utilidades de logging.
- **Archivos y funciones clave:** ver §4; `bootstrap_pipeline_inputs()` en `core/pipeline.py` carga CAD/BC3/embeddings/training sin visión (útil para tests o reutilización).
- **Integración:** llamado desde tests y potencialmente runners alternativos.
- **Configuración:** rutas en `ProjectContext.metadata`; reglas estrictas BC3 opcionales `budget_bc3_strict_units`.

### 6.2 `processors/`

- **Propósito:** normalizar entradas externas (JSON Autodesk, archivo BC3).
- **`process_autodesk_json(json_path: str) -> dict[str, Any]`:** recorre colección de objetos, agrupa por capa, extrae textos, cotas, sombreados, bloques, geometría ligera.
- **`parse_bc3(path: str) -> dict[str, Any]`:** lee BC3 con encoding `latin-1`; retorna `items` (con precio>0 y unidad), `chapters`, `concepts_by_code`, jerarquía, textos largos, mediciones.

### 6.3 `knowledge/`

- **Propósito:** embebidos BC3, ejemplos desde PRES, expansión PRES, metodología automática, caché.
- **`load_or_build_embeddings(bc3_catalog)`:** puede lanzar si falta `OPENAI_API_KEY` (según *embedder* por defecto).
- **`generate_methodology_context(training_pairs, bc3_catalog, max_chars=10000)`:** texto en español para contexto de visión.

### 6.4 `rules_engine/`

- **Propósito:** derivar takeoffs adicionales desde takeoffs base mediante reglas JSON (`default_rules.json`).
- **`RulesEngine.apply(takeoffs)`:** orden estable; evita duplicar `item_key`.

### 6.5 `budget/` (además de export/composer)

- **`chapter_rules.py`:** selección de candidato fuerte, rutas de capítulo, reglas de inclusión presupuestal.
- **`discipline_mapping.py`:** constantes `STRUCTURAL`, `ELECTRICAL`, `SANITARY`, `FINISHES_ARCH`, `GENERAL` y mapas a prefijos de capítulo del composer.

### 6.6 `pipeline/`

- **`project_manifest.py`:** YAML → `ProjectManifest` (ver ejemplo en `inputs/projects/example_project.yaml`).
- **`pdf_discipline_split.py`:** clasificación de página única con prompt `_DISCIPLINE_PROMPT` y salida JSON `discipline`, `title`.

### 6.7 `config/`

- **`layer_mapping.py`:** utilidades de mapeo de capas CAD (consumo según scripts/procesadores).

### 6.8 `scripts/` (runners auxiliares)

| Script | Rol resumido (desde docstrings/código) |
|--------|----------------------------------------|
| `run_prueba_web_01_full.py` | Orquesta lote BLCAD + PDF + GPT sin PRES; subprocesos a otros scripts |
| `run_merged_cad_pdf_vision.py` | CAD merge + PDF visión |
| `run_multi_dwg_project_cad.py` | Proyecto multi-DWG |
| `run_blcad09_discipline_pipeline.py` | Pipeline por disciplina BLCAD09 |
| `run_dw_pres_compare.py` | Comparación DW/PRES |
| `audit_extraction_part1.py` | Auditoría de extracción |
| `export_presentacion.py` | Export orientado a presentación |
| `verify_aps_setup.py` | Verificación de setup APS |

### 6.9 `aps_integration/` (soporte Design Automation / plugin)

- **`da_manager.py`, `build_plugin.py`, `DuplaExtractor/`:** piezas para extractor/plugin; el runner principal usa **REST** `model_derivative.py` sin exigir COM local.

### 6.10 `_legacy/`

- **Propósito:** código histórico (`run_pipeline.py`, `cad_automation`, etc.). **No** es el camino documentado en `dupla_run_full_analysis_local.py`.

### 6.11 `compare_budget.py`

- **Función CLI:** `main()` con argparse; compara filas de presupuesto generado vs real usando heurísticas de disciplina (`budget/discipline_mapping.py`).

---

## 7. Modelos de Datos

### 7.1 Esquemas internos (`core/schemas.py`)

**Dataclasses principales (kw_only, con `to_dict()`):**

- `ProjectContext`: `project_id`, `project_name`, `source_json_path`, `plan_image_paths`, `bc3_path`, `measurement_unit` (default `"m"`), `metadata: dict`.
- `LevelInventory`: `level_id`, `level_name`, `source` (`"json"|"vision"|"hybrid"`), listas de `Wall`, `Door`, `Window`, `WetArea`, `Kitchen`, `Stair`, `Fixture`, `StructuralElement`, `Opening`, notas, áreas, etc.
- `QuantityTakeoff`: `item_key`, `item_type`, `level_id`, `unit`, `quantity`, `formula`, `inputs`, `assumptions`, `source_refs`, `trace: QuantityTrace`.
- `BudgetCandidate`: `takeoff_key`, `bc3_code`, `summary`, `unit`, `score`, `rationale`, `source`.
- `BudgetRow`: `row_type` (`"chapter"|"line"|"subtotal"`), `code`, `nat`, `unit`, `summary`, `quantity`, `unit_price`, `amount`, jerarquía, `metadata`, `excel_row`.

**Ejemplo real (fragmento del repo):** `examples/sample_structural_inventory.json` muestra un `LevelInventory` serializado con muros, `cad_hints`, `space_types`, etc. (estructura alineada con `level_inventory_from_dict`).

**Helpers:** `project_context_from_dict`, `level_inventory_from_dict`.

---

### 7.2 Datos de entrada

| Archivo / tipo | Contenido | Estructura | Productor | Consumidor | Notas |
|----------------|-----------|------------|-----------|------------|-------|
| `.env` | Secretos APS y OpenAI | `CLIENT_ID`, `CLIENT_SECRET`, `APS_BUCKET_NAME`, `OPENAI_API_KEY` | Usuario | `aps_auth`, `oss_manager`, `vision_agent`, `bc3_embeddings` | No commitear |
| `inputs/projects/*.yaml` | Manifiesto de proyecto | `project_name`, `project_id`, `paths.*`, `vision.profile` o `vision.sources[]`, flags APS | Usuario | `pipeline/project_manifest.py` | Ejemplo: `inputs/projects/example_project.yaml` |
| DWG | Plano CAD | Binario | Usuario | APS upload | |
| PDF / PNG / JPG / WEBP | Planos raster | Binario / imágenes | Usuario o `render_pdf_to_images` | `vision_agent` | |
| BC3 | Catálogo FIEBDC | Texto registros `~C`, `~D`, `~T`, `~M`… | Presto/export externo | `parse_bc3` | Encoding `latin-1` en parser |
| PRES.xlsx (u otro xlsx) | Presupuesto histórico | Hoja 1; datos desde fila 4: col0 Código, col1 Nat, col2 Ud, col3 Resumen, col4 CanPres, col5 PrPres, col6 ImpPres | Usuario | `knowledge/training_data.py` | En el workspace hay `PRES.xlsx` en raíz (git status) |
| `*.autodesk_raw.json` | Volcado APS | JSON grande sin esquema fijo único | `stage_aps_extraction` | Depuración | |
| `*.normalized.json` | Hechos CAD normalizados | Ver `process_autodesk_json` return | `process_autodesk_json` | `build_level_inventory`, visión | |

**Tamaños:** dependen del proyecto; el código no impone límite propio de filas BC3, pero el clasificador trunca a **80** ítems BC3 por llamada GPT (`bc3_items[:80]` en `classifier_agent.py`).

---

### 7.3 Datos de salida

| Artefacto | Estructura | Productor | Consumidor |
|-----------|------------|-----------|------------|
| `{output_name}.xlsx` | Filas presupuesto + estilos | `export_budget_workbook` | Usuario, `compare_budget.py` |
| `dupla_budget_for_review.xlsx` | Columnas revisión (12 headers en `_save_for_review`) | `dupla_run_full_analysis_local.py` | Revisor humano |
| `{output_name}.bc3` | Registros `~V`, `~K`, `~C`, `~D`, `~T`, `~M` | `export_budget_bc3` | Presto / FIEBDC |
| `dupla_full_budget_output.json` | `chapters`, `lines`, `rows`, `budget_diagnostics`, etc. | `stage_build_budget` | Depuración |
| `vision_inventory_results.json` | Lista de dicts por página (inventario o error) | `stage_vision_analysis` | Depuración |
| `pipeline_report.json` | `stages[]` sin campo `output` serializado | `PipelineReport.save` | CI/humano |
| `run_summary.json` | Rutas y conteos | `main()` | Humano |
| `dupla_debug.log` | Logs DEBUG | `setup_logging` | Humano |

**Fila Excel presupuesto:** 7 columnas de datos alineadas a `HEADERS` en `export_excel.py`.

---

## 8. Integraciones Externas

### 8.1 Autodesk Platform Services (APS)

- **Qué hace en el sistema:** subir DWG a OSS; crear traducción Model Derivative; descargar propiedades y ensamblar JSON para `process_autodesk_json`.
- **Endpoints usados (desde código):**
  - `POST https://developer.api.autodesk.com/authentication/v2/token` (`aps_auth.py`)
  - `POST https://developer.api.autodesk.com/oss/v2/buckets` y URLs firmadas (`oss_manager.py`)
  - `GET/POST https://developer.api.autodesk.com/modelderivative/v2/designdata/...` (`model_derivative.py`, `BASE_URL` + `MD_URL`)
- **Request/response:** OAuth `client_credentials` con scope largo en `aps_auth.py`; token Bearer en resto; respuestas JSON (manifiesto, metadatos, propiedades).
- **Configuración y credenciales:** `.env` → `CLIENT_ID`, `CLIENT_SECRET`, `APS_BUCKET_NAME` (default `dupla_dwg_bucket_test_01` en `oss_manager.py`).
- **Límites y costos:** no codificados en el repo; dependen de contrato Autodesk. Timeouts configurables: `translation_timeout_seconds`, `max_property_wait_seconds`, etc.
- **Si la API falla:** excepciones HTTP (`raise_for_status`) o reintentos de token 401 en `_request_with_token_refresh`. A nivel pipeline, etapa falla y se detiene el flujo principal.

### 8.2 OpenAI API

- **Qué hace:** visión (`gpt-4o` multimodal); clasificación BC3 por capítulo (`gpt-4o` texto); embeddings (`text-embedding-3-small` por defecto en `bc3_embeddings.py`).
- **Endpoints:** vía SDK `openai` (`OpenAI().chat.completions.create`, `embeddings.create`).
- **Request/response:** mensajes con imágenes en base64 para visión; prompts con catálogo BC3 truncado; embeddings en lotes.
- **Credenciales:** `OPENAI_API_KEY` en `.env` (cargado explícitamente desde raíz repo en varios módulos).
- **Límites:** `max_tokens=4096` visión, `max_tokens=2048` clasificador por capítulo; truncado metodología oficina `_MAX_OFFICE_METHODOLOGY_CHARS = 12000` en `vision_agent.py`; metodología auto `max_chars=10000` en `methodology_generator.py`.
- **Si la API falla:**
  - Visión: por página se captura excepción en `run_full_vision_analysis` → dict con `error`.
  - Clasificador: si falla el bloque GPT, warning y **fallback** a `rank_budget_candidates` (solapamiento de tokens) en `match_takeoffs_to_bc3`.
  - Embeddings: en `bootstrap_pipeline_inputs` falla con log warning y continúa sin embeddings; en `stage_knowledge_inputs` una excepción no capturada podría fallar la etapa (no hay try/except global en `stage_knowledge_inputs` alrededor de `load_or_build_embeddings`).

---

## 9. Prompts de IA

### 9.1 Prompt de Visión

- **Ubicación:** `agents/vision_agent.py` — constantes `_SIMPLE_SYSTEM_PROMPT`, `_SIMPLE_SCHEMA_HINT`; composición `_compose_vision_system_prompt(vision_profile_key)` + `_build_simple_user_prompt(...)`.
- **Texto del system prompt (resumen fiel):** rol de presupuestista senior dominicano; aplicar bloque metodología oficina sin contradecir JSON; reglas numeradas (1–12) sobre búsqueda de leyendas, cotas, tipos de plano, instalaciones, etc.; cierre “Return ONLY valid JSON”.
- **Inyección dinámica:**
  - Perfil disciplina: `agents/vision_profiles.py` → `focus_addon` por `STRUCTURAL|ELECTRICAL|SANITARY|FINISHES_ARCH|GENERAL`.
  - `office_methodology` manual (archivo markdown path `OFFICE_METHODOLOGY_PATH` en runner) + `auto_methodology` desde `generate_methodology_context`.
  - Resumen CAD: `format_cad_facts_for_prompt(cad_summary)` → capas, cotas, bloques, textos, sombreados.
- **Output esperado:** JSON alineado con `_SIMPLE_SCHEMA_HINT` (clave `plan_type`, listas `walls`, `doors`, … `annotations_and_notes`).
- **Truncados y límites:** metodología oficina 12000 chars; imágenes `detail: "high"` en API.

### 9.2 Prompt del Clasificador (BC3)

- **Ubicación:** `agents/classifier_agent.py` → `_gpt4o_classify_chapter(...)`.
- **System message:** `"Presupuestista dominicano. Devuelve SOLO un JSON array..."`.
- **User prompt:** encabezado con capítulo (`chapter_code`, `chapter_desc`), texto estático `_STATIC_CHAPTER_GUIDANCE[chapter_code]`, opcional `few_shot_examples` de `generate_few_shot_examples`, lista `PARTIDAS A CLASIFICAR` como JSON inline, `CATALOGO BC3` máx 80 ítems, instrucciones estrictas de no inventar códigos; formato salida array `{takeoff_key, bc3_code, unit_price, match_type}`.
- **Inyección dinámica:** takeoffs del capítulo; subset BC3 filtrado por tokens o por búsqueda semántica; ejemplos PRES filtrados.
- **Output esperado:** JSON array parseado por `_extract_json_list`.

### 9.3 Prompt del clasificador de disciplina por página PDF

- **Ubicación:** `pipeline/pdf_discipline_split.py` — `_DISCIPLINE_PROMPT`.
- **Output esperado:** JSON con `discipline` ∈ {structural, electrical, sanitary, finishes_architectural, general} y `title`.

---

## 10. Sistema de Tests

- **Qué se testea (módulos con archivo dedicado en `tests/`):** `schemas`, `inventory_builder`, `quantifier_agent`, `budget_composer`, `export_excel`, `bc3_parser`, `bc3_embeddings`, `training_data`, `methodology_generator`, `pres_expansion`, `project_manifest`, `pdf_discipline_split`, `discipline_mapping`, `presto_constants`, `model_derivative`, `oss_manager`, `pipeline_integration`, `rules_engine` (variantes muros/pisos/techos/aperturas/áreas húmedas), `rule_precedence`, `feedback_store`, `pres_structural_filter`, inventario estructural, etc.
- **Qué NO se testea (observado):** no hay test que mockee el runner completo `dupla_run_full_analysis_local.main()` contra APS real; la integración externa se limita a pruebas unitarias/mocks parciales (`test_model_derivative.py`, `test_oss_manager.py`, etc.).
- **Cobertura por módulo:** no se ejecutó `pytest-cov` en este análisis; **cobertura exacta no verificada**.
- **Tests que fallan:** en la corrida local reciente: **0 fallos** — `76 passed in 50.36s` (salida pytest en entorno del proyecto).
- **Fixtures/mocks:** presentes en tests por módulo (no enumerados todos aquí); p. ej. JSON normalizados de ejemplo en tests de inventario/cuantificador.
- **Cómo correr:** desde raíz del repo, con venv activo: `python -m pytest tests` (según entorno del usuario).

---

## 11. Configuración y Despliegue

- **Variables de entorno necesarias:** `CLIENT_ID`, `CLIENT_SECRET` (APS); `APS_BUCKET_NAME` (opcional con default); `OPENAI_API_KEY` (visión/clasificador/embeddings).
- **Instalación:** `pip install -r requirements.txt` (y PyMuPDF ya listado).
- **Cómo correr el sistema:**
  - Editar CONFIG en `dupla_run_full_analysis_local.py` **o** pasar `--project inputs/projects/mi.yaml`.
  - `python dupla_run_full_analysis_local.py`
  - Validación sin red: `--validate-only`.
- **Requisitos:** Python compatible con sintaxis del repo (3.10+ razonable); acceso saliente a internet para APS y OpenAI; espacio en disco para JSON e imágenes renderizadas.

---

## 12. Decisiones de Diseño y Trade-offs

### 12.1 Inventario “simple” en visión + adaptador Python

- **Contexto:** Los comentarios en `vision_agent.py` indican que pedir el esquema completo de `LevelInventory` al modelo producía datos vacíos.
- **Decisión tomada:** prompt con JSON relativamente plano + función `_simple_to_level_inventory`.
- **Alternativas descartadas (implícito en comentarios):** un solo paso LLM → esquema complejo.
- **Consecuencias:** mejor control de campos y normalización; más código de mantenimiento en el adaptador; el modelo puede omitir claves que el adaptador tolera con listas vacías.
- **Evaluación actual:** patrón **activo** en `analyze_plan`; comentario de diseño explícito en cabecera del módulo.

### 12.2 Merge híbrido con preferencias asimétricas

- **Decisión:** `build_level_inventory` prefiere visión en `floor_area_m2` y en `area_m2` de muros al fusionar entidades.
- **Alternativas:** siempre preferir CAD o siempre visión.
- **Consecuencias:** mejor uso de polígonos visibles en plano; riesgo de conflictos si CAD y visión discrepan (se acumulan `conflict_notes` vía `_scalar_merge` / `_merge_entities`).
- **Evaluación actual:** implementación explícita en docstring y cuerpo de `build_level_inventory`.

### 12.3 Clasificación BC3 por capítulo con catálogo truncado

- **Decisión:** `_gpt4o_classify_chapter` envía máximo **80** ítems BC3 por capítulo.
- **Consecuencias:** costo/latencia acotados; riesgo de omitir el código correcto si no entra en el subconjunto filtrado por tokens o embeddings.
- **Evaluación actual:** contrapeso parcial vía `embedding_index` + `search_bc3` para ordenar ítems relevantes en `_filter_bc3_for_chapter`.

### 12.4 Bucket OSS `transient`

- **Decisión:** política `transient` al crear bucket.
- **Consecuencias:** almacenamiento temporal en Autodesk; adecuado para procesamiento, no para archivo permanente de DWGs.

### 12.5 Reglas de negocio en JSON (`default_rules.json`)

- **Decisión:** expansión de takeoffs declarativa consumida por `rules_engine`.
- **Consecuencias:** cambios de negocio localizados sin reentrenar modelos; riesgo de reglas mal configuradas que multipliquen cantidades.

---

## 13. Limitaciones Conocidas

- **Dependencia de servicios externos:** sin APS/OpenAI no hay paridad funcional completa en producción.
- **DWG complejo:** la calidad del JSON de Model Derivative depende del contenido del DWG y de la traducción 2D; geometría y propiedades pueden ser incompletas.
- **Visión:** coste por página; errores parciales por imagen; posible alucinación de cantidades si el plano es ambiguo.
- **BC3:** parser con `TODO` en descomposición completa (`processors/bc3_parser.py`); catálogos muy jerárquicos pueden no reflejarse totalmente.
- **Excel BC3 export:** `export_bc3.py` usa cabecera `~K` con marcador `EUR` en un tramo del registro aunque comentarios digan RD$ — **posible inconsistencia semántica** entre comentario y literal de archivo (ver líneas alrededor de `~K` en `export_bc3.py`); impacto exacto en Presto **no verificado** aquí.
- **Multiplataforma:** rutas largas en Windows motivaron hash corto para carpeta de render (`_pdf_pages_cache_dir`).
- **Código muerto / legacy:** `_legacy/` y scripts antiguos pueden confundir si un nuevo desarrollador no usa el runner principal.
- **`cad_automation/`:** vacío o sin archivos según búsqueda por glob — rol actual nulo.

---

## 14. Mapa de Dependencias entre Módulos

Grafo textual (depende de →):

- `dupla_run_full_analysis_local.py` → `aps_*`, `processors`, `agents.vision_agent`, `knowledge.*`, `core.pipeline`, `core.stage`, `core.logging_config`, `core.schemas`, `budget.export_*`, `pipeline.project_manifest`
- `core.pipeline` → `classifier_agent`, `quantifier_agent`, `composer`, `inventory_builder`, `rules_engine`, `bc3_parser`, `json_processor`, `bc3_embeddings`, `training_data`, `pres_expansion`
- `agents.vision_agent` → `vision_profiles`, `core.schemas`
- `agents.classifier_agent` → `bc3_embeddings`, `training_data`, `pres_expansion`, `core.schemas`
- `agents.quantifier_agent` → `core.schemas`
- `budget.composer` → `chapter_rules`, `core.schemas`
- `budget.export_excel` / `export_bc3` → `core.schemas`
- `core.inventory_builder` → `core.schemas` (+ OpenAI opcional en `_gpt_classify_cad_layers`)
- `processors.json_processor` → stdlib only
- `processors.bc3_parser` → stdlib only
- `knowledge.bc3_embeddings` → `numpy`, `openai`, `core.schemas` (solo tipos en firmas auxiliares)
- `rules_engine` → `core.schemas`, `registry` → JSON local

---

## 15. Glosario

- **BC3:** formato de intercambio de presupuestos FIEBDC-3 (texto con registros `~C`, `~D`, etc.), usado por **Presto** y herramientas compatibles.
- **FIEBDC:** familia de normas españolas para intercambio de información de construcción; aquí **FIEBDC-3/2016** en cabecera generada.
- **Presto:** software de presupuestos que consume BC3 (archivos RTF de ejemplo en `data/presto_files/`).
- **Partida:** línea de medición con unidad y precio (en Excel: fila con `Nat` típicamente “Partida”).
- **Capítulo:** agrupación jerárquica de partidas (en composer: `BudgetChapter` y filas `row_type="chapter"`).
- **Takeoff / mediciones:** `QuantityTakeoff` — cantidad derivada del inventario con fórmula y trazabilidad (`QuantityTrace`).
- **APS / OSS / Model Derivative:** servicios Autodesk para almacenar DWG y traducirlos a formatos de visualización y propiedades.
- **URN:** identificador codificado del objeto en Model Derivative (construido en `model_derivative.py` a partir de bucket + object).
- **PRES.xlsx:** presupuesto Excel de referencia del estudio; alimenta *training pairs* y metodología automática.
- **APU:** no definido formalmente en el código analizado como tipo; en dominio de construcción suele ser “Análisis de Precio Unitario” (no hay clase `APU` en `core/schemas.py`).
- **ITBIS:** impuesto; **no** aparece como constante central en los módulos núcleo listados (puede existir en documentación legacy).
- **SVF2:** formato derivado Autodesk usado en flujo moderno de visor/model derivative.

---

*Fin del documento. Fecha de generación del análisis estático: 2026-04-21. Verificación automatizada: pytest `76 passed` en el entorno donde se ejecutó la suite; corridas E2E con credenciales reales no incluidas en esta verificación.*
