# Reingeniería Completa — Sistema Dupla de Presupuestos de Construcción con IA

## 1. Resumen Ejecutivo
Dupla es un sistema de automatización de presupuestos de construcción que toma como insumos planos técnicos (DWG y/o PDF), extrae inventario constructivo y genera presupuesto en formatos operativos de obra (Excel y BC3/FIEBDC). El camino activo del repositorio está diseñado como pipeline monolítico por etapas, con foco en trazabilidad de cantidades y reutilización de catálogos BC3.

El repositorio combina integración con Autodesk APS (subida DWG, traducción Model Derivative y lectura de propiedades), análisis visual con modelos OpenAI para inventario desde planos renderizados, cuantificación determinística en Python y composición final de partidas presupuestarias. El núcleo funcional está en carpetas agents, core, budget, processors, disciplines, rules_engine y aps_integration.

El estado actual muestra una base técnica amplia y modular, con una suite de pruebas numerosa, pero en el entorno verificado durante esta auditoría la ejecución de tests no completa por faltantes de dependencias y conflictos de colección con código legacy. La arquitectura principal, no obstante, se puede trazar de extremo a extremo desde DWG/PDF hasta Excel/BC3 con artefactos intermedios persistidos en disco.

## 2. Problema de Negocio
- Qué proceso manual reemplaza:
  - Reemplaza la lectura manual de planos, conteo de elementos, estimación de metrajes y armado manual de presupuestos en hojas de cálculo y herramientas de costo.
- Quién es el usuario final:
  - Presupuestistas, ingenieros de costos y equipos técnicos de preconstrucción.
- Qué inputs tiene disponibles el usuario:
  - Archivos DWG de diseño.
  - Planos PDF.
  - Catálogos BC3 para partidas y precios base.
  - Archivo PRES.xlsx histórico para contexto y ejemplos.
  - Reglas por disciplina (domain_rules.yaml).
- Qué output espera recibir:
  - Presupuesto por disciplina en Excel.
  - Presupuesto por disciplina en BC3 (FIEBDC-3/2020).
  - Artefactos de auditoría: inventario de visión, facts CAD, reportes de calidad y reportes de faltantes.
- Qué valor genera la automatización:
  - Reduce tiempo operativo de levantamiento y estructuración de presupuesto.
  - Homogeneiza trazabilidad de cantidades (fórmulas, evidencias y supuestos).
  - Facilita continuidad de flujo hacia herramientas compatibles con BC3.

## 3. Arquitectura General
- Diagrama de bloques en texto (ASCII art)

```text
[DWG] -------------------------------> [APS OSS + Model Derivative]
                                          |
                                          v
                                    [autodesk_raw.json]
                                          |
                                          v
                                  [json_processor.py]
                                          |
                                          v
                                      [cad_facts]

[PDF] ---> [render_pdf_to_images] ---> [page_XXXX.png]
                                          |
                                          v
                              [vision_agent.py / OpenAI Vision]
                                          |
                                          v
                                   [vision_inventory.json]

[cad_facts] + [vision_inventory] ---> [build_hybrid_inventory]
                                          |
                                          v
                                   [LevelInventory[]]
                                          |
                                          v
                                [quantifier_agent.py]
                                          |
                                          v
                                 [QuantityTakeoff[]]
                                          |
                                          v
                               [rules_engine.apply()]
                                          |
                                          v
                             [takeoffs expandidos]
                                          |
                                          v
                [classifier_agent.py / PartidaGenerator / BC3 parser]
                                          |
                                          v
                         [BudgetCandidate por takeoff]
                                          |
                                          v
                                 [budget/composer.py]
                                          |
                                          v
                              [rows, chapters, lines]
                                |                    |
                                v                    v
                  [export_excel.py -> XLSX]   [export_bc3.py -> BC3]
```

- Stack tecnológico completo (lenguaje, frameworks, APIs, bases de datos)
  - Lenguaje: Python 3.11 (entorno verificado).
  - Librerías declaradas en requirements.txt:
    - openai>=1.0
    - python-dotenv>=1.0
    - requests>=2.31
    - pytest>=7.0
    - openpyxl>=3.1
    - pymupdf>=1.24.0
  - Librerías usadas por módulos activos (detectadas en código):
    - numpy (embeddings), yaml (domain rules), pathlib, dataclasses, logging.
  - APIs externas:
    - Autodesk APS Authentication, OSS y Model Derivative.
    - OpenAI Chat Completions y Embeddings.
  - Base de datos:
    - No hay base de datos relacional/no relacional obligatoria en el camino activo.
    - Persistencia basada en archivos JSON/XLSX/BC3 en disco.

- Patrón arquitectónico (pipeline, microservicios, monolito, etc.)
  - Monolito modular en Python con pipeline secuencial por etapas.
  - Orquestación por scripts runner (principalmente dupla_run_gebsa.py).
  - Diseño orientado a artefactos intermedios persistentes por corrida.

- Decisiones de arquitectura clave
  - Pipeline JSON-first (APS/Model Derivative + normalización) en vez de COM como camino principal.
  - Capa de cuantificación determinística separada de capa de IA.
  - Reglas de expansión de takeoffs desacopladas en rules_engine/default_rules.json.
  - Matching BC3 con fallback determinístico cuando no hay LLM o falla generación.
  - Persistencia de estado de corrida con run_state.json por ejecución.

## 4. Estructura del Repositorio
(Tree anotado con propósito de cada carpeta y archivo relevante)

```text
Dupla/
├── dupla_run_gebsa.py                     # Runner principal multi-disciplina GEBSA
├── dupla_run_full_analysis_local.py       # Runner local por etapas con PipelineRunner
├── compare_budget.py                      # Comparador Excel generado vs PRES.xlsx
├── requirements.txt                       # Dependencias activas del pipeline
├── requirements-legacy.txt                # Dependencias para caminos legacy
├── README.md                              # Resumen arquitectura activa
├── PROJECT_OVERVIEW.md / TECHNICAL_DOCS.md / SRS.md
│
├── agents/
│   ├── vision_agent.py                    # Imágenes -> inventario JSON/LevelInventory
│   ├── quantifier_agent.py                # Inventario -> takeoffs determinísticos
│   ├── classifier_agent.py                # Takeoffs -> candidatos BC3
│   ├── partida_generator.py               # Generación de partidas con LLM
│   └── partida_adapter.py                 # Adaptación de partidas generadas a formato legacy
│
├── core/
│   ├── schemas.py                         # Dataclasses de contexto, inventario, takeoffs y presupuesto
│   ├── pipeline.py                        # Orquestación de inventario híbrido, semantic layer y budget
│   ├── inventory_builder.py               # Merge CAD + visión
│   ├── semantic_enrichment.py             # Enriquecimiento semántico determinístico
│   ├── quality_engine.py                  # Evaluación de calidad semántica
│   ├── semantic_adapter.py                # Filtra elementos BLOCKED
│   ├── output_structure.py                # Layout de salida por corrida
│   ├── openai_chat_models.py              # Configuración central de modelos OpenAI
│   └── stage.py                           # PipelineRunner por etapas (runner local)
│
├── budget/
│   ├── composer.py                        # Composición final de capítulos/líneas/rows
│   ├── chapter_rules.py                   # Mapeos de capítulo y fallback BC3
│   ├── export_excel.py                    # Exportación workbook
│   ├── export_bc3.py                      # Exportación FIEBDC-3
│   ├── consolidator.py                    # Consolidación de presupuestos
│   └── pres_structural_filter.py          # Filtros de item_types estructurales
│
├── aps_integration/
│   ├── aps_auth.py                        # OAuth 2-legged
│   ├── oss_manager.py                     # Buckets, signed URLs, upload de archivos
│   ├── model_derivative.py                # Traducción SVF2 y extracción de propiedades
│   ├── da_manager.py                      # Design Automation (uso no principal)
│   ├── build_plugin.py                    # Build plugin .NET (soporte)
│   └── DuplaExtractor/                    # Proyecto C# asociado
│
├── processors/
│   ├── json_processor.py                  # Autodesk JSON -> cad_facts normalizado
│   ├── bc3_parser.py                      # Parser BC3 reutilizable
│   ├── construcosto_parser.py             # Parser CSV de costos
│   └── text_extractor.py / explore_json.py
│
├── disciplines/
│   ├── base.py / registry.py              # Protocolo de engine y fábrica por disciplina
│   ├── domain_rules.py                    # Loader YAML de reglas de dominio
│   ├── domain_validator.py                # Validación post-visión
│   ├── arquitectura/                      # engine, quantifier, chapters, domain_rules.yaml
│   ├── estructura/                        # engine, quantifier, rebar, chapters, domain_rules.yaml
│   ├── electrico/                         # engine, quantifier, chapters, domain_rules.yaml
│   └── sanitario/                         # engine, quantifier, chapters, domain_rules.yaml
│
├── rules_engine/
│   ├── registry.py                        # Definiciones y aplicación de reglas
│   ├── default_rules.json                 # Reglas de expansión configurables
│   └── __init__.py                        # RulesEngine / default_rules_engine
│
├── knowledge/
│   ├── training_data.py                   # Extract training pairs desde PRES.xlsx
│   ├── methodology_generator.py           # Contexto metodológico automático
│   ├── bc3_embeddings.py                  # Índice semántico BC3
│   ├── pres_expansion.py                  # Expansión sintética de takeoffs
│   ├── office_methodology.md              # Criterio manual de oficina
│   ├── prompts/
│   │   ├── arquitectura/user_prompt.md
│   │   ├── estructura/user_prompt.md
│   │   ├── electrico/user_prompt.md
│   │   └── sanitario/user_prompt.md
│   └── cache/                             # Caché de embeddings
│
├── pricing/
│   └── construcosto_loader.py             # Carga y búsqueda de precios de CSV externos
│
├── validation/
│   ├── discipline_inference.py            # Inferencia de disciplina de takeoff
│   └── budget_validator.py                # Validaciones de coherencia de presupuesto
│
├── scripts/                               # Runners auxiliares y auditoría
├── tests/                                 # Suite de pruebas activa
├── data/                                  # Catálogos BC3, PRES.xlsx, CSV costos, archivos de referencia
├── examples/                              # Muestras JSON/XLSX de salida
├── output/                                # Salidas de corridas
└── _legacy/                               # Código retirado/experimental y tests legacy
```

## 5. Pipeline Principal — Flujo Completo Paso a Paso
### 5.1 Etapa: Arranque, argumentos y preflight
- Archivo(s) involucrado(s)
  - dupla_run_gebsa.py
- Función(es) principal(es) con signature
  - main() -> None
  - run_preflight(disciplines: dict[str, dict[str, str]], bc3_path: str) -> list[str]
- Input: qué recibe (tipo, estructura, ejemplo)
  - CLI:
    - --only str
    - --resume bool
    - --skip-aps bool
  - Config estática en el runner:
    - DISCIPLINES dict por disciplina con rutas pdf/dwg
    - BC3_PATH, XLSX_TRAINING_PATH, OUTPUTS_DIR
- Procesamiento: qué hace internamente (lógica, no código)
  - Determina disciplinas activas.
  - Si skip-aps está activo, elimina clave dwg de disciplinas activas para ese run.
  - Verifica existencia de archivos de entrada y reglas por disciplina.
  - Verifica credenciales y dependencias mínimas.
- Output: qué produce (tipo, estructura, ejemplo)
  - Lista de errores de preflight.
  - Si vacía, continúa; si no, termina proceso.
- Dependencias: qué necesita para funcionar
  - os.getenv, pathlib.Path, módulos yaml y fitz instalados.
- Errores posibles y manejo
  - Falta archivo, falta .env, faltan dependencias: registra error y hace sys.exit(1).
- Decisiones de diseño en esta etapa
  - Preflight estricto antes de cualquier costo de API.
  - Validación por disciplina de prompt y domain_rules.

### 5.2 Etapa: Creación de estructura de salida y estado de corrida
- Archivo(s) involucrado(s)
  - dupla_run_gebsa.py
  - core/output_structure.py
- Función(es) principal(es) con signature
  - RunOutputDir.__init__(base_dir: str | Path, project_name: str, timestamp: str | None = None)
  - load_run_state(run_dir: RunOutputDir) -> dict[str, dict[str, Any]]
  - save_run_state(run_dir: RunOutputDir, state: dict) -> None
- Input
  - OUTPUTS_DIR + PROJECT_NAME + timestamp actual.
- Procesamiento
  - Crea carpeta raíz de corrida.
  - Configura log file handler adicional en dupla_debug.log.
  - Construye o recupera run_state.json.
- Output
  - Árbol de salida con rutas utilitarias para cada artefacto.
- Side effects
  - Escritura de carpetas y archivos en disco.
- Errores
  - Fallos de permisos de escritura (no hay captura específica en este tramo).
- Decisiones
  - Estructura por timestamp para corridas reproducibles y no destructivas.

### 5.3 Etapa: Carga de recursos compartidos (única por corrida)
- Archivo(s)
  - dupla_run_gebsa.py
  - processors/bc3_parser.py
  - knowledge/bc3_embeddings.py
  - knowledge/training_data.py
  - knowledge/methodology_generator.py
- Función(es)
  - parse_bc3(path: str) -> dict[str, Any]
  - merge_bc3_catalogs(*catalogs: dict[str, Any]) -> dict[str, Any]
  - load_or_build_embeddings(bc3_catalog: dict[str, Any], ...) -> EmbeddingIndex | None
  - extract_training_pairs(xlsx_path: str | Path) -> list[TrainingPair]
  - generate_methodology_context(training_pairs: list[TrainingPair] | None, bc3_catalog: dict[str, Any] | None, ...) -> str
- Input
  - data/*.bc3
  - data/PRES.xlsx
- Procesamiento
  - Parsea y fusiona catálogos BC3.
  - Construye/carga embeddings del catálogo.
  - Extrae pares de entrenamiento de PRES.xlsx.
  - Genera contexto metodológico automático.
- Output
  - shared dict con:
    - bc3_catalog
    - bc3_path_value
    - embedding_index
    - training_pairs
    - xlsx_path
    - auto_methodology
- Side effects
  - Lectura de archivos de datos.
  - Escritura de caché de embeddings en knowledge/cache.
- Errores y manejo
  - Si no hay BC3, termina con error.
  - Embeddings y training pueden degradar a None/lista vacía según disponibilidad.
- Decisiones
  - Cargar una vez para reutilizar en todas las disciplinas.

### 5.4 Etapa: Extracción APS desde DWG (por disciplina)
- Archivo(s)
  - dupla_run_gebsa.py
  - aps_integration/aps_auth.py
  - aps_integration/oss_manager.py
  - aps_integration/model_derivative.py
  - processors/json_processor.py
- Función(es)
  - get_aps_token()
  - create_bucket(token, bucket_name)
  - upload_file_to_bucket(token, bucket_name, file_path, object_name=None, unique_suffix=None)
  - extract_dwg_data(token, bucket_key, object_name, views=..., translation_timeout_seconds=..., ... ) -> dict
  - process_autodesk_json(json_path: str) -> dict[str, Any]
- Input
  - Ruta DWG de la disciplina.
  - Credenciales APS desde .env.
- Procesamiento
  - OAuth 2-legged.
  - Asegura bucket OSS.
  - Sube DWG con sufijo único.
  - Traduce a SVF2 y espera manifest.
  - Obtiene metadata y propiedades por vista.
  - Normaliza a cad_facts.
- Output
  - autodesk_raw.json
  - cad_facts.json
  - dict cad_facts en memoria.
- Side effects
  - Llamadas HTTP a Autodesk.
  - Escritura de JSONs en carpeta de disciplina.
- Errores y manejo
  - Captura Exception en runner y continúa con cad_facts = {} (PDF-only fallback).
- Decisiones
  - Resiliencia: si APS falla, el pipeline sigue con visión.
  - Polling configurable para manifest y propiedades.

### 5.5 Etapa: Render de PDF a imágenes
- Archivo(s)
  - dupla_run_gebsa.py
- Función(es)
  - render_pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list[Path]
- Input
  - PDF de disciplina.
- Procesamiento
  - Usa PyMuPDF (fitz) para rasterizar cada página a PNG.
- Output
  - Lista de paths de imágenes page_XXXX.png.
- Side effects
  - Escritura de imágenes en rendered_pages/p_<hash>.
- Errores y manejo
  - Si falla fitz/open de PDF, excepción sube y se registra como error de disciplina.
- Decisiones
  - DPI fijo 200 para balance de legibilidad/costo.

### 5.6 Etapa: Análisis de visión por página
- Archivo(s)
  - dupla_run_gebsa.py
  - agents/vision_agent.py
  - knowledge/prompts/*/user_prompt.md
- Función(es)
  - run_full_vision_analysis(pages_dir: str, cad_summary: dict[str, Any], office_methodology: str | None = None, upload_discipline_id: str | None = None) -> list[dict[str, Any]]
  - analyze_plan(image_path: Path, cad_summary: dict[str, Any], level_name: str, office_methodology: str | None = None, upload_discipline_id: str | None = None) -> dict[str, Any]
- Input
  - Carpeta de imágenes renderizadas.
  - cad_facts (puede ser vacío).
  - metodología combinada (auto + manual).
  - disciplina de subida.
- Procesamiento
  - Construye prompt de usuario con placeholders:
    - {view_type}, {level_name}, {upload_block}, {methodology_block}, {cad_hints}, {schema}
  - Usa _SIMPLE_SYSTEM_PROMPT y _SIMPLE_SCHEMA_HINT.
  - Trunca metodología a _MAX_OFFICE_METHODOLOGY_CHARS = 12000.
  - Invoca OpenAI chat completions con imagen base64.
  - Parsea JSON de respuesta y adapta a LevelInventory completo.
- Output
  - Lista de dicts de inventario por página.
  - En runner: vision_inventory.json por disciplina.
- Side effects
  - Llamadas a OpenAI.
  - Escritura de JSON de visión.
- Errores y manejo
  - Error por página: se registra y se agrega objeto con {"error": ...} para esa imagen.
- Decisiones
  - Pipeline de visión en dos pasos: respuesta simple del modelo + adaptación Python.
  - Prompt por disciplina configurable vía markdown externo.

### 5.7 Etapa: Validación de dominio post-visión
- Archivo(s)
  - dupla_run_gebsa.py
  - disciplines/domain_rules.py
  - disciplines/domain_validator.py
- Función(es)
  - load_domain_rules_for_discipline(discipline_id: str) -> DomainRules | None
  - validate_vision_output(vision_results: list[dict[str, Any]], rules: DomainRules, project_name: str = "") -> ValidationResult
  - write_unclassified_report(result: ValidationResult, output_path: Path) -> Path | None
  - write_missing_attributes_report(result: ValidationResult, output_path: Path) -> Path | None
- Input
  - vision_results.
  - domain_rules.yaml de la disciplina.
- Procesamiento
  - Clasifica elementos en belongs / not_belongs / unclassified.
  - Verifica atributos obligatorios definidos en reglas.
- Output
  - reportes de no clasificados y atributos faltantes.
- Side effects
  - Escritura de txt/json de reportes.
- Errores y manejo
  - Si no hay reglas, omite etapa sin fallar.
- Decisiones
  - Gate de calidad disciplinario externo al modelo IA.

### 5.8 Etapa: Construcción del presupuesto core
- Archivo(s)
  - dupla_run_gebsa.py
  - core/pipeline.py
  - core/inventory_builder.py
  - core/semantic_enrichment.py
  - core/quality_engine.py
  - core/semantic_adapter.py
  - agents/quantifier_agent.py
  - rules_engine/__init__.py + rules_engine/registry.py + rules_engine/default_rules.json
  - agents/classifier_agent.py
  - agents/partida_generator.py + agents/partida_adapter.py
  - budget/composer.py
- Función(es)
  - build_budget_from_sources(context: ProjectContext, cad_facts: dict[str, Any], vision_payloads: ..., bc3_catalog: dict[str, Any], rules_engine: RulesEngine | None = None, *, embedding_index: Any | None = None, training_pairs: list[Any] | None = None) -> dict[str, Any]
- Input
  - ProjectContext con metadata de disciplina y allowed_item_types.
  - cad_facts y vision payloads.
  - bc3_catalog + embeddings + training_pairs.
- Procesamiento
  - build_hybrid_inventory: fusiona CAD y visión por nivel.
  - Capa semántica opcional:
    - enrich_semantics
    - evaluate_semantic_quality
    - adapt_semantic_to_inventory si hay BLOCKED.
  - quantify_inventory: genera takeoffs determinísticos trazables.
  - rules_engine.apply: deriva takeoffs por reglas JSON.
  - merge_pres_template_takeoffs (si está habilitado).
  - _match_or_generate:
    - intenta PartidaGenerator (si OPENAI_API_KEY)
    - fallback match_takeoffs_to_bc3.
  - compose_budget: genera chapters, lines, rows y diagnósticos.
- Output
  - budget dict con:
    - chapters
    - lines
    - rows
    - budget_lines
    - takeoffs
    - candidates_by_takeoff
    - hybrid_inventory
    - base_takeoffs
    - quality_report (si semantic layer activa)
- Side effects
  - Carga opcional de snapshot de precios ConstruCosto.
- Errores y manejo
  - PartidaGenerator falla: fallback a matching BC3.
  - En varias sub-etapas se captura y continua con degradación funcional.
- Decisiones
  - Separación estricta de cuantificación determinística vs generación/matching IA.

### 5.9 Etapa: Exportación de salida final
- Archivo(s)
  - budget/export_excel.py
  - budget/export_bc3.py
  - dupla_run_gebsa.py
- Función(es)
  - export_budget_workbook(context: ProjectContext, rows: Iterable[BudgetRow | Mapping[str, object]], output_path: str | Path, *, sheet_name: str = "Presupuesto", quality_report: Mapping[str, Any] | None = None) -> Path
  - export_budget_bc3(context: ProjectContext, rows: list[BudgetRow | Mapping[str, object]], output_path: str | Path, *, bc3_catalog: dict[str, Any] | None = None) -> Path
- Input
  - rows del presupuesto compuesto.
  - quality_report opcional.
- Procesamiento
  - Excel:
    - crea hoja principal con encabezados fijos.
    - aplica estilos por tipo de fila (chapter/subtotal/line).
    - agrega hoja de quality report y hoja PENDIENTES.
  - BC3:
    - emite registros ~V, ~K, ~C, ~D, ~M, ~T.
    - sanea códigos para límite Presto (13 chars).
    - incorpora descomposición APU cuando existe en catálogo.
- Output
  - presupuesto_<disciplina>.xlsx
  - presupuesto_<disciplina>.bc3
  - budget_output.json
  - quality_report.json + INPUT_GAPS.md
- Side effects
  - Escritura de archivos en carpeta de disciplina.
- Errores y manejo
  - Excel: fallback de nombre cuando el archivo está bloqueado por PermissionError.
  - BC3: errores de IO suben al caller.
- Decisiones
  - Export compatible con Presto 8.8 y FIEBDC-3/2020.

### 5.10 Etapa: Resumen de corrida y persistencia de estado
- Archivo(s)
  - dupla_run_gebsa.py
- Función(es)
  - save_run_state
- Input
  - resultados por disciplina.
- Procesamiento
  - Persiste estado tras cada disciplina.
  - Escribe run_summary.json global.
- Output
  - run_state.json
  - run_summary.json
- Errores y manejo
  - Si una disciplina falla, queda status=error y el pipeline continúa con las demás.
- Decisiones
  - Fault isolation por disciplina para evitar aborto total por falla parcial.

## 6. Módulos de Soporte
### 6.1 agents
- Propósito
  - Implementar extracción por visión, cuantificación y selección/generación de partidas.
- Archivos y funciones clave
  - agents/vision_agent.py
    - analyze_plan(image_path, cad_summary, level_name, *, office_methodology=None, upload_discipline_id=None)
    - run_full_vision_analysis(pages_dir, cad_summary, *, office_methodology=None, upload_discipline_id=None)
  - agents/quantifier_agent.py
    - quantify_inventory(levels, *, runner_source_discipline=None)
  - agents/classifier_agent.py
    - match_takeoffs_to_bc3(takeoffs, bc3_catalog, top_k=3, *, embedding_index=None, training_pairs=None, project_discipline_id=None)
  - agents/partida_generator.py
    - PartidaGenerator.generate(...)
  - agents/partida_adapter.py
    - adapt_generated_to_legacy_format(...)
- Cómo se integra con el pipeline
  - Invocado por core/pipeline.py y runners.
- Configuración necesaria
  - OPENAI_API_KEY.
  - OPENAI_VISION_* y OPENAI_CHAT_* opcionales.

### 6.2 core
- Propósito
  - Núcleo de modelos y orquestación técnica.
- Archivos y funciones clave
  - core/schemas.py: modelos de datos tipados.
  - core/pipeline.py: build_budget_from_sources, build_hybrid_inventory.
  - core/inventory_builder.py: merge de entidades CAD+visión.
  - core/semantic_enrichment.py: enrich_semantics.
  - core/quality_engine.py: evaluate_semantic_quality.
  - core/semantic_adapter.py: adapt_semantic_to_inventory.
  - core/output_structure.py: RunOutputDir.
  - core/openai_chat_models.py: resolución de modelos y parámetros OpenAI.
  - core/stage.py: PipelineRunner.
- Integración
  - Consumido por runners, budget y tests.
- Configuración
  - Variables OPENAI_*
  - Metadata en ProjectContext.

### 6.3 budget
- Propósito
  - Convertir takeoffs/candidatos en presupuesto estructurado exportable.
- Archivos clave
  - budget/composer.py
    - compose_budget, compose_budget_rows, takeoff_budget_eligibility.
  - budget/chapter_rules.py
    - chapter_path_for_takeoff, default_bc3_code_for_takeoff, select_strong_candidate.
  - budget/export_excel.py
    - export_budget_workbook.
  - budget/export_bc3.py
    - export_budget_bc3.
- Integración
  - Llamado desde core/pipeline.py y runners.
- Configuración
  - bc3_catalog opcional para descomposición APU.

### 6.4 aps_integration
- Propósito
  - Operar autenticación, almacenamiento y traducción APS.
- Archivos clave
  - aps_auth.py: get_aps_token.
  - oss_manager.py: create_bucket, upload_file_to_bucket, generate_signed_url.
  - model_derivative.py: extract_dwg_data y helpers de polling.
- Integración
  - Llamado por runners antes de visión.
- Configuración
  - CLIENT_ID, CLIENT_SECRET, APS_BUCKET_NAME.

### 6.5 processors
- Propósito
  - Parsing y normalización de formatos externos.
- Archivos clave
  - processors/json_processor.py: process_autodesk_json.
  - processors/bc3_parser.py: parse_bc3, merge_bc3_catalogs.
- Integración
  - consumido por core/pipeline y runners.
- Configuración
  - encoding de origen (latin-1 para BC3).

### 6.6 disciplines
- Propósito
  - Configuración y reglas por disciplina funcional.
- Archivos clave
  - disciplines/registry.py: get_engine(discipline_id).
  - disciplines/base.py: protocolos y configuraciones.
  - disciplines/domain_rules.py: carga de YAML.
  - disciplines/domain_validator.py: validación post-visión.
  - subcarpetas por disciplina con engine/quantifier/chapters.
- Integración
  - runners y pipeline usan discipline_id para filtros y comportamiento.
- Configuración
  - domain_rules.yaml en cada disciplina.

### 6.7 knowledge
- Propósito
  - Contexto semántico, embeddings, prompts y dataset de entrenamiento.
- Archivos clave
  - training_data.py: extract_training_pairs.
  - methodology_generator.py: generate_methodology_context.
  - bc3_embeddings.py: load_or_build_embeddings, batch_search_bc3.
  - prompts/*/user_prompt.md: plantillas por disciplina.
- Integración
  - visión y clasificación.
- Configuración
  - OPENAI_API_KEY para embeddings.

### 6.8 pricing
- Propósito
  - Resolver precios desde CSV ConstruCosto.
- Archivo clave
  - pricing/construcosto_loader.py.
- Integración
  - budget/composer.py intenta precio ConstruCosto antes de fallback BC3.

### 6.9 rules_engine
- Propósito
  - Derivación determinística configurable de takeoffs.
- Archivos
  - rules_engine/registry.py
  - rules_engine/default_rules.json
- Integración
  - core/pipeline.py en build_budget_from_inventory/build_budget_from_sources.

### 6.10 validation
- Propósito
  - Validaciones transversales de disciplina y presupuesto.
- Archivos
  - validation/discipline_inference.py
  - validation/budget_validator.py
- Integración
  - composer y pipeline.

## 7. Modelos de Datos
### 7.1 Esquemas internos
(Dataclasses, TypedDicts, esquemas JSON — con campos, tipos, y ejemplo)

Principales dataclasses en core/schemas.py:
- ProjectContext
  - project_id: str | None
  - project_name: str | None
  - source_json_path: str | None
  - plan_image_paths: list[str]
  - bc3_path: str | None
  - measurement_unit: str
  - metadata: dict[str, Any]
- InventoryEntity (base)
  - id: str
  - level_id: str | None
  - source: Literal[json, vision, hybrid]
  - source_refs, assumptions, inputs, conflict_notes, confidence, evidence
- LevelInventory
  - level_id, level_name, source
  - floor_area_m2, ceiling_area_m2, space_types
  - walls, openings, doors, windows, wet_areas, kitchens, stairs, fixtures, structural_elements
- QuantityTrace
  - source_entity_ids, source_entity_sources, steps, evidence, conflict_notes, metadata
- QuantityTakeoff
  - item_key, item_type, level_id, unit, quantity, formula, inputs, assumptions, source_refs, trace
- BudgetCandidate
  - takeoff_key, bc3_code, summary, unit, score, rationale, source, bc3_origin
- BudgetChapter
  - chapter_id, code, title, level, parent_id, path, child_ids, line_keys
- BudgetLine
  - line_id, takeoff_key, chapter_id, code, nat, unit, summary, quantity, unit_price, amount_formula, metadata
- BudgetRow
  - row_type (chapter|line|subtotal), code, nat, unit, summary, quantity, unit_price, amount, metadata, excel_row

Ejemplo real de salida híbrida (examples/sample_hybrid_pipeline_result.json):

```json
{
  "hybrid_inventory_excerpt": {
    "level_id": "level_01",
    "source": "hybrid",
    "floor_area_m2": 100.0,
    "conflict_notes": [
      "Conflict on floor_area_m2: kept JSON value 100.0, vision suggested 95.0."
    ],
    "walls": [
      {
        "id": "json-wall-a-wall",
        "length_m": 10.0,
        "height_m": 3.0
      }
    ]
  }
}
```

Ejemplo real de takeoff (examples/sample_structural_takeoffs.json):

```json
{
  "item_key": "beam_demo:concrete_volume",
  "item_type": "beam_concrete_volume",
  "unit": "m3",
  "quantity": 1.125,
  "formula": "structural_element.span_m * structural_element.count * structural_element.section_width_m * structural_element.section_height_m"
}
```

### 7.2 Datos de entrada
(Estructura de cada archivo de datos: CSVs, BC3, XLSX)

- data/PRES.xlsx
  - Hoja: Hoja1
  - Filas: 2450
  - Columnas: 7
  - Encabezados (fila 3):
    - Código
    - Nat
    - Ud
    - Resumen
    - CanPres
    - PrPres
    - ImpPres
  - Ejemplos reales:
    - TGIU0001, Capítulo, PRELIMINARES
    - P0112001, Partida, P.A., Almacén y Oficina de la Obra

- data/GIV00001 (1).bc3
  - Tamaño: 36,485,115 bytes
  - Uso: catálogo principal BC3 (items, capítulos, descomposición).
  - Parseado por processors/bc3_parser.py (encoding latin-1).

- data/TGIU.bc3
  - Tamaño: 9,670,521 bytes
  - Uso: catálogo adicional/fallback.

- data/construcosto/*.csv
  - Analisis de Costos Punta Cana ConstruCosto.csv
    - filas: 5982, columnas: 14
  - Equipos y Movimientos de Tierra Punta Cana ConstruCosto.csv
    - filas: 474, columnas: 11
  - Mano de obra  Punta Cana ConstruCosto.csv
    - filas: 876, columnas: 18
  - Materiales e Insumos Punta Cana ConstruCosto.csv
    - filas: 1519, columnas: 7

- data/presto_files/*
  - Archivos de referencia de entorno Presto (pzh, imágenes, rtf).

Clasificación de origen de datos:
- Input estático: BC3, PRES.xlsx, CSV ConstruCosto, prompts markdown, rules yaml/json.
- Input operativo: DWG/PDF externos configurados en runner.
- Cache generado: knowledge/cache/*.npz de embeddings.

### 7.3 Datos de salida
(Estructura del Excel generado, del archivo BC3, de logs/traces)

- Excel generado (budget/export_excel.py)
  - Hoja principal:
    - Encabezados:
      - Código, Nat, Ud, Resumen, CanPres, PrPres, ImpPres, Fuente Cantidad, Fuente Precio, BC3 Origen, Método de Precio
    - Filas de tipos chapter, line, subtotal con estilos distintos.
  - Hoja Quality_Report (si aplica): issues por estado.
  - Hoja PENDIENTES: líneas con precio pendiente.

- BC3 generado (budget/export_bc3.py)
  - Registros emitidos:
    - ~V versión/charset
    - ~K parámetros regionales
    - ~C conceptos (root/capítulos/partidas)
    - ~D descomposición
    - ~M mediciones
    - ~T textos largos
  - Compatibilidad objetivo: Presto 8.8, codificación cp1252.

- Reportes intermedios y de trazabilidad
  - autodesk_raw.json
  - cad_facts.json
  - vision_inventory.json
  - budget_output.json
  - quality_report.json
  - INPUT_GAPS.md
  - run_state.json
  - run_summary.json
  - dupla_debug.log

Ejemplo real de estructura de presupuesto compuesto (examples/sample_budget_composer_output.json):
- project_context
- chapters[]
- lines[]
- rows[]

## 8. Integraciones Externas
### 8.1 Autodesk APS
- Qué hace en el sistema
  - Autenticación, subida de DWG y extracción de propiedades técnicas del modelo.
- Endpoints usados
  - Authentication:
    - https://developer.api.autodesk.com/authentication/v2/token
  - OSS:
    - https://developer.api.autodesk.com/oss/v2/buckets
    - https://developer.api.autodesk.com/oss/v2/buckets/{bucket}/objects/{object}/signed
  - Model Derivative:
    - https://developer.api.autodesk.com/modelderivative/v2/designdata/job
    - https://developer.api.autodesk.com/modelderivative/v2/designdata/{urn}/manifest
    - https://developer.api.autodesk.com/modelderivative/v2/designdata/{urn}/metadata
    - https://developer.api.autodesk.com/modelderivative/v2/designdata/{urn}/metadata/{guid}/properties
- Formato de request/response
  - Auth: x-www-form-urlencoded client_credentials.
  - OSS/MD: JSON REST con Bearer token.
- Configuración y credenciales
  - CLIENT_ID, CLIENT_SECRET, APS_BUCKET_NAME.
- Límites y costos
  - No hay límites explícitos codificados; hay timeouts/polling configurables.
  - Traducciones de gran tamaño pueden tardar significativamente.
- Fallbacks si falla
  - En runner principal, APS failure en disciplina cae a PDF-only con warning.

### 8.2 OpenAI API
- Qué hace en el sistema
  - Análisis visual por página.
  - Clasificación/generación de partidas BC3.
  - Embeddings semánticos de catálogo.
- Endpoints usados
  - Chat Completions.
  - Embeddings.
- Formato de request/response
  - Chat con mensajes system/user, en visión incluye image_url base64.
  - Embeddings por batch de textos.
- Configuración y credenciales
  - OPENAI_API_KEY
  - OPENAI_VISION_MODEL, OPENAI_VISION_MAX_OUTPUT, OPENAI_VISION_REASONING_EFFORT, OPENAI_VISION_TEMPERATURE
  - OPENAI_CHAT_MODEL, OPENAI_CHAT_MAX_OUTPUT, OPENAI_CHAT_REASONING_EFFORT, OPENAI_CHAT_TEMPERATURE
- Límites y costos
  - Costos no modelados en código.
  - Límite funcional: max output tokens configurable (default 4096 en visión/chat helpers).
- Fallbacks si falla
  - En matching de partidas, si falla ruta LLM se usa ranking determinístico por tokens/embeddings.
  - En visión por página, error se encapsula por página y la corrida continúa.

### 8.3 ConstruCosto (dataset externo en CSV)
- Qué hace en el sistema
  - Proveer precio unitario alterno para líneas presupuestarias.
- Endpoints usados
  - No aplica (lectura local CSV).
- Configuración y credenciales
  - No requiere credenciales.
- Fallbacks
  - Si no hay snapshot o match de precio, composer cae a BC3 o PRECIO_PENDIENTE.

## 9. Prompts de IA
### 9.1 Prompt de Visión
- Texto completo del prompt (o resumen si es muy largo)
  - Prompt principal definido en agents/vision_agent.py:
    - _SIMPLE_SYSTEM_PROMPT: instruye extracción exhaustiva de elementos constructivos.
    - _SIMPLE_SCHEMA_HINT: define JSON esperado (plan_type, walls, doors, windows, wet_areas, kitchens, stairs, structural_elements, electrical, plumbing, fixtures, etc.).
  - Además soporta plantillas disciplinares en knowledge/prompts/<disciplina>/user_prompt.md con placeholders.
- Qué se inyecta dinámicamente (metodología, CAD facts, etc.)
  - {view_type}
  - {level_name}
  - {methodology_block}
  - {upload_block}
  - {cad_hints}
  - {schema}
- Qué output espera del modelo
  - JSON válido (sin markdown) conforme al schema hint.
- Truncados y límites de tokens
  - _MAX_OFFICE_METHODOLOGY_CHARS = 12000 para metodología inyectada.
  - OPENAI_VISION_MAX_OUTPUT default 4096.

### 9.2 Prompt del Clasificador
- Texto completo del prompt (o resumen si es muy largo)
  - En agents/classifier_agent.py::_gpt4o_classify_chapter:
    - Prompt por capítulo BC3.
    - Incluye lista de takeoffs y subconjunto de catálogo BC3.
    - Instruye que bc3_code debe venir del catálogo y unit_price debe respetar price de catálogo.
- Qué se inyecta dinámicamente
  - chapter_code, chapter_desc.
  - few_shot_examples desde training_data.
  - project_discipline_id.
  - takeoff_lines y bc3_lines.
- Qué output espera
  - JSON array:
    - takeoff_key
    - bc3_code
    - unit_price
    - match_type
- Truncados y límites
  - Máximo 80 ítems BC3 por prompt (en código).
  - max_tokens=2048 para llamada GPT-4o en ese método.

### 9.3 Cualquier otro prompt
- Prompts disciplinares markdown:
  - knowledge/prompts/arquitectura/user_prompt.md
  - knowledge/prompts/estructura/user_prompt.md
  - knowledge/prompts/electrico/user_prompt.md
  - knowledge/prompts/sanitario/user_prompt.md
- Base de sistema:
  - knowledge/prompts/base_system.md
- Contexto metodológico:
  - knowledge/office_methodology.md (manual)
  - knowledge/methodology_generator.py (automático)

## 10. Sistema de Tests
- Qué se testea
  - Parsing BC3 y embeddings.
  - Cuantificación (incluyendo wet areas y estructural).
  - Reglas de expansión (walls/openings/floors/ceilings/wet_areas).
  - Composición y exportación de presupuesto.
  - Integración de pipeline (tests/test_pipeline_integration.py).
  - Módulos de metodología, feedback store, adapters y generadores de partida.
- Qué falta testear
  - Integración real contra APIs externas (APS/OpenAI) en entorno CI local verificado.
  - Flujos E2E multi-disciplina con activos reales externos (DWG/PDF no incluidos en repo).
  - Aislamiento explícito entre tests legacy y tests activos.
- Cómo correr tests
  - python -m pytest -q -ra
- Estado actual (pasando/fallando)
  - Verificación ejecutada en entorno local: la colección falló con 24 errores.
  - Causas observadas en reporte:
    - ModuleNotFoundError: ezdxf (tests legacy cad_automation).
    - ModuleNotFoundError: win32com (tests legacy).
    - ModuleNotFoundError: numpy (tests activos que importan knowledge/bc3_embeddings.py).
    - FileNotFoundError en _legacy/test_vision.py por ruta local hardcoded externa.
    - import file mismatch entre _legacy/test_model_derivative.py y tests/test_model_derivative.py.
  - No pude verificar test pass-rate de módulos activos porque la colección se interrumpe antes de ejecutar suite completa.

## 11. Configuración y Despliegue
- Variables de entorno necesarias
  - OPENAI_API_KEY
  - CLIENT_ID
  - CLIENT_SECRET
  - APS_BUCKET_NAME
  - OPENAI_CHAT_MODEL
  - OPENAI_CHAT_MAX_OUTPUT
  - OPENAI_CHAT_REASONING_EFFORT
  - OPENAI_CHAT_TEMPERATURE
  - OPENAI_VISION_MODEL
  - OPENAI_VISION_MAX_OUTPUT
  - OPENAI_VISION_REASONING_EFFORT
  - OPENAI_VISION_TEMPERATURE
- Cómo instalar dependencias
  - pip install -r requirements.txt
  - Para componentes legacy: pip install -r requirements-legacy.txt
- Cómo correr el sistema
  - Runner principal GEBSA:
    - python dupla_run_gebsa.py
    - python dupla_run_gebsa.py --only arquitectura
    - python dupla_run_gebsa.py --resume
    - python dupla_run_gebsa.py --skip-aps
  - Runner local por etapas:
    - python dupla_run_full_analysis_local.py --discipline arquitectonica
- Requisitos del entorno (Python version, etc.)
  - Entorno verificado durante análisis: Python 3.11.1.
  - Windows (se observan rutas y comportamientos orientados a Windows).
  - Dependencias de sistema para algunos módulos legacy (COM/AutoCAD) no forman parte del camino activo.

## 12. Decisiones de Diseño y Trade-offs
### 12.1 Pipeline JSON-first en camino activo
- Contexto
  - El repositorio mantiene código COM legacy, pero el flujo activo se describe como APS/JSON-first.
- Decisión tomada
  - Usar Autodesk APS + normalización JSON como fuente principal de facts CAD.
- Alternativas descartadas
  - Automatización COM/AutoCAD directa como camino principal.
- Consecuencias
  - Buenas: desacopla de AutoCAD local para el flujo principal; permite fallback PDF-only.
  - Malas: depende de disponibilidad y latencia de APS.
- Evaluación actual (¿fue buena decisión?)
  - En estado actual, esta decisión está reflejada consistentemente en README, runners y módulos core.

### 12.2 Cuantificación determinística separada de IA
- Contexto
  - El sistema mezcla IA para percepción/matching y cálculo de cantidades para presupuesto.
- Decisión tomada
  - Mantener fórmulas y reglas de cantidades en agentes/quantifier_agent.py y rules_engine.
- Alternativas descartadas
  - Delegar cantidades finales directamente al modelo IA.
- Consecuencias
  - Buenas: trazabilidad por fórmula y metadata.
  - Malas: requiere mantenimiento de reglas y defaults.
- Evaluación actual
  - El código y ejemplos muestran trazabilidad explícita de item_key/formula/assumptions.

### 12.3 Matching BC3 con fallback múltiple
- Contexto
  - Selección de partidas puede fallar por ausencia de API key o respuesta LLM inválida.
- Decisión tomada
  - Ruta preferente con PartidaGenerator/GPT y fallback a match_takeoffs_to_bc3 determinístico.
- Alternativas descartadas
  - Pipeline estrictamente dependiente de una sola ruta LLM.
- Consecuencias
  - Buenas: degradación funcional controlada.
  - Malas: consistencia de resultados puede variar entre rutas.
- Evaluación actual
  - Implementación robusta en core/pipeline.py::_match_or_generate.

### 12.4 Persistencia extensa de artefactos por corrida
- Contexto
  - Necesidad de auditoría y depuración por disciplina.
- Decisión tomada
  - Escribir múltiples JSON/reportes/logs por corrida.
- Alternativas descartadas
  - Ejecutar en memoria sin artefactos persistidos.
- Consecuencias
  - Buenas: alta observabilidad del pipeline.
  - Malas: crecimiento de disco en output.
- Evaluación actual
  - Diseño consistente en RunOutputDir y runners.

### 12.5 Validación disciplinaria externa al modelo
- Contexto
  - Salida de visión puede incluir tipos no previstos.
- Decisión tomada
  - Validar con domain_rules.yaml y reportar unclassified/missing attributes.
- Alternativas descartadas
  - Aceptar salida de visión sin gate disciplinario.
- Consecuencias
  - Buenas: control de calidad explícito.
  - Malas: depende de mantenimiento de reglas YAML por disciplina.
- Evaluación actual
  - Etapa activa y funcional en runner principal.

## 13. Limitaciones Conocidas
- La suite de tests no ejecuta completa en el entorno verificado por faltantes de dependencias (numpy, ezdxf, win32com) y conflictos con tests legacy.
- Existen rutas hardcoded externas (particularmente en código legacy y configuraciones de ejemplo) que no son portables entre máquinas.
- El pipeline depende de APIs externas (APS/OpenAI) para etapas críticas; degradaciones están implementadas, pero no sustituyen completamente la extracción DWG.
- En runners, múltiples parámetros están hardcoded en sección CONFIG y requieren edición manual para nuevos proyectos.
- El volumen de artefactos generados por corrida es alto (imágenes renderizadas, JSON intermedios, logs).
- No pude verificar ejecución E2E real contra activos DWG/PDF del proyecto GEBSA porque las rutas locales configuradas en runner apuntan a ubicaciones fuera del repositorio.

## 14. Mapa de Dependencias entre Módulos
(Quién depende de quién — como grafo en texto)

```text
dupla_run_gebsa.py
  -> aps_integration.aps_auth
  -> aps_integration.oss_manager
  -> aps_integration.model_derivative
  -> processors.json_processor
  -> agents.vision_agent
  -> disciplines.domain_rules
  -> disciplines.domain_validator
  -> processors.bc3_parser
  -> knowledge.bc3_embeddings
  -> knowledge.training_data
  -> knowledge.methodology_generator
  -> core.output_structure
  -> core.pipeline
  -> budget.export_excel
  -> budget.export_bc3

core.pipeline
  -> core.inventory_builder
  -> core.semantic_enrichment
  -> core.quality_engine
  -> core.semantic_adapter
  -> agents.quantifier_agent
  -> rules_engine
  -> agents.classifier_agent
  -> agents.partida_generator
  -> agents.partida_adapter
  -> budget.composer
  -> pricing.construcosto_loader
  -> processors.bc3_parser
  -> processors.json_processor

budget.composer
  -> budget.chapter_rules
  -> validation.discipline_inference
  -> pricing.construcosto_loader

agents.classifier_agent
  -> knowledge.bc3_embeddings
  -> knowledge.pres_expansion
  -> knowledge.training_data

disciplines.*
  -> disciplines.base
  -> rules_engine
  -> core.schemas
```

## 15. Glosario
- BC3:
  - Formato de intercambio de presupuestos de construcción (FIEBDC).
- FIEBDC-3:
  - Estándar de codificación/intercambio para conceptos y descomposición de presupuesto.
- Presto:
  - Software de presupuesto y mediciones compatible con BC3.
- Partida:
  - Línea presupuestaria (concepto de obra) con unidad, cantidad y precio.
- Capítulo:
  - Agrupación jerárquica de partidas en el presupuesto.
- Takeoff:
  - Medición/cuantiﬁcación derivada del inventario técnico.
- APU:
  - Análisis de precios unitarios (descomposición de recursos y costos).
- CAD facts:
  - Datos normalizados extraídos de DWG vía APS (capas, textos, blocks, geometría).
- LevelInventory:
  - Estructura unificada de inventario por nivel/planta.
- QuantityTrace:
  - Trazabilidad de una cantidad (evidencia, pasos, metadata, supuestos).
- Semantic layer:
  - Capa de enriquecimiento y validación semántica previa a cuantificación final.
- APS:
  - Autodesk Platform Services.
- Model Derivative:
  - Servicio APS para traducir y extraer metadata/propiedades de modelos.
- OSS (APS):
  - Object Storage Service de Autodesk.
- ITBIS:
  - Impuesto dominicano sobre bienes y servicios (aparece en datasets de costos).

