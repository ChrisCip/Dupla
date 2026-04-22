# Reingeniería Completa — Sistema Dupla de Presupuestos de Construcción con IA

**Metadocumento:** generado a partir de lectura del código fuente en el repositorio y una corrida de tests locales (`python -m pytest tests -q`) el **2026-04-21**. **Última verificación de tests:** `142 passed` en ~20 s (mismo día). **No se verificó** una ejecución completa con credenciales reales de Autodesk ni OpenAI al documentar: la descripción de esas integraciones se basa **solo** en el código.

---

## 1. Resumen Ejecutivo

**Dupla** es un sistema en **Python** que automatiza la elaboración de **presupuestos de construcción** a partir de **planos en DWG** (procesados vía **Autodesk Platform Services**, APS, en la nube) y de **imágenes de planos** (rasterizadas desde PDF o leídas desde carpeta), usando **modelos de visión y lenguaje** de **OpenAI** para extraer inventario cuantificable, y **reglas deterministas** para convertir ese inventario en **mediciones (takeoffs)**, emparejadas con un **catálogo BC3 (FIEBDC)** y, opcionalmente, con ejemplos de un **Excel de presupuesto de referencia** (formato PRES o NASAS Preliminary). El resultado se exporta a **Excel** y a un **archivo BC3** compatible con flujos tipo **Presto 8.8**, más artefactos JSON de trazabilidad y depuración.

El núcleo operativo es un **pipeline monolítico secuencial** orquestado por `core/stage.py` (`PipelineRunner`) y lógica de negocio en `core/pipeline.py`, invocado normalmente desde `dupla_run_full_analysis_local.py` (configuración local y rutas) o `dupla_run_gebsa.py` (proyecto multi-disciplina GEBSA con validaciones adicionales). Existen **scripts** en `scripts/` para flujos auxiliares (NASAS, pruebas, comparación presupuestos) y un directorio `_legacy/` con herramientas y pruebas antiguas de APS/CAD.

**Estado de verificación local:** `python -m pytest tests -q` reporta **142 pruebas pasando, 0 fallando** (ver sección 10). Existen `validation/discipline_rules.json` (reglas V1–V5) y alineación de `budget/presto_constants.PRESTO_HEADER_CODES` con `budget/export_excel.HEADERS` (11 columnas).

---

## 2. Problema de Negocio

- **Qué proceso manual reemplaza:** recorrer planos (DWG/PDF), medir y contar elementos (muros, acabados, estructura, instalaciones), asignar cada partida a códigos de un catálogo (BC3), cuantificar unidades, aplicar precios, armar capítulos y exportar a Excel/Presto.
- **Quién es el usuario final:** presupuestista, ingeniero de costos u oficina técnica que ya trabaja con **catálogo BC3** y hojas Excel, y que puede importar **BC3 (FIEBDC)** en software de presupuesto.
- **Qué inputs tiene disponibles el usuario:** `DWG`; `PDF` o **carpeta de imágenes**; archivo **BC3** de referencia; opcional **Excel** de presupuesto histórico (PRES o NASAS Preliminary) para pares de entrenamiento y metodología automática; `project.yaml` opcional; archivo **`.env`** con `CLIENT_ID`, `CLIENT_SECRET` (Autodesk) y `OPENAI_API_KEY` (OpenAI), más variables de modelo opcionales.
- **Qué output espera recibir:** Excel de presupuesto (`export_excel.HEADERS`), Excel de **revisión** (`dupla_budget_for_review.xlsx` en el runner local), `dupla_full_budget_output.json`, `vision_inventory_results.json`, JSON **Autodesk** crudo y normalizado, `pipeline_report.json`, `run_summary.json`, `dupla_debug.log`, y **BC3** exportado.
- **Qué valor genera la automatización:** combina heurísticas del modelo derivado (capas, bloques, pistas) con interpretación **visual** de planos, estandariza el inventario en `core/schemas.py`, traza cantidades con `QuantityTrace` y propone/valida códigos BC3 mediante embeddings y/o llamadas a modelo de lenguaje.

---

## 3. Arquitectura General

### Diagrama de bloques (ASCII)

```
[DWG] ----upload----> [APS OSS] ----Model Derivative----> [JSON propiedades]
   |                        |                                |
   |                        |                                v
   |                        |                    [json_processor: cad_facts]
   v                        |                                |
[PDF/imgs] --> [PyMuPDF] --> [PNG pages]                        |
   |                        |                                |
   |                        v                                v
   +---------> [vision_agent: analyze_plan] <--- cad_facts (prompt)
   |                        |                                |
   |                        v                                v
   |              [LevelInventory / dict por página]         |
   |                        |-------- build_level_inventory -+
   |                        v
   +----------------> [build_hybrid_inventory] --> [quantify_inventory] --> [RulesEngine]
                                                      |
                                                      v
                           [_match_or_generate: PartidaGenerator | match_takeoffs_to_bc3]
                                                      |
                                                      v
                                    [compose_budget] --> [export_excel] + [export_bc3]
```

### Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Lenguaje | Python (3.x; entorno de tests observado: CPython 3.13 en Windows) |
| HTTP | `requests` |
| API LLM / visión | `openai` (SDK 1.x, `openai>=1.0` en `requirements.txt`) |
| Config local | `python-dotenv` (`.env` en raíz del repo) |
| Excel | `openpyxl` |
| PDF raster | `pymupdf` (módulo `fitz`) |
| YAML | `pyyaml` |
| NumPy | usado en `knowledge/bc3_embeddings.py` (embeddings) |
| Tests | `pytest` |

### Patrón arquitectónico

**Monolito Python** con **pipeline por etapas** (`PipelineRunner`: éxito/error por etapa, tiempos, `pipeline_report.json`). No hay API HTTP propia de producto en el núcleo; la integración es **batch** vía scripts. Las **reglas** de expansión de takeoffs viven en `rules_engine/`.

### Decisiones de arquitectura clave (estado actual)

- **JSON-first / APS:** el DWG no se abre con AutoCAD local; se sube a OSS y se traduce vía **Model Derivative** (ver `aps_integration/model_derivative.py` docstring: flujo REST, sin COM).
- **Inventario híbrido:** `build_level_inventory` fusiona heurísticas de CAD normalizado con el inventario de visión sin pisar en silencio: conflictos en notas (ver `core/inventory_builder.py`).
- **Dos vías de emparejamiento a presupuesto:** primero se intenta `PartidaGenerator` (si hay `OPENAI_API_KEY`); si falla o no hay clave, `match_takeoffs_to_bc3` en `agents/classifier_agent.py` (con embeddings si existen).
- **Capa semántica opcional:** en `core/pipeline.py` `build_budget_from_sources`, bloque `enable_semantic` + `discipline_id` en metadata: solo se activa si `context.metadata["enable_semantic_layer"]` es verdadero y hay `discipline_id` (ruta `core/semantic_enrichment.py`, `core/quality_engine.py`).

---

## 4. Estructura del Repositorio

**Conteo aproximado:** miles de archivos bajo el repo (incluye `.venv/`, cachés, salidas, CSV grandes); el análisis operativo se centra en el **código fuente** y `data/` relevante.

A continuación, **raíz y propósito** (no se listan los miles de entradas de `output/`, `comparisons/`, caché de BC3, etc., salvo anotación).

| Ruta / elemento | Propósito |
|-----------------|-----------|
| `dupla_run_full_analysis_local.py` | Runner principal local: CONFIG, CLI `--project`, `--validate-only`, `--discipline`, `PipelineRunner`, etapas APS → páginas → conocimiento → visión → presupuesto → Excel → BC3. |
| `dupla_run_gebsa.py` | Runner multi-disciplina (GEBSA): bucles por disciplina, reutiliza `build_budget_from_sources` y añade validación de dominio, informes. |
| `compare_budget.py` | Comparación de presupuestos (CLI con `if __name__ == "__main__"`). |
| `agents/` | Agentes: `vision_agent.py`, `classifier_agent.py`, `quantifier_agent.py`, `partida_generator.py`, `partida_adapter.py`, etc. |
| `aps_integration/` | Autenticación OSS, `model_derivative`, `oss_manager`, utilidades; subcarpeta histórica con muchos JSON de prueba. |
| `analysis/` | Inventarios y prompts markdown por disciplina (`analysis/discipline_prompts/*.md`) usados en flujos de análisis detallado. |
| `budget/` | Composición, exportación Excel/BC3, consolidación, `presto_constants.py`, `nasas_preliminary_io.py`, etc. |
| `core/` | `pipeline.py`, `schemas.py`, `stage.py`, `inventory_builder.py`, `semantic_*`, `quality_engine.py`, `openai_chat_models.py`, etc. |
| `disciplines/` | Motores por disciplina (arquitectura, estructura, eléctrico, sanitario): reglas de dominio YAML, `get_engine` en `disciplines/__init__.py`. |
| `knowledge/` | BC3 embeddings, `training_data.py`, `methodology_generator.py`, `prompts/` (system/user por engine), caché `knowledge/cache/*.npz`, `office_methodology.md`. |
| `pipeline/` | `project_manifest.py` (YAML de proyecto, `vision.sources` multi-PDF). |
| `pricing/` | `construcosto_loader.py` (snapshots de precios de referencia si existen CSV). |
| `processors/` | `json_processor.py` (normalización de JSON de Autodesk), `bc3_parser.py`, parsers auxiliares. |
| `rules_engine/` | Reglas JSON y motor de reglas para expandir takeoffs. |
| `validation/` | `budget_validator.py`, `discipline_inference.py`, `discipline_rules.json` (reglas V1+). |
| `scripts/` | Pipelines y utilidades: NASAS, merged CAD/PDF, `verify_aps_setup.py`, etc. |
| `tests/` | 39 archivos de test `test_*.py` (ver sección 10). |
| `data/` | BC3, XLSX, imágenes, CSV ConstruCosto, `NASAS09_Preliminary_Budget.xlsx`, etc. |
| `config/` | Configuración suelta (muy pequeña). |
| `inputs/` | Entradas de usuario opcionales (p. ej. manifiestos de proyecto). |
| `output/`, `analysis_output/`, `comparisons/`, `api_results/` | **Salidas generadas** o históricas (no son código). |
| `_legacy/` | Código y tests antiguos (CAD batch, pruebas APS). |
| `.env` | **Credenciales** (no versionadas en git idealmente; en local existe según el usuario). |
| `requirements.txt` | Dependencias mínimas: `openai`, `python-dotenv`, `requests`, `pytest`, `openpyxl`, `pymupdf`, `pyyaml`. |
| `_diag.py` … `_diag6.py` | Scripts de diagnóstico puntuales en raíz. |
| `PRES.xlsx` | En raíz: Excel de presupuesto de referencia (usado en configs que apunten a él). |
| `README.md`, `SRS.md`, `TECHNICAL_DOCS.md` | Documentación humana (fuera del alcance de “solo código”, pero presente). |
| `BLCAD09/`, `BLCAD14/` | Carpetas de proyecto/material de ejemplo (análisis BLCAD). |
| `8- ACAD-PLANOS…pdf/.dwg` | Archivos de plano sueltos en raíz (entrada de usuario, no módulo). |

---

## 5. Pipeline Principal — Flujo Completo Paso a Punto (runner local)

A continuación, el recorrido **real** al ejecutar `python dupla_run_full_analysis_local.py` (sin `--validate-only`, con dependencias y credenciales disponibles), según el orden de llamadas en `dupla_run_full_analysis_local.py` y las funciones a las que delega.

### 5.0 Etapa: Pre `main` — configuración y `RUN`

- **Archivo(s):** `dupla_run_full_analysis_local.py`
- **Función(es):** al importar, `RUN = _build_run_defaults()`; si se usa `apply_project_manifest`, se reasigna `global RUN`.
- **Entrada:** bloque `CONFIG` (constantes) y/o `project.yaml` vía `load_project_manifest(Path)`.
- **Procesamiento:** `ProjectManifest` (`pipeline/project_manifest.py`) resuelve rutas respecto al directorio del YAML; soporta `vision.sources` para multi-PDF.
- **Salida en memoria:** `RUN: SimpleNamespace` con campos como `project_name`, `project_id`, `dwg_path`, `pdf_path`, `use_pdf`, `bc3_path`, `xlsx_training_path`, `outputs_dir`, `output_name`, `translation_views`, `vision_sources`, `pres_template_takeoffs`, etc.
- **Efectos secundarios:** ninguno en disco hasta `main()`.
- **Errores:** manifiesto inválido → `SystemExit` en `main` si `validate_manifest` devuelve errores.
- **Decisiones de diseño:** el mismo runner sirve con CONFIG embebido o con YAML reutilizable para proyectos (NASAS, BLCAD, etc.).

### 5.1 Etapa: `main` — parseo de CLI y directorio de salida

- **Función:** `def main() -> None:`
- **Parámetros CLI:**
  - `--project` (str | None)
  - `--validate-only` (flag)
  - `--discipline` (choices: `arquitectonica` | `estructural` | `electrica` | `sanitaria` | None)
- **Efecto:** `_CLI_RUN_DISCIPLINE = args.discipline` (variable de módulo, usada luego en metadatos y se pasa a visión como `upload_discipline_id` en `stage_vision_analysis`).
- **Efectos secundarios:** `outputs_dir = RUN.outputs_dir.resolve()`, `outputs_dir.mkdir(parents=True, exist_ok=True)`; `setup_logging(..., log_file=outputs_dir / "dupla_debug.log")`.
- **Errores:** si `validate-only`, se comprueban existencias de `RUN.dwg_path`, PDF, imágenes, BC3, XLSX según reglas; fallo → `SystemExit`.

### 5.2 Etapa: `aps_extraction`

- **Función invocada por stage:** `stage_aps_extraction(dwg_path: Path, outputs_dir: Path, bucket_name: str) -> dict`
- **Llamadas internas ordenadas:**
  1. `get_aps_token()` → `aps_integration/aps_auth.py` (POST a `https://developer.api.autodesk.com/authentication/v2/token` con `CLIENT_ID`, `CLIENT_SECRET`, scope fijo en código).
  2. `create_bucket(token, bucket_name)` → `oss_manager.py` (simplificación: creación/uso de bucket OSS).
  3. `upload_file_to_bucket(token, bucket_name, str(dwg_path), object_name=RUN.upload_object_name, unique_suffix=...)` 
  4. `extract_dwg_data(token, bucket_name, object_name, views=RUN.translation_views, ...)` → `aps_integration/model_derivative.py`  
     - `extract_dwg_data` firma:  
       `(token: str | dict, bucket_key: str, object_name: str, *, views: Iterable[str] = DEFAULT_VIEWS, translation_timeout_seconds: int, poll_interval_seconds: int, max_property_wait_seconds: int, failed_manifest_grace_polls: int, failed_manifest_grace_sleep_seconds: int) -> dict`  
  5. Escribe `outputs_dir / f"{dwg_path.stem}.autodesk_raw.json"` (JSON del resultado bruto de extracción).
  6. `process_autodesk_json(str(raw_json_path))` → `processors/json_processor.py` → diccionario **normalizado** (cad facts).
  7. Escribe `outputs_dir / f"{dwg_path.stem}.normalized.json"`.
- **Retorno del stage:** `{"cad_facts": normalized, "raw_json_path", "normalized_json_path", "uploaded_object_name"}`.
- **Efectos secundarios:** escritura de 2 JSON, uso de **red** (Autodesk) y almacenamiento en bucket.
- **Errores:** excepción en cualquier subpaso hace que `PipelineRunner.run_stage` marque la etapa como `error` y se llame a `_finish` sin continuar. Reintentos 401 se manejan en `model_derivative._request_with_token_refresh` (refresco de token y un reintento).

### 5.3 Etapa: `vision_pages` — resolución de imágenes

- **Función:** `stage_resolve_pages(outputs_dir: Path) -> dict`
- **Ramas:**
  1. Si `RUN.vision_sources` (lista de `VisionSourceSpec`): por cada fuente, renderiza PDF a PNG en `_pdf_pages_cache_dir` (hash del path del PDF) o usa `images_dir`; retorna `{"multi": True, "bundles": [{pages_dir, discipline, page_count}, ...], "page_count", "source": "multi_input", "pages_dir": first bundle's dir}`.
  2. Si un solo PDF: `render_pdf_to_images(pdf_path, rendered_dir, dpi=200)` (PyMuPDF).
  3. Si no PDF: imágenes existentes bajo `RUN.images_dir`.
- **Efectos secundarios:** archivos `page_0001.png`… bajo `outputs_dir/rendered_pages/p_<hash>/`.
- **Errores:** `FileNotFoundError` si PDF falta; `RuntimeError` si `USE_PDF` y no hay `pymupdf`.

### 5.4 Etapa: `knowledge_inputs` — BC3, training, embeddings, metodología

- **Función:** `stage_knowledge_inputs(outputs_dir: Path) -> dict` (según cuerpo actual: usa `RUN.*`)
- **Pasos:**
  1. `parse_bc3(str(bc3_path))` si `RUN.bc3_path` → `processors/bc3_parser.py`.
  2. `extract_training_pairs(xlsx_training_path)` → `knowledge/training_data.py` (ramas: Excel clásico PRES o, si aplica, `load_nasas_preliminary_budget_rows` para NASAS Preliminary vía `budget/nasas_preliminary_io.py`).
  3. `load_or_build_embeddings(bc3_catalog)` → `knowledge/bc3_embeddings.py` con caché en `knowledge/cache/<fingerprint>_<model>.npz` + JSON metadatos.
  4. `generate_methodology_context(training_pairs=..., bc3_catalog=...)` → `knowledge/methodology_generator.py`.
- **Retorno:** `bc3_catalog`, `bc3_path_value`, `training_pairs`, `embedding_index` (o None), `xlsx_training_path` (str o None), `auto_methodology` (str).
- **Efectos secundarios:** lectura/escritura caché embeddings.

### 5.5 Etapa: `vision_analysis`

- **Función:** `stage_vision_analysis(pages_input: Path | dict, cad_facts: dict, outputs_dir: Path, *, auto_methodology: str | None, upload_discipline_id: str | None) -> dict`
- **Lógica de ramificación:**
  - **Multi-bundles:** para cada `bundle` en `pages_input["bundles"]`, llama a `run_full_vision_analysis(str(pages_dir), cad_facts, office_methodology=methodology, upload_discipline_id=bundle.get("discipline") or upload_discipline_id)` (función de `agents/vision_agent.py`).
  - **Un solo directorio:** `run_full_vision_analysis(..., upload_discipline_id=upload_discipline_id)` (argumento reenviado desde `main` = `_CLI_RUN_DISCIPLINE`).
- **`run_full_vision_analysis` firma:**  
  `(pages_dir: str, cad_summary: dict[str, Any], *, office_methodology: str | None = None, upload_discipline_id: str | None = None) -> list[dict[str, Any]]`  
  Itera imágenes en el directorio y por cada una llama `analyze_plan(image_path, cad_summary, level_name, office_methodology=..., upload_discipline_id=...)`.
- **`analyze_plan` firma:**  
  `(image_path: Path, cad_summary: dict[str, Any], level_name: str, *, office_methodology: str | None = None, upload_discipline_id: str | None = None) -> dict[str, Any]`  
  Usa `get_client()` → `openai.OpenAI` con `OPENAI_API_KEY`; `encode_image`; `_vision_chat_completion` con `messages` que incluyen `_SIMPLE_SYSTEM_PROMPT` y user content de `_build_simple_user_prompt` (métodología, pistas CAD, posible `analysis/discipline_prompts/…` si aplica) + imagen en base64; parsea JSON con `_extract_json`; adapta a `LevelInventory` con `_simple_to_level_inventory` y `level_inventory_from_dict` (`core.schemas`); añade `cad_cross_checks` y metadatos.
- **Efectos secundarios:** escribe `outputs_dir / "office_methodology_snapshot.md"` si hay metodología; escribe `outputs_dir / "vision_inventory_results.json"` con la lista de resultados por página.
- **Errores por página:** capturados en `run_full_vision_analysis` → dict `{"error": str, "file": str}` (no detiene toda la lista).

### 5.6 Etapa: `build_budget`

- **Función:** `stage_build_budget(cad_facts, vision_results, bc3_catalog, embedding_index, training_pairs, raw_json_path, normalized_json_path, uploaded_object_name, pages_resolution: Path | dict, xlsx_path, outputs_dir) -> dict`
- **Construcción de `ProjectContext`:** con `core.schemas.ProjectContext(project_id=RUN.project_id, project_name=RUN.project_name, source_json_path=str(raw_json_path), plan_image_paths=...)` donde `plan_image_paths` se obtiene de listar imágenes de un directorio o de unir bundles multi-PDF. `metadata` incluye rutas, flags de traducción, `xlsx_path`, `pres_template_takeoffs: RUN.pres_template_takeoffs`, y `**discipline_meta` (p. ej. `discipline_id`, `allowed_item_types` con `_CLI_RUN_DISCIPLINE` o `DISCIPLINE` en CONFIG).
- **Núcleo:** `build_budget_from_sources(context, cad_facts, vision_results, bc3_catalog, embedding_index=embedding_index, training_pairs=training_pairs)` en `core/pipeline.py`.
- **Dentro de `build_budget_from_sources` (orden resumido pero completo lógicamente):**
  1. `build_hybrid_inventory(cad_facts, vision_payloads)` → mezcla CAD + visión (o solo CAD si no hay visión válida) usando `build_level_inventory` y `level_inventory_from_dict` donde aplica.
  2. Opcional: capa **semántica** si `enable_semantic_layer` y `discipline_id` en metadata: `enrich_semantics` → `evaluate_semantic_quality` → posible `adapt_semantic_to_inventory`.
  3. `build_expanded_takeoffs_from_inventory(hybrid_inventory, rules_engine, runner_source_discipline=project_discipline)` → internamente `quantify_inventory` + `RulesEngine.apply` (`rules_engine/`), luego `merge_pres_template_takeoffs` si el flag PRES en metadata.
  4. `_match_or_generate(expanded_takeoffs, bc3_catalog, embedding_index, training_pairs, project_discipline_id)`:
     - Si `OPENAI_API_KEY` y generador: `PartidaGenerator().generate(...)` y `adapt_generated_to_legacy_format` (`agents/partida_generator.py`, `partida_adapter.py`);
     - Si no: `match_takeoffs_to_bc3(takeoffs, bc3_catalog, top_k=3, embedding_index=..., training_pairs=..., project_discipline_id=...)` (`agents/classifier_agent.py`).
  5. `build_final_budget` → `compose_budget(context, takeoffs, candidates_by_takeoff, bc3_catalog=..., construcosto_snapshot=...)` (`budget/composer.py`); añade `budget["hybrid_inventory"]`, `base_takeoffs`, etc.
- **Efecto secundario:** escribe `outputs_dir / "dupla_full_budget_output.json"`.
- **Errores:** excepción no capturada en stage → `PipelineRunner` marca error. **Nota:** `compose_budget` puede llamar a `run_budget_validation` si `context.metadata.get("run_budget_validation")` es verdadero: requiere `validation/discipline_rules.json` legible; si falla, el compositor captura la excepción y deja de incluir `budget_validation` (ver `budget/composer.py`).

### 5.7 Etapa: `excel_export`

- **Función:** `stage_excel_export(context: ProjectContext, budget: dict, outputs_dir: Path) -> dict`
- **Llamada:** `export_budget_workbook(context=context, rows=budget["rows"], output_path=workbook_path, ...)` en `budget/export_excel.py` — firma:  
  `export_budget_workbook(context: ProjectContext, rows: Iterable[BudgetRow | Mapping], output_path: str | Path, *, sheet_name: str = "Presupuesto", quality_report: Mapping | None = None) -> Path`
- **Otra salida:** `_save_for_review` → `dupla_budget_for_review.xlsx` con hoja "Revision" y encabezados fijos (columnas A–L en el código de revisión, distintas de `HEADERS` del presupuesto principal).

### 5.8 Etapa: `bc3_export`

- **Función:** `stage_bc3_export(context, budget, outputs_dir) -> dict`
- **Llamada:** `export_budget_bc3(context, rows=budget["rows"], output_path=bc3_output_path, ...)` — `budget/export_bc3.py` — encoding **cp1252** según comentario del módulo; códigos truncados a 13 caracteres (Presto).
- **Errores:** si falla, el `main` solo registra **warning** y continúa (Excel ya generado).

### 5.9 Etapa: Cierre

- **Función:** `_finish(runner, outputs_dir, summary)` → `runner.report(summary=...).save(outputs_dir / "pipeline_report.json")`. Escribe además `run_summary.json` en `main` antes de `_finish`.

---

## 6. Módulos de Soporte (por directorio lógico)

### 6.1 `core/`

- **Propósito:** contratos de datos, orquestación del presupuesto, utilidades de inventario y capas de calidad/semántica.
- **Archivos y funciones clave:**  
  - `pipeline.py` — `build_budget_from_sources`, `build_hybrid_inventory`, `build_final_budget`, `bootstrap_pipeline_inputs`, `_match_or_generate`.  
  - `schemas.py` — dataclasses `ProjectContext`, `LevelInventory`, `QuantityTakeoff`, `BudgetCandidate`, `BudgetRow`, etc.  
  - `stage.py` — `PipelineRunner.run_stage`, `PipelineReport.save`.  
  - `inventory_builder.py` — `build_level_inventory(cad_facts, vision_inventory, *, level_id, level_name)`.  
- **Configuración:** el metadata `ProjectContext` controla PRES, disciplina, capa semántica.

### 6.2 `agents/`

- **Propósito:** visión, cuantificación, matching BC3, generación de partidas.
- **`vision_agent.py`:** `analyze_plan`, `run_full_vision_analysis`, constantes de prompt, adaptación a inventario.  
- **`classifier_agent.py`:** `match_takeoffs_to_bc3`, diccionarios de capítulos y tokenización.  
- **`quantifier_agent.py`:** `quantify_inventory(levels, *, runner_source_discipline: str | None = None) -> list[QuantityTakeoff]`.  
- **`partida_generator.py` / `partida_adapter.py`:** vía generativa a candidatos "compatibles" con el compositor.

### 6.3 `aps_integration/`

- **Propósito:** autenticación 2-legged y extracción Model Derivative.  
- **`aps_auth.py`:** `get_aps_token()`.  
- **`model_derivative.py`:** `extract_dwg_data`, polling de manifiestos, descarga de propiedades.  
- **`oss_manager.py`:** subida a bucket, creación de bucket.

### 6.4 `processors/`

- **Propósito:** parseo BC3, normalización de JSON de Autodesk, otros parsers.  
- **`json_processor.py`:** `process_autodesk_json(path) -> dict`.  
- **`bc3_parser.py`:** `parse_bc3` → estructura con `items` (lista de partidas y metadatos).

### 6.5 `budget/`

- **Propósito:** composición de filas, capítulos, export FIEBDC/Excel, constantes Presto, lectura NASAS.  
- **`composer.py`:** `compose_budget`, `compose_budget_rows` — lógica de filtrado, `run_budget_validation` condicionado.  
- **`export_excel.py`:** `HEADERS` de 11 columnas (Código, Nat, Ud, Resumen, CanPres, PrPres, ImpPres, Fuente Cantidad, Fuente Precio, BC3 Origen, Método de Precio).  
- **`export_bc3.py`:** `export_budget_bc3`.  
- **`presto_constants.py`:** `PRESTO_FIRST_DATA_ROW = 4`, `PRESTO_HEADER_CODES` con **7** columnas (subconjunto de `HEADERS` de export) — usado en tests y `compare_budget`.

### 6.6 `disciplines/`

- **Propósito:** reglas y filtros por disciplina de oficina (arquitectura, estructura, eléctrico, sanitario).  
- **Integración:** `get_engine` + metadata `allowed_item_types` en el contexto; filtros en `quantify_inventory` y en `compose_budget` vía `allowed_item_types`.

### 6.7 `knowledge/`

- **Propósito:** embeddings OpenAI de textos BC3, pares de entrenamiento desde Excel, generación de texto de metodología, prompts base por engine en `knowledge/prompts/`.

### 6.8 `rules_engine/`

- **Propósito:** expansión de takeoffs (reglas JSON + código Python en `registry.py`).

### 6.9 `validation/`

- **Propósito:** validar consistencia del presupuesto compuesto; inferir disciplina de origen.  
- **Problema actual:** `load_discipline_rules()` lee `validation/discipline_rules.json` — **archivo ausente** en el snapshot del repositorio analizado, lo que hace **fallar** validación y tests asociados.

### 6.10 `pipeline/project_manifest.py`

- **Propósito:** mapeo YAML → `ProjectManifest` y `VisionSourceSpec` (multi-fuente de visión).

### 6.11 `scripts/` (cada script es un entry point; ver sección 5 equivalente resumida al final de esta sección en la tabla de “puntos de entrada” del doc original; aquí, lista breve)

| Script | Rol |
|--------|-----|
| `run_nasas09_corridas.py` | Orquesta corridas asociadas al proyecto NASAS. |
| `run_merged_cad_pdf_vision.py` | Fusiona recorridos CAD/PDF/visión. |
| `run_dw_pres_compare.py` | Compara flujos DW vs PRES. |
| `run_multi_dwg_project_cad.py` | Multi-DWG. |
| `run_blcad09_discipline_pipeline.py` | Pipeline por disciplina BLCAD. |
| `run_prueba_web_01_full.py` | Prueba de corrida "web" histórica. |
| `verify_aps_setup.py` | Comprueba configuración APS. |
| `open_nasas09_excels.py` | Apertura de Excels (utilidad). |
| `audit_extraction_part1.py` | Auditoría de extracción. |
| `export_presentacion.py` | Export a presentación. |

---

## 7. Modelos de Datos

### 7.1 Esquemas internos (muestras; lista no exhaustiva de todos los campos de cada entidad se encuentra en `core/schemas.py`)

- **`ProjectContext`:** `project_id: str | None`, `project_name: str | None`, `source_json_path: str | None`, `plan_image_paths: list[str]`, `bc3_path: str | None`, `measurement_unit: str`, `metadata: dict[str, Any]`.
- **`LevelInventory`:** `level_id`, `level_name`, `source`, listas de `Wall`, `Door`, `Window`, estructurales, etc.
- **`QuantityTakeoff`:** `item_key`, `item_type`, `unit`, `quantity`, `formula`, `trace: QuantityTrace`, etc.
- **`BudgetCandidate`:** emparejamiento a código BC3 con puntuación y trazas.
- **`BudgetRow`:** `row_type` en `chapter|line|subtotal`, columnas alineadas a export.

### 7.2 Datos de entrada (archivos de ejemplo reales en el repo)

- **BC3 (FIEBDC-3/2002):** texto por líneas con prefijos `~V`, `~K`, `~C`, `~D`, `~M`, `~T`. Ejemplo (primeras líneas reales de `data/TGIU.bc3`):
  ```
  ~V|SOFT S.A.|FIEBDC-3/2002|Presto 8.8||ANSI|
  ~K|\2\2\3\2\2\2\2\DOP\|0|
  ~C|%01FH|%|Factor herramienta y seguridad de mano de obra|3|251119|3|
  ```
  **Encoding** típico de lectura en parsers: UTF-8 o fallback según implementación; **export** BC3 en `export_bc3.py` usa `cp1252` para Presto.  
  **Tamaño:** `TGIU.bc3` tiene del orden de **>20.000** líneas (miles de partidas) — cifra obtenida por lectura parcial e inferencia de extensión de archivo, no de un conteo de registros en runtime.

- **Excel PRES / NASAS:** estructura consumida en `knowledge/training_data.py` (columnas detectadas y ramas PRES vs NASAS Preliminary vía `budget/nasas_preliminary_io.py`). El repo incluye p. ej. `data/NASAS09_Preliminary_Budget.xlsx` (archivo binario; análisis estructural = código de `load_nasas_preliminary_budget_rows`).

- **Cache embeddings:** `knowledge/cache/bc3_<fingerprint>_<model>.npz` + JSON hermano — generados, no manuales.

- **construcosto CSV** bajo `data/construcosto/` (varios archivos) — leídos por `pricing/construcosto_loader.py` si existen y si el flujo carga el snapshot (excepciones se silencian en `_load_construcosto_if_available`).

### 7.3 Datos de salida

- **Excel de presupuesto:** columnas en `export_excel.HEADERS` (11 columnas, ver arriba).  
- **BC3 de salida:** estructura FIEBDC-3/2020 descrita en el docstring de `export_bc3.py` (~V, ~C códigos ≤13, ~M, etc.).  
- **JSON de presupuesto:** diccionario con `chapters`, `lines`, `rows`, `hybrid_inventory`, `takeoffs`, `candidates_by_takeoff` según campos añadidos en `build_final_budget` y `compose_budget`.  
- **Logs:** texto plano UTF-8 en `dupla_debug.log`; `pipeline_report.json` con lista de `stages` (sin campo `output` en serialización de `StageResult.to_dict` — el `output` se elimina a propósito en `to_dict` de `core/stage.py`).

---

## 8. Integraciones Externas

### 8.1 Autodesk Platform Services (Authentication + OSS + Model Derivative)

- **Qué hace en el sistema:** subir el DWG, traducir a formato viewable, descargar propiedades/árbol, producir el JSON de entrada para `json_processor`.  
- **Endpoints (desde código):**  
  - Token: `https://developer.api.autodesk.com/authentication/v2/token`  
  - Model Derivative base: `https://developer.api.autodesk.com/modelderivative/v2/designdata` (ver constantes en `model_derivative.py` y en `oss_manager` para almacenamiento en objetos)  
- **Configuración:** `CLIENT_ID`, `CLIENT_SECRET` vía `dotenv` en `aps_auth.py`. Buckets: `APS_BUCKET_NAME` y/o override `BUCKET_NAME` en runners.  
- **Si falla:** excepciones de `requests` o datos vacíos; el stage APS marca `error` y el pipeline se detiene en el runner local. Reintento en 401 en requests firmados a Model Derivative.  
- **Límites/costos:** no codificados en el repo; dependen de la **cuota Autodesk** del tenant (no documentado en código). **Timeouts** configurables: `translation_timeout_seconds` por defecto 3600, etc.  
- **No verificado aquí:** tiempos reales de traducción de DWG concretos ni costes de almacenamiento.

### 8.2 OpenAI (Visión y lenguaje)

- **Uso:**  
  - `agents/vision_agent.py` — `OpenAI` SDK, `chat.completions.create` con imagen (data URL) y mensajes. Modelo: `vision_model_id()` = `OPENAI_VISION_MODEL` o default `"gpt-5.1"`.  
  - `agents/classifier_agent.py` — camino GPT-4o por capítulos (según comentario en cabecera) cuando hay API key y catálogo.  
  - `PartidaGenerator` — generación de partidas vía `OPENAI_API_KEY`.  
  - `knowledge/bc3_embeddings.py` — embeddings de textos (modelo por defecto en constantes del módulo, p. ej. `text-embedding-3-small`-style naming en caché de archivos).  
- **Variables de entorno vinculadas (no exhaustivo):** `OPENAI_API_KEY` (obligatoria para visión), `OPENAI_VISION_MODEL`, `OPENAI_VISION_MAX_OUTPUT`, `OPENAI_VISION_REASONING_EFFORT`, `OPENAI_VISION_TEMPERATURE` (comentario en `vision_agent.py` indica `temperature` solo familia gpt-4).  
- **Límites en código:** `max_completion_tokens` acotado por `_vision_max_output_tokens()` (256–128000 rango lógico); metodología de oficina truncada a `12000` caracteres en prompt (`_MAX_OFFICE_METHODOLOGY_CHARS`).  
- **Si falla:** visión: por página se captura excepción; matching: fallback a ranking determinista; PartidaGenerator: excepción → fallback a `match_takeoffs_to_bc3` (log warning en `pipeline._match_or_generate`).

---

## 9. Prompts de IA

### 9.1 Prompt de Visión (sistema y usuario)

- **Sistema:** constante `_SIMPLE_SYSTEM_PROMPT` en `agents/vision_agent.py` (líneas ~155–178): define rol de "ingeniero presupuestista senior dominicano", reglas 1–15 sobre búsqueda en el plano, distinción de tipos, plano arquitectónico vs estructural, salida **solo JSON**.  
- **Hint de esquema:** `_SIMPLE_SCHEMA_HINT` (largo, mismo archivo) con forma JSON esperada (walls, etc.).  
- **Usuario:** `_build_simple_user_prompt(image_path, level_name, cad_summary, office_methodology=..., upload_discipline_id=...)` compone: tipo de vista, bloque "METODOLOGÍA DE OFICINA" si aplica, bloque de disciplina vía diccionarios de alias, pistas de CAD vía `format_cad_facts_for_prompt`, o — si existe el fichero en `analysis/discipline_prompts/<disciplina>.md` — **plantilla sustitutiva** leída de disco.  
- **Output esperado:** JSON parseable; luego se transforma a `LevelInventory` en Python, no se confía al modelo con el esquema completo de 15+ campos por entidad (comentario en la cabecera del módulo: enfoque de dos pasos, “simple count” / JSON “simple” + adaptador).  
- **Truncados:** metodología de oficina a 12 000 caracteres; además cota de salida vía `OPENAI_VISION_MAX_OUTPUT`.

### 9.2 Prompt del Clasificador (matching BC3)

- **Dónde:** `agents/classifier_agent.py` — lógica por **capítulos** (`_CHAPTERS` con 9 códigos "01"–"09") y, cuando procede, construcción de mensajes a OpenAI (funciones internas con cadenas en inglés/español mezclados según implementación: revisar sección "GPT" del archivo). **No** se pega en este documento el texto entero (cientos de líneas); está en el archivo fuente.  
- **Qué se inyecta:** descripciones de capítulo, rebanadas del catálogo BC3, few-shots de `knowledge/training_data.generate_few_shot_examples`, y *queries* de embeddings si `embedding_index` no es nulo.  
- **Qué se espera:** estructura JSON con asignación de códigos BC3 por takeoff (detalle en funciones de parsing dentro del mismo módulo).

### 9.3 PartidaGenerator

- **Dónde:** `agents/partida_generator.py` — catálogo de capítulos `CHAPTER_CATALOG` (24 entradas) mapeo `item_type` → capítulo, prompts construidos en la clase `PartidaGenerator` (método `generate`).  
- **Dinámico:** `QuantityTakeoff` serializados, pares de `TrainingPair` si existen, y trozos de BC3 de referencia no como lookup sino como formato.  
- **Límites:** depende de `openai` y de mensajes; **no** hay en la cabecera un único límite de tokens documentado al nivel de `vision_agent`.

### 9.4 Otros (embeddings, semántica, capa de detalle)

- `core/semantic_enrichment.py` y `knowledge/methodology_generator.py` generan texto/contexto; los prompts exactos de `semantic_enrichment` deberán leerse en ese archivo. **No puestos aquí en texto completo** por longitud.  
- **Nota de verificación:** no se hizo *dump* de tráfico de red en runtime.

---

## 10. Sistema de Tests

- **Dónde:** `tests/` (39 módulos `test_*.py` listados vía búsqueda de archivos).  
- **Cómo correr:** desde la raíz del repo, con el mismo intérprete que tenga dependencias:  
  `python -m pytest tests` (o `pytest tests -q`).  
- **Estado (verificado 2026-04-21):** **142 passed**, **0 failed**, **~20 s** (CPython en Windows, duración aproximada; puede variar con CPU y caché).  
- **Antes de alinear repositorio y documento** podían fallar: (1) `test_headers_match_export` si `PRESTO_HEADER_CODES` no igualaba a `export_excel.HEADERS` en las 11 columnas; (2) tests de `test_budget_validator.py` si faltaba `validation/discipline_rules.json`. Ese estado quedó corregido en código/datos.  
- **Cobertura por módulo:** **no** se generó un informe de cobertura (no se ejecutó `pytest --cov`). La cobertura es **estimada desconocida** sin herramienta.  
- **Qué se testea (indicación por nombres de archivos):** parse BC3, embeddings, compositor, export Excel, reglas, pipeline integración, inventory, quantifier, reglas mojadas/paredes, manifiestos, NASAS, mapping disciplinas, etc.  
- **Qué no se testea o es frágil:** flujos completos con APS reales, vision real (llamada OpenAI) — la mayoría son **mocks o datos sintéticos** (revisar cada test para detalle; no se releyeron los 39 archivos completos en esta sesión).  
- **Fixtures/mocks:** presentes vía `pytest` y datos en `data/` o dicts in-line; detalle: **no inventariado registro a registro** en este documento.

**Marcado explícito:** "No pude verificar" que el estado de fallos/pases sea el mismo en Linux/macOS/otra versión de Python: solo se corrió en el entorno Windows descrito en el mensaje de error de `pytest` (CPython 3.13).

---

## 11. Configuración y Despliegue

- **Variables de entorno mínimas:**  
  - `CLIENT_ID`, `CLIENT_SECRET` (Autodesk)  
  - `OPENAI_API_KEY` (OpenAI)  
  - Opcionales: `OPENAI_VISION_MODEL`, `OPENAI_VISION_MAX_OUTPUT`, `OPENAI_VISION_REASONING_EFFORT`, `OPENAI_VISION_TEMPERATURE`, `APS_BUCKET_NAME` (o equivalente leído en `oss_manager` — leer el archivo para nombre exacto).  
- **Instalación de dependencias:** `pip install -r requirements.txt` (y/o entorno virtual creado en el repo, p. ej. `.venv/`).  
- **Ejecución principal:** `python dupla_run_full_analysis_local.py` con opciones descritas; o `python dupla_run_gebsa.py`.  
- **Requisitos:** Python 3, acceso a Internet para APS y OpenAI, espacio en disco para renders PNG y caché de embeddings.  
- **No hay** Dockerfile estándar ni orquestación Kubernetes en el árbol analizado (búsqueda limitada: no se encontró un `Dockerfile` en la raíz de los listados básicos).

---

## 12. Decisiones de Diseño y Trade-offs

### 12.1 Procesar DWG en la nube (APS) en vez de local

- **Contexto:** extraer entidades y propiedades sin instalar AutoCAD.  
- **Decisión tomada:** REST-only Model Derivative (comentado en `model_derivative.py`).  
- **Alternativas descartadas (implícito en estructura):** automatización COM local (parte de `_legacy/` sugiere experimentos viejos).  
- **Consecuencias:** dependencia de conectividad, latencia, cuotas; ganancia: reproducibilidad y ausencia de licencia de escritorio.  
- **Evaluación actual:** describible como **coherente** con un producto *cloud*; el coste operativo pasa a ser externo.

### 12.2 Inventario "simple" en visión + adaptador en Python

- **Decisión:** el modelo responde JSON con estructura más simple; `_simple_to_level_inventory` mapea a `LevelInventory`.  
- **Consecuencia:** menos fallos de esquema en el LLM, más lógica en Python.

### 12.3 PartidaGenerator con fallback a matching BC3 clásico

- **Decisión:** `_match_or_generate` intenta generación, ante cualquier excepción o vacío, cae a `match_takeoffs_to_bc3`.  
- **Consecuencia:** robustez, pero trazas de fallo pueden ser solo logs.

### 12.4 Disciplina por CLI y por motor

- **Decisión:** `upload_discipline_id` afecta el prompt; la metadata filtra con `get_engine` y `allowed_item_types`.  
- **Consecuencia:** riesgo de desajuste si CLI y fuentes multi-PDF no alinean disciplinas; el sistema lo acepta — puede inferir o advertir (warning si no `--discipline`).

### 12.5 Contrato de columnas Excel / Presto (`presto_constants` vs `export_excel`)

- **Decisión:** `PRESTO_HEADER_CODES` replica el orden y los nombres de `HEADERS` en `export_excel.py` (11 columnas, incl. fuentes y método de precio) para que `assert_presto_header_row_matches_export` garantice un solo contrato.

### 12.6 Reglas de validación por disciplina (`discipline_rules.json`)

- **Decisión:** reglas de mapeo `discipline_to_chapters` (prefijos 01–09 y otros) y `completeness_hints` en JSON bajo `validation/`, cargadas por `load_discipline_rules()` en `validation/budget_validator.py`. Sin este archivo, `run_budget_validation` y los tests asociados no podían completarse.

---

## 13. Limitaciones Conocidas

- **Dependencia de claves y red:** sin `OPENAI_API_KEY` o sin APS, el pipeline deja de ser funcional o se degrada (sin embeddings, sin visión, sin extracción).  
- **Límite de precisión de visión:** páginas ilegibles o baja resolución afectan `quantify_inventory` aguas abajo.  
- **Sincronización PRES/BC3:** pares de entrenamiento son heurísticos; formatos de Excel múltiples añaden ramas.  
- **Códigos Presto/BC3:** longitud 13, sanitización agresiva en export BC3.  
- **Carga de `discipline_rules.json`:** el validador requiere el archivo en `validation/`; en el repositorio actual está presente (mapa mínimo de disciplinas a capítulos; `completeness_hints` vacío salvo ampliación futura).  
- **Rendimiento:** DWG grandes, muchas páginas de PDF, muchas llamadas a OpenAI: coste y tiempo.  
- **Código en `_legacy/` y scripts sueltos:** no garantizados como mantenidos.

---

## 14. Mapa de Dependencias entre Módulos (grafo de texto)

```
dupla_run_full_analysis_local
  -> aps_auth, model_derivative, oss_manager
  -> json_processor
  -> vision_agent
  -> training_data, methodology_generator, bc3_embeddings
  -> parse_bc3
  -> pipeline.build_budget_from_sources
      -> inventory_builder, semantic_* (condicional)
      -> quantifier_agent
      -> rules_engine
      -> partida_generator / classifier_agent
      -> composer
  -> export_excel, export_bc3
  -> stage (PipelineRunner)

classifier_agent -> bc3_embeddings, training_data, schemas

vision_agent -> schemas, openai
```

(Integraciones como `disciplines` y `validation` conectan al `compose_budget` y quantifier; no se expande cada arista a nivel de función en este mapa resumido.)

---

## 15. Glosario

| Término | Significado en este repo / dominio |
|---------|-----------------------------------|
| **BC3** | Formato de intercambio de presupuestos FIEBDC (texto estructurado con `~C`, `~D`, etc.). |
| **FIEBDC** / **Presto** | Norma/herramienta de presupuestación; Presto 8.8 es referencia en comentarios de export. |
| **PRES** | Hoja de presupuesto de referencia (Excel) para pares *few-shot* y plantillas. |
| **Partida** | Línea de medición con precio; en código a veces mapeo a un código BC3. |
| **Capítulo** | Agrupación jerárquica (p. ej. códigos 01–09 en el clasificador, o 01–24 en `PartidaGenerator`). |
| **Takeoff** | `QuantityTakeoff` — medida derivada de entidades (m2, m3, unidad). |
| **APU** | (Dominio) análisis de precio unitario; puede aparecer en descripciones de partidas, no un tipo Python único. |
| **ITBIS** | Impuesto (mención posible en documentación regional; no forzada en el núcleo Python citado). |
| **APS** | Autodesk Platform Services. |
| **SVF2** / **Model Derivative** | Flujo de traducción a viewables y lectura de propiedades. |
| **OCR / visión** | Uso de modelo multimodal para leer imágenes de planos, no un motor OCR clásico separado. |
| **NASAS Preliminary** | Variante de layout Excel consumida vía `budget/nasas_preliminary_io.py`. |

---

*Fin del documento de reingeniería. Para cualquier sección, el detalle "absoluto" (cada rama, cada comentario) está en los archivos citados: este artefacto es un mapa fiel al estado del repositorio en la fecha de análisis, con límites de verificación en línea dónde se indica expresamente.*
