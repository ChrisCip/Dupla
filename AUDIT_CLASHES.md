# Auditoria tecnica de clashes/coordinacion

Repositorio auditado: `/Users/samuelfernandez/Dupla`  
Fecha: 2026-05-14  
Comando principal de tests: `python -m pytest coordination/tests/ -v --tb=short`

## 1. Resumen ejecutivo

El refactor estructural esta mayormente aplicado: el paquete activo de coordinacion vive en `coordination/`, `core/coordination/__init__.py` quedo como capa de re-export de compatibilidad y no quedan imports Python activos hacia `core.coordination.*` fuera de esa compatibilidad. Paso 1 (`nearby_text`) esta implementado e integrado en el runner y en el naming semantico, pero los tests no pudieron ejecutarse porque el entorno actual no tiene `shapely` instalado aunque `requirements.txt:9` lo declara. Paso 2 (`tile_renderer`) no fue encontrado, Paso 3 (`vision_validator`) no fue encontrado en `coordination/`, y Paso 4 (overlays anotados/HTML con imagenes) esta ausente salvo filtros de exclusion de overlays existentes. No encontre `coordination/reporting/tile_renderer.py`, ningun modulo `vision_validator`, ni HTML que incruste imagenes; `render_coordination_human_report_html()` genera HTML estatico a partir de Markdown en `coordination/reporting/reporting.py:671`.

## 2. Inventario de archivos

LOC = lineas no vacias, excluyendo comentarios `#` en Python. Rutas relativas desde `/Users/samuelfernandez/Dupla`; la ruta absoluta se obtiene anteponiendo ese root.

### `coordination/core/`

| Archivo | LOC | Ubicacion | Estado | Evidencia |
|---|---:|---|---|---|
| `coordination/core/__init__.py` | 0 | `coordination/` activo | huerfano/vacio | archivo vacio; paquete importable por estructura |
| `coordination/core/clash.py` | 238 | `coordination/` activo | activo | modelos y motor en `coordination/core/clash.py:18`, `coordination/core/clash.py:94`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:25` |
| `coordination/core/clash_element_mapper.py` | 390 | `coordination/` activo | activo | mapper en `coordination/core/clash_element_mapper.py:17`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:26` |
| `coordination/core/models_25d.py` | 118 | `coordination/` activo | activo | `Element25D` en `coordination/core/models_25d.py:87`; importado por casi todos los extractores |
| `coordination/core/nasas_paths.py` | 122 | `coordination/` activo | activo | helpers NASAS en `coordination/core/nasas_paths.py:21`, `coordination/core/nasas_paths.py:111`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:28` |
| `coordination/core/registry.py` | 81 | `coordination/` activo | activo | registry en `coordination/core/registry.py:35`, document en `coordination/core/registry.py:82`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:34` |
| `coordination/core/units.py` | 22 | `coordination/` activo | activo | conversiones en `coordination/core/units.py:10`, `coordination/core/units.py:21`; re-export en `coordination/__init__.py:29` |

### `coordination/extraction/`

| Archivo | LOC | Ubicacion | Estado | Evidencia |
|---|---:|---|---|---|
| `coordination/extraction/__init__.py` | 0 | `coordination/` activo | huerfano/vacio | paquete vacio |
| `coordination/extraction/aps_cache.py` | 29 | `coordination/` activo | activo | cache helpers en `coordination/extraction/aps_cache.py:11`; usado por APS en `coordination/extraction/from_dwg_aps.py:10` |
| `coordination/extraction/from_aps_viewer_dump.py` | 129 | `coordination/` activo | activo | `elements_from_viewer_dump()` en `coordination/extraction/from_aps_viewer_dump.py:17`; usado por APS en `coordination/extraction/from_dwg_aps.py:11` |
| `coordination/extraction/from_autodesk_properties.py` | 270 | `coordination/` activo | activo | picks Autodesk en `coordination/extraction/from_autodesk_properties.py:24`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:35` |
| `coordination/extraction/from_dwg_accore.py` | 633 | `coordination/` activo | activo | Accore extractor en `coordination/extraction/from_dwg_accore.py:58`, parser payload en `coordination/extraction/from_dwg_accore.py:339`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:36` |
| `coordination/extraction/from_dwg_aps.py` | 166 | `coordination/` activo | activo | APS extractor en `coordination/extraction/from_dwg_aps.py:21`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:42` |
| `coordination/extraction/from_dwg_com.py` | 279 | `coordination/` activo | activo/fallback | COM fallback en `coordination/extraction/from_dwg_com.py:229`; importado por Accore y runner en `coordination/extraction/from_dwg_accore.py:16`, `coordination/scripts/run_nasas09_project_coordination.py:43` |
| `coordination/extraction/from_dwg_ezdxf.py` | 141 | `coordination/` activo | activo/fallback DXF | `extract_elements_from_dwg()` en `coordination/extraction/from_dwg_ezdxf.py:69`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:44` |
| `coordination/extraction/from_pdf_vector.py` | 228 | `coordination/` activo | activo | `extract_elements_from_pdf()` en `coordination/extraction/from_pdf_vector.py:24`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:45` |
| `coordination/extraction/from_raster_image.py` | 188 | `coordination/` activo | activo opcional | `extract_elements_from_image()` en `coordination/extraction/from_raster_image.py:21`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:46` |

### `coordination/selection/`

| Archivo | LOC | Ubicacion | Estado | Evidencia |
|---|---:|---|---|---|
| `coordination/selection/__init__.py` | 0 | `coordination/` activo | huerfano/vacio | paquete vacio |
| `coordination/selection/coordinate_audit.py` | 428 | `coordination/` activo | activo | `SourceAudit` y schedule en `coordination/selection/coordinate_audit.py:18`, `coordination/selection/coordinate_audit.py:215`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:55` |
| `coordination/selection/fast_compare.py` | 938 | `coordination/` activo | activo | perfil `fast_compare` en `coordination/selection/fast_compare.py:17`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:62` |
| `coordination/selection/level_inference.py` | 72 | `coordination/` activo | activo | inferencia de nivel en `coordination/selection/level_inference.py:19`, `coordination/selection/level_inference.py:61`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:80` |
| `coordination/selection/source_selection.py` | 103 | `coordination/` activo | activo | seleccion de medios en `coordination/selection/source_selection.py:42`, `coordination/selection/source_selection.py:85`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:81` |

### `coordination/semantic/`

| Archivo | LOC | Ubicacion | Estado | Evidencia |
|---|---:|---|---|---|
| `coordination/semantic/__init__.py` | 0 | `coordination/` activo | huerfano/vacio | paquete vacio |
| `coordination/semantic/nearby_text.py` | 208 | `coordination/` activo | activo | `CadText` y funciones en `coordination/semantic/nearby_text.py:20`, `coordination/semantic/nearby_text.py:31`, `coordination/semantic/nearby_text.py:95`, `coordination/semantic/nearby_text.py:100`, `coordination/semantic/nearby_text.py:158`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:86` |
| `coordination/semantic/semantic_elements.py` | 352 | `coordination/` activo | activo | `SemanticElement25D` en `coordination/semantic/semantic_elements.py:70`; naming con `nearby_texts` en `coordination/semantic/semantic_elements.py:126`, `coordination/semantic/semantic_elements.py:321` |

### `coordination/reporting/`

| Archivo | LOC | Ubicacion | Estado | Evidencia |
|---|---:|---|---|---|
| `coordination/reporting/__init__.py` | 0 | `coordination/` activo | huerfano/vacio | paquete vacio |
| `coordination/reporting/reporting.py` | 1038 | `coordination/` activo | activo | contexto y reportes en `coordination/reporting/reporting.py:12`, `coordination/reporting/reporting.py:169`, `coordination/reporting/reporting.py:516`, `coordination/reporting/reporting.py:671`; importado por runner en `coordination/scripts/run_nasas09_project_coordination.py:47` |
| `coordination/reporting/tile_renderer.py` | n/a | `coordination/` esperado | no encontrado | `find coordination -name '*tile*'` no devolvio archivos |

### `coordination/scripts/`

| Archivo | LOC | Ubicacion | Estado | Evidencia |
|---|---:|---|---|---|
| `coordination/scripts/__init__.py` | 0 | `coordination/` activo | huerfano/vacio | paquete vacio |
| `coordination/scripts/demo_coordination_nasas.py` | 91 | `coordination/` activo | entrypoint CLI | `main()` en `coordination/scripts/demo_coordination_nasas.py:38` |
| `coordination/scripts/render_coordination_delivery_pack.py` | 297 | `coordination/` activo | entrypoint CLI | `main()` en `coordination/scripts/render_coordination_delivery_pack.py:17` |
| `coordination/scripts/render_coordination_portfolio_pack.py` | 273 | `coordination/` activo | entrypoint CLI | `main()` en `coordination/scripts/render_coordination_portfolio_pack.py:17` |
| `coordination/scripts/render_coordination_report.py` | 100 | `coordination/` activo | entrypoint CLI | `main()` en `coordination/scripts/render_coordination_report.py:24` |
| `coordination/scripts/run_nasas09_project_coordination.py` | 1728 | `coordination/` activo | runner principal | `main()` en `coordination/scripts/run_nasas09_project_coordination.py:106`; integra extractores, audit, clash, semantic mapping |
| `coordination/scripts/run_nasas_coordination_autodesk_raw.py` | 82 | `coordination/` activo | entrypoint CLI | `main()` en `coordination/scripts/run_nasas_coordination_autodesk_raw.py:52` |

### `coordination/tests/`

| Archivo | LOC | Ubicacion | Estado | Evidencia |
|---|---:|---|---|---|
| `coordination/tests/test_aps_viewer_dump.py` | 39 | `coordination/` tests | activo | importa extractor en `coordination/tests/test_aps_viewer_dump.py:3` |
| `coordination/tests/test_clash_element_mapper.py` | 170 | `coordination/` tests | activo | importa mapper en `coordination/tests/test_clash_element_mapper.py:3` |
| `coordination/tests/test_coordinate_audit.py` | 207 | `coordination/` tests | activo | importa audit en `coordination/tests/test_coordinate_audit.py:5` |
| `coordination/tests/test_coordination.py` | 186 | `coordination/` tests | activo | importa API top-level en `coordination/tests/test_coordination.py:10` |
| `coordination/tests/test_coordination_reporting.py` | 269 | `coordination/` tests | activo | importa reporting en `coordination/tests/test_coordination_reporting.py:5` |
| `coordination/tests/test_coordination_reporting_semantic.py` | 126 | `coordination/` tests | activo | importa reporting semantico en `coordination/tests/test_coordination_reporting_semantic.py:5` |
| `coordination/tests/test_dwg_accore_parser.py` | 106 | `coordination/` tests | activo | importa Accore en `coordination/tests/test_dwg_accore_parser.py:3` |
| `coordination/tests/test_dwg_com_extractor.py` | 23 | `coordination/` tests | activo | importa COM helpers en `coordination/tests/test_dwg_com_extractor.py:1` |
| `coordination/tests/test_dxf_support.py` | 21 | `coordination/` tests | activo | importa ezdxf extractor en `coordination/tests/test_dxf_support.py:7` |
| `coordination/tests/test_fast_compare.py` | 457 | `coordination/` tests | activo | importa runner y fast_compare en `coordination/tests/test_fast_compare.py:7` |
| `coordination/tests/test_from_autodesk_properties.py` | 39 | `coordination/` tests | activo | importa Autodesk properties en `coordination/tests/test_from_autodesk_properties.py:5` |
| `coordination/tests/test_level_inference.py` | 52 | `coordination/` tests | activo | importa level inference en `coordination/tests/test_level_inference.py:3` |
| `coordination/tests/test_nearby_text.py` | 75 | `coordination/` tests | activo | importa `nearby_text` en `coordination/tests/test_nearby_text.py:4` |
| `coordination/tests/test_pdf_vector_extractor.py` | 38 | `coordination/` tests | activo | importa PDF extractor en `coordination/tests/test_pdf_vector_extractor.py:7` |
| `coordination/tests/test_semantic_elements.py` | 133 | `coordination/` tests | activo | importa semantic elements en `coordination/tests/test_semantic_elements.py:6` |
| `coordination/tests/test_serena_support.py` | 5 | `coordination/` tests | activo | importa NASAS paths en `coordination/tests/test_serena_support.py:1` |
| `coordination/tests/test_source_selection.py` | 46 | `coordination/` tests | activo | importa source selection en `coordination/tests/test_source_selection.py:5` |

### `coordination/docs/` y refactor log

| Archivo | LOC | Ubicacion | Estado | Evidencia |
|---|---:|---|---|---|
| `coordination/docs/GUIA_FLUJO_CLASHES.md` | 431 | `coordination/` docs | activo doc, referencias antiguas | documenta flujo; aun menciona rutas `core/coordination/...` en `coordination/docs/GUIA_FLUJO_CLASHES.md:39` |
| `coordination/docs/PLANTILLA_INFORME_COORDINACION.md` | 66 | `coordination/` docs | activo doc | plantilla de informe |
| `coordination/REFACTOR_LOG.md` | 150 | `coordination/` doc | activo doc | declara migracion y compatibilidad en `coordination/REFACTOR_LOG.md:187` |

### `core/coordination/` compatibilidad

| Archivo | LOC | Ubicacion | Estado | Evidencia |
|---|---:|---|---|---|
| `core/coordination/__init__.py` | 46 | `core/coordination/` | backward-compat | re-exporta desde `coordination.*` en `core/coordination/__init__.py:9` a `core/coordination/__init__.py:37` |

### Legacy y archivos sueltos relevantes

| Archivo | LOC | Ubicacion | Estado | Evidencia |
|---|---:|---|---|---|
| `_legacy/run_clash_detection.py` | 311 | `_legacy/` | legacy, no usado por runner | flujo COM + OpenAI/Vision legacy; usa imagenes y OpenAI en `_legacy/run_clash_detection.py:229` a `_legacy/run_clash_detection.py:253` |
| `_legacy/cad_automation/analysis.py` | 454 | `_legacy/` | legacy | `detect_clashes()` legacy en `_legacy/cad_automation/analysis.py:165`; no importado por `coordination/` |
| `_legacy/cad_automation/models.py` | 222 | `_legacy/` | legacy | modelos `ClashSeverity`, `ClashResult` en `_legacy/cad_automation/models.py:1` y exports detectados |
| `_legacy/cad_automation/tests/test_analysis.py` | 108 | `_legacy/` tests | legacy tests | tests legacy de clashes; no pertenecen a paquete activo |
| `DIAGNOSTICO.md` | 230 | raiz | doc diagnostico | menciona baseline y rutas antiguas, por ejemplo `nearby_text` ausente previo en `DIAGNOSTICO.md:125` |
| `SRS.md` | 853 | raiz | doc general, no activo | usa `conflict_notes`, no implementa clashes |

## 3. Descripcion por archivo

### Core

- `coordination/core/clash.py`: motor 2.5D de hard clashes por interseccion de planta y solape Z. Exporta `ClashConflict`, `ClashIncident`, `clash_pairs()`, `group_conflicts_into_incidents()` y `conflicts_to_conflict_notes()` en `coordination/core/clash.py:18`, `coordination/core/clash.py:50`, `coordination/core/clash.py:94`, `coordination/core/clash.py:197`. Lo llama el runner en `coordination/scripts/run_nasas09_project_coordination.py:25` y llama a `models_25d`/`registry` en `coordination/core/clash.py:14`.
- `coordination/core/models_25d.py`: contratos Pydantic 2.5D para disciplinas, niveles, intervalos Z y elementos. Exporta `Discipline`, `ProjectLevel`, `ZInterval`, `Element25D`, `element_from_inventory_meters()` en `coordination/core/models_25d.py:13`, `coordination/core/models_25d.py:38`, `coordination/core/models_25d.py:50`, `coordination/core/models_25d.py:87`, `coordination/core/models_25d.py:131`. Lo llaman extractores, selection, semantic y tests; llama solo a `coordination.core.units` en `coordination/core/models_25d.py:10`.
- `coordination/core/clash_element_mapper.py`: conecta incidentes primarios con elementos semanticos por bbox, handles, layers y confianza. Exporta `map_primary_incidents_to_elements()` en `coordination/core/clash_element_mapper.py:17`; lo llama el runner en `coordination/scripts/run_nasas09_project_coordination.py:26` y llama `SemanticElement25D` en `coordination/core/clash_element_mapper.py:10`.
- `coordination/core/nasas_paths.py`: inferencia de disciplina/ruta NASAS, traduccion de huellas y clave documental/revision. Exporta `discipline_from_nasas_relative_path()`, `translate_footprint()`, `coordination_issue_key()` en `coordination/core/nasas_paths.py:21`, `coordination/core/nasas_paths.py:83`, `coordination/core/nasas_paths.py:111`. Lo llaman extractores y runner; llama `Discipline` en `coordination/core/nasas_paths.py:9`.
- `coordination/core/registry.py`: modelos de niveles y reglas de vistas/exclusion. Exporta `ProjectLevelRegistryDocument` y `ProjectLevelRegistry` en `coordination/core/registry.py:35`, `coordination/core/registry.py:82`; lo llama el runner en `coordination/scripts/run_nasas09_project_coordination.py:34` y extractores PDF/APS/raster; llama `models_25d` en `coordination/core/registry.py:10`.
- `coordination/core/units.py`: conversiones simples `to_mm()` y `from_mm()` en `coordination/core/units.py:10`, `coordination/core/units.py:21`. Lo llama `models_25d` y algunos extractores; no llama a modulos internos.

### Extraction

- `coordination/extraction/from_dwg_accore.py`: extractor principal DWG via AutoCAD Core Console y parser de payload Accore. Exporta `AccorePayloadResult`, `extract_elements_from_dwg_via_accore()`, `profile_accore_payload()`, `extract_elements_from_accore_payload()` en `coordination/extraction/from_dwg_accore.py:42`, `coordination/extraction/from_dwg_accore.py:58`, `coordination/extraction/from_dwg_accore.py:208`, `coordination/extraction/from_dwg_accore.py:339`; lo llama el runner en `coordination/scripts/run_nasas09_project_coordination.py:36` y llama `from_dwg_com`, `models_25d`, `nasas_paths` en `coordination/extraction/from_dwg_accore.py:16`.
- `coordination/extraction/from_dwg_com.py`: fallback AutoCAD COM con filtro de anotaciones y layers no geometricas. Exporta `extract_elements_from_dwg_via_com()` en `coordination/extraction/from_dwg_com.py:229`; lo llama Accore y runner. Depende opcionalmente de `win32com` y `pywintypes` en `coordination/extraction/from_dwg_com.py:18`.
- `coordination/extraction/from_dwg_ezdxf.py`: extractor DXF/local legible con `ezdxf`. Exporta `extract_elements_from_dwg()` en `coordination/extraction/from_dwg_ezdxf.py:69`; lo llama runner en `coordination/scripts/run_nasas09_project_coordination.py:44`; llama `models_25d` y `nasas_paths` en `coordination/extraction/from_dwg_ezdxf.py:14`.
- `coordination/extraction/from_dwg_aps.py`: pipeline APS que usa cache, viewer dump y propiedades Autodesk. Exporta `extract_elements_from_dwg_via_aps()` en `coordination/extraction/from_dwg_aps.py:21`; lo llama runner; llama `aps_cache`, `from_aps_viewer_dump`, `from_autodesk_properties`, `level_inference`, `registry` en `coordination/extraction/from_dwg_aps.py:10`.
- `coordination/extraction/from_aps_viewer_dump.py`: convierte primitives del viewer APS a poligonos/elementos. Exporta `elements_from_viewer_dump()` en `coordination/extraction/from_aps_viewer_dump.py:17`; lo llama `from_dwg_aps`; usa Shapely en `coordination/extraction/from_aps_viewer_dump.py:8`.
- `coordination/extraction/from_autodesk_properties.py`: transforma entidades Autodesk crudas en picks y elementos proxy. Exporta `AutodeskEntityPick`, `pick_best_entities()`, `picks_to_elements()`, `bulk_elements_from_autodesk_raw()` en `coordination/extraction/from_autodesk_properties.py:24`, `coordination/extraction/from_autodesk_properties.py:75`, `coordination/extraction/from_autodesk_properties.py:130`, `coordination/extraction/from_autodesk_properties.py:227`; lo llaman runner y APS.
- `coordination/extraction/from_pdf_vector.py`: extrae regiones vectoriales desde PDF con PyMuPDF. Exporta `extract_elements_from_pdf()` en `coordination/extraction/from_pdf_vector.py:24`; lo llama runner; llama `level_inference`, `models_25d`, `registry` en `coordination/extraction/from_pdf_vector.py:11`.
- `coordination/extraction/from_raster_image.py`: fallback de imagen/PDF raster como candidatos de baja confianza. Exporta `extract_elements_from_image()` en `coordination/extraction/from_raster_image.py:21`; lo llama runner cuando se incluyen imagenes en `coordination/scripts/run_nasas09_project_coordination.py:547`; llama `level_inference`, `models_25d`, `registry`.
- `coordination/extraction/aps_cache.py`: helpers de cache JSON por hash. Exporta `file_cache_key()`, `load_cached_json()`, `save_cached_json()` en `coordination/extraction/aps_cache.py:11`, `coordination/extraction/aps_cache.py:25`, `coordination/extraction/aps_cache.py:34`; usado por `from_dwg_aps`.

### Selection

- `coordination/selection/source_selection.py`: escanea medios de coordinacion y excluye imagenes derivadas/overlays. Exporta `collect_coordination_media()` y `should_include_source()` en `coordination/selection/source_selection.py:42`, `coordination/selection/source_selection.py:85`; lo llama runner en `coordination/scripts/run_nasas09_project_coordination.py:81`.
- `coordination/selection/level_inference.py`: resuelve nivel desde texto, pagina PDF o nombre de vista. Exporta `LevelResolution`, `infer_level_from_text()`, `infer_level_from_view_name()` en `coordination/selection/level_inference.py:13`, `coordination/selection/level_inference.py:19`, `coordination/selection/level_inference.py:61`; lo llaman extractores y runner.
- `coordination/selection/fast_compare.py`: seleccion documental, cohorts, readiness, scheduling y normalizacion de elementos. Exporta `SourceCandidate`, `PreMatchCandidate`, `compute_readiness_payload()`, `normalize_fast_compare_element()`, `primary_geometry_role()` en `coordination/selection/fast_compare.py:32`, `coordination/selection/fast_compare.py:46`, `coordination/selection/fast_compare.py:229`, `coordination/selection/fast_compare.py:511`, `coordination/selection/fast_compare.py:657`; lo llama runner en `coordination/scripts/run_nasas09_project_coordination.py:62`.
- `coordination/selection/coordinate_audit.py`: audita fuentes, bandas de coordenadas y agenda pares. Exporta `SourceAudit`, `PairScheduleItem`, `build_source_audit()`, `build_pair_schedule()` en `coordination/selection/coordinate_audit.py:18`, `coordination/selection/coordinate_audit.py:46`, `coordination/selection/coordinate_audit.py:64`, `coordination/selection/coordinate_audit.py:215`; lo llama runner en `coordination/scripts/run_nasas09_project_coordination.py:55`.

### Semantic

- `coordination/semantic/nearby_text.py`: extrae textos CAD DBText/MText del payload Accore, crea indice espacial y adjunta textos cercanos a elementos. Exporta `CadText`, `extract_texts_from_accore_payload()`, `build_text_index()`, `find_nearby_texts()`, `enrich_elements_with_nearby_text()` en `coordination/semantic/nearby_text.py:20`, `coordination/semantic/nearby_text.py:31`, `coordination/semantic/nearby_text.py:95`, `coordination/semantic/nearby_text.py:100`, `coordination/semantic/nearby_text.py:158`; lo llama runner en `coordination/scripts/run_nasas09_project_coordination.py:86`.
- `coordination/semantic/semantic_elements.py`: wrapper conservador para elementos semanticos y export por DWG. Exporta `SemanticElement25D`, `build_semantic_elements_from_accore_payload()`, `export_elements_by_dwg_json()` en `coordination/semantic/semantic_elements.py:70`, `coordination/semantic/semantic_elements.py:99`, `coordination/semantic/semantic_elements.py:169`; lo llama runner y `clash_element_mapper`; llama reglas de dominio y `Element25D` en `coordination/semantic/semantic_elements.py:19`.

### Reporting

- `coordination/reporting/reporting.py`: genera contexto, Markdown tecnico, reporte humano Markdown/HTML, severidad, accion recomendada y secciones para bot. Exporta `build_coordination_report_context()`, `render_coordination_report_markdown()`, `render_coordination_human_report_markdown()`, `render_coordination_human_report_html()` en `coordination/reporting/reporting.py:12`, `coordination/reporting/reporting.py:169`, `coordination/reporting/reporting.py:516`, `coordination/reporting/reporting.py:671`; lo llama runner en `coordination/scripts/run_nasas09_project_coordination.py:47`.

### Scripts

- `coordination/scripts/run_nasas09_project_coordination.py`: runner principal NASAS, orquesta seleccion, extraccion, `nearby_text`, clash, semantic mapping y reportes. Importa todos los modulos principales en `coordination/scripts/run_nasas09_project_coordination.py:25` a `coordination/scripts/run_nasas09_project_coordination.py:90`; llama enriquecimiento `nearby_text` en `coordination/scripts/run_nasas09_project_coordination.py:970`.
- `coordination/scripts/render_coordination_report.py`: entrypoint para renderizar reportes desde JSON existentes. Importa `ClashIncident`, `coordinate_audit` y `reporting` en `coordination/scripts/render_coordination_report.py:15` a `coordination/scripts/render_coordination_report.py:17`.
- `coordination/scripts/run_nasas_coordination_autodesk_raw.py`: entrypoint antiguo/auxiliar sobre Autodesk raw. Importa `clash_pairs`, `conflicts_to_conflict_notes` y extractores Autodesk en `coordination/scripts/run_nasas_coordination_autodesk_raw.py:26`.
- `coordination/scripts/demo_coordination_nasas.py`: demo CLI sobre datos NASAS. Importa API top-level en `coordination/scripts/demo_coordination_nasas.py:25`.
- `coordination/scripts/render_coordination_delivery_pack.py` y `render_coordination_portfolio_pack.py`: empaquetan entregables y portafolio de corridas; `main()` en `coordination/scripts/render_coordination_delivery_pack.py:17`, `coordination/scripts/render_coordination_portfolio_pack.py:17`.

### Compat y legacy

- `core/coordination/__init__.py`: unico archivo real bajo `core/coordination/`; re-exporta core, extraction, selection, semantic y reporting desde `coordination.*` en `core/coordination/__init__.py:9` a `core/coordination/__init__.py:37`. No tiene callers Python encontrados; estado backward-compat.
- `_legacy/run_clash_detection.py`: flujo legacy COM + Vision/OpenAI para detectar conflictos visuales sobre imagenes renderizadas. No lo llama el runner activo; usa carga de imagen y mensaje multimodal en `_legacy/run_clash_detection.py:229` a `_legacy/run_clash_detection.py:253`.
- `_legacy/cad_automation/analysis.py`: motor legacy de areas y clashes por bounding boxes. Exporta `detect_clashes()` en `_legacy/cad_automation/analysis.py:165`; no lo llama `coordination/`.
- `_legacy/cad_automation/models.py`: modelos legacy de CAD y `ClashResult`/`ClashSeverity`; no usados por paquete activo.

## 4. Estado del refactor

- ✅ Todo el codigo fuente activo de coordinacion encontrado vive en `coordination/`; bajo `core/coordination/` solo queda `__init__.py` y `__pycache__` (`core/coordination/__init__.py:1`).
- ✅ `core/coordination/__init__.py` tiene re-exports backward-compatible desde `coordination.*` (`core/coordination/__init__.py:9` a `core/coordination/__init__.py:37`).
- ✅ Scripts de coordinacion estan en `coordination/scripts/` (`coordination/scripts/run_nasas09_project_coordination.py:1`, `coordination/scripts/render_coordination_report.py:1`). No encontre runner activo equivalente suelto en `scripts/`.
- ✅ Tests de coordinacion estan en `coordination/tests/`; hay 17 archivos `test_*.py` y 69 funciones test por AST.
- ⚠️ Docs de coordinacion estan en `coordination/docs/`, pero contienen referencias antiguas a `core/coordination/...`, por ejemplo `coordination/docs/GUIA_FLUJO_CLASHES.md:39`.
- ✅ No encontre duplicados fuente old/new bajo `core/coordination/`; solo existe `core/coordination/__init__.py`.
- ✅ No encontre imports rotos `from core.coordination` o `import core.coordination` en archivos Python. La busqueda solo devolvio menciones documentales en `coordination/REFACTOR_LOG.md:187` y `coordination/REFACTOR_LOG.md:191`.

## 5. Estado de los 4 pasos nuevos

### Paso 1 - `nearby_text`: ✅ implementado, integrado; tests bloqueados por entorno

- Existe `coordination/semantic/nearby_text.py`.
- Contiene `CadText` (`coordination/semantic/nearby_text.py:20`), `extract_texts_from_accore_payload()` (`coordination/semantic/nearby_text.py:31`), `build_text_index()` (`coordination/semantic/nearby_text.py:95`), `find_nearby_texts()` (`coordination/semantic/nearby_text.py:100`) y `enrich_elements_with_nearby_text()` (`coordination/semantic/nearby_text.py:158`).
- Integracion runner: importa `enrich_elements_with_nearby_text` y `extract_texts_from_accore_payload` en `coordination/scripts/run_nasas09_project_coordination.py:86` a `coordination/scripts/run_nasas09_project_coordination.py:89`. Lo llama despues de normalizar elementos en `coordination/scripts/run_nasas09_project_coordination.py:970`; extrae textos y enriquece en `coordination/scripts/run_nasas09_project_coordination.py:1015` a `coordination/scripts/run_nasas09_project_coordination.py:1022`.
- Integracion naming: `build_semantic_elements_from_accore_payload()` pasa `nearby_texts` a `_resolve_publishable_name()` en `coordination/semantic/semantic_elements.py:126` a `coordination/semantic/semantic_elements.py:130`; `_resolve_publishable_name()` usa `_publishable_name_from_nearby_texts()` en `coordination/semantic/semantic_elements.py:321` a `coordination/semantic/semantic_elements.py:333`.
- Tests: `coordination/tests/test_nearby_text.py` existe y declara 8 tests. La ejecucion `python -m pytest coordination/tests/test_nearby_text.py -v --tb=short` fallo en collection por `ModuleNotFoundError: No module named 'shapely'` al importar `coordination/core/clash.py:10`.

### Paso 2 - `tile_renderer`: ❌ ausente

- `coordination/reporting/tile_renderer.py`: no encontrado.
- No encontre `TileSpec`, `RenderedTile`, `render_tile_svg()`, `render_incident_tile()` ni `render_all_incident_tiles()` en `coordination/`.
- No hay import de `tile_renderer` en el runner; los imports iniciales terminan en `nearby_text` y `coordination` top-level (`coordination/scripts/run_nasas09_project_coordination.py:86` a `coordination/scripts/run_nasas09_project_coordination.py:90`).
- `reporting.py` no referencia tiles ni imagenes. El HTML se arma con tags `h1`, `h2`, `p`, `pre` en `coordination/reporting/reporting.py:677` a `coordination/reporting/reporting.py:699`.
- No hay tests `test_tile_renderer.py`.

### Paso 3 - `vision_validator`: ❌ ausente en `coordination/`

- No existe modulo de validacion visual bajo `coordination/`.
- No hay import de `vision_validator` ni de `agents.vision_agent` en el runner. Los imports del runner estan en `coordination/scripts/run_nasas09_project_coordination.py:25` a `coordination/scripts/run_nasas09_project_coordination.py:90`.
- Existe Vision general en `agents/vision_agent.py`, con prompt orientado a inventario/cuantiﬁcacion, no a clashes; `analyze_plan()` esta en `agents/vision_agent.py:1067`. No encontre reutilizacion por coordinacion.
- Existe flujo legacy visual en `_legacy/run_clash_detection.py`, pero no esta migrado ni importado por el runner activo.
- No hay tests de `vision_validator`.

### Paso 4 - overlays anotados: ❌ ausente

- No existe funcionalidad separada de overlays anotados en `coordination/`; `find coordination -name '*overlay*'` no devolvio fuente.
- Los filtros de fuente excluyen overlays existentes por patron, no los generan: `coordination/selection/source_selection.py:18` incluye `overlay`, y el test lo valida en `coordination/tests/test_source_selection.py:19`.
- No hay tiles con zona de interseccion roja, labels de texto, leyenda ni barra de escala porque no existe `tile_renderer.py`.
- El reporte HTML no incrusta imagenes: `render_coordination_human_report_html()` solo transforma Markdown a texto escapado en `coordination/reporting/reporting.py:677` a `coordination/reporting/reporting.py:699`.

## 6. Estado de modulos existentes

### Modelos de datos

- `models_25d.py`: `Element25D` no tiene campo tipado `nearby_texts`; conserva solo `metadata: dict[str, Any]` en `coordination/core/models_25d.py:101`. `nearby_texts` se adjunta dinamicamente en `element.metadata["nearby_texts"]` desde `coordination/semantic/nearby_text.py:169` y `coordination/semantic/nearby_text.py:174`.
- `clash.py`: `ClashConflict` incluye campos geometricos/traceability como `plan_intersection_bounds_mm`, `geometry_sources` y `level_assignment_sources` (`coordination/core/clash.py:31` a `coordination/core/clash.py:38`). `ClashIncident` incluye `plan_centroid_mm`, `plan_bounds_mm`, `geometry_sources` (`coordination/core/clash.py:61` a `coordination/core/clash.py:65`). No tiene `tile_path`, `vision_evidence`, lifecycle, assignee ni status.
- `semantic_elements.py`: `SemanticElement25D` no tiene campos top-level `vision_evidence`, `nearby_texts` ni `tile_path`; tiene `metadata` generico en `coordination/semantic/semantic_elements.py:96`, y guarda `nearby_texts` dentro de metadata en `coordination/semantic/semantic_elements.py:157` a `coordination/semantic/semantic_elements.py:161`.

### Extractores

- `from_dwg_accore.py`: `ANNOTATION_TYPES` sigue incluyendo `DBTEXT`, `MTEXT`, `MText`, `Dimension`, `Leader`, `MLeader`, `Point` en `coordination/extraction/from_dwg_accore.py:28` a `coordination/extraction/from_dwg_accore.py:36`.
- El `continue` que salta textos/anotaciones sigue presente en `extract_elements_from_accore_payload()` en `coordination/extraction/from_dwg_accore.py:361` a `coordination/extraction/from_dwg_accore.py:362`. La extraccion de textos se implemento separada en `nearby_text.py`, no como `Element25D`.

### Reporting

- `reporting.py`: no incluye tiles/imagenes. `render_coordination_human_report_markdown()` empieza en `coordination/reporting/reporting.py:516`; `render_coordination_human_report_html()` empieza en `coordination/reporting/reporting.py:671` y no genera `<img>`.
- Las funciones de reporte si fueron ampliadas para semantic mapping textual: `_report_evidence_text()` usa nombre/tipo publicable en `coordination/reporting/reporting.py:729`, y `_exact_entity_text()` aparece en `coordination/reporting/reporting.py:745`.

### Runner

Imports iniciales relevantes en `coordination/scripts/run_nasas09_project_coordination.py`:

- stdlib y dotenv: `argparse`, `json`, `logging`, `os`, `sys`, `Counter`, `defaultdict`, `ThreadPoolExecutor`, `datetime`, `Path`, `perf_counter`, `SimpleNamespace`, `Iterable`, `load_dotenv` en `coordination/scripts/run_nasas09_project_coordination.py:6` a `coordination/scripts/run_nasas09_project_coordination.py:19`.
- core: `ClashConflict`, `group_conflicts_into_incidents`, `map_primary_incidents_to_elements`, `Element25D`, `nasas_paths`, `ProjectLevelRegistryDocument` en `coordination/scripts/run_nasas09_project_coordination.py:25` a `coordination/scripts/run_nasas09_project_coordination.py:34`.
- extraction: Autodesk, Accore, APS, COM, ezdxf, PDF vector, raster en `coordination/scripts/run_nasas09_project_coordination.py:35` a `coordination/scripts/run_nasas09_project_coordination.py:46`.
- reporting: `build_analysis_bot_context`, `build_coordination_report_context`, human/technical renderers en `coordination/scripts/run_nasas09_project_coordination.py:47` a `coordination/scripts/run_nasas09_project_coordination.py:54`.
- selection: coordinate audit, fast_compare, level/source selection en `coordination/scripts/run_nasas09_project_coordination.py:55` a `coordination/scripts/run_nasas09_project_coordination.py:81`.
- semantic: `build_semantic_elements_from_accore_payload`, `export_elements_by_dwg_json`, `nearby_text` en `coordination/scripts/run_nasas09_project_coordination.py:82` a `coordination/scripts/run_nasas09_project_coordination.py:89`.
- no hay imports de `tile_renderer` ni `vision_validator`.

Llamadas principales:

- `nearby_text`: llamada a `_enrich_fast_compare_elements_with_nearby_text()` en `coordination/scripts/run_nasas09_project_coordination.py:970`; extraccion/enriquecimiento en `coordination/scripts/run_nasas09_project_coordination.py:1015` a `coordination/scripts/run_nasas09_project_coordination.py:1022`.
- semantic mapping: `_build_semantic_mapping_payloads()` se llama si `--enable-semantic-mapping` en `coordination/scripts/run_nasas09_project_coordination.py:1490` a `coordination/scripts/run_nasas09_project_coordination.py:1503`.
- clash: `_build_fast_compare_primary_conflicts()` y `group_conflicts_into_incidents()` en `coordination/scripts/run_nasas09_project_coordination.py:1386` a `coordination/scripts/run_nasas09_project_coordination.py:1393`.

## 7. Resultados de tests

Archivos de tests encontrados en `coordination/tests/`: 17. Funciones test por AST: 69.

Resumen por archivo:

| Archivo | Tests |
|---|---:|
| `coordination/tests/test_aps_viewer_dump.py` | 1 |
| `coordination/tests/test_clash_element_mapper.py` | 4 |
| `coordination/tests/test_coordinate_audit.py` | 6 |
| `coordination/tests/test_coordination.py` | 11 |
| `coordination/tests/test_coordination_reporting.py` | 4 |
| `coordination/tests/test_coordination_reporting_semantic.py` | 2 |
| `coordination/tests/test_dwg_accore_parser.py` | 2 |
| `coordination/tests/test_dwg_com_extractor.py` | 2 |
| `coordination/tests/test_dxf_support.py` | 1 |
| `coordination/tests/test_fast_compare.py` | 12 |
| `coordination/tests/test_from_autodesk_properties.py` | 2 |
| `coordination/tests/test_level_inference.py` | 3 |
| `coordination/tests/test_nearby_text.py` | 8 |
| `coordination/tests/test_pdf_vector_extractor.py` | 2 |
| `coordination/tests/test_semantic_elements.py` | 4 |
| `coordination/tests/test_serena_support.py` | 1 |
| `coordination/tests/test_source_selection.py` | 4 |

Resultado de `python -m pytest coordination/tests/ -v --tb=short`:

```text
collected 0 items / 17 errors
ERROR coordination/tests/test_aps_viewer_dump.py
...
ERROR coordination/tests/test_source_selection.py
E   ModuleNotFoundError: No module named 'shapely'
!!!!!!!!!!!!!!!!!!! Interrupted: 17 errors during collection !!!!!!!!!!!!!!!!!!!
============================== 17 errors in 0.54s ==============================
```

Error exacto recurrente:

```text
coordination/core/clash.py:10: in <module>
    from shapely.geometry import Polygon
E   ModuleNotFoundError: No module named 'shapely'
```

Resultado especifico `nearby_text`:

```text
collected 0 items / 1 error
ERROR coordination/tests/test_nearby_text.py
coordination/core/clash.py:10: in <module>
    from shapely.geometry import Polygon
E   ModuleNotFoundError: No module named 'shapely'
```

No hay tests de `tile_renderer` ni `vision_validator`.

## 8. Dependencias

Dependencias externas usadas por `coordination/`:

- `pydantic`: modelos core, registry, semantic y audit (`coordination/core/models_25d.py:8`, `coordination/core/registry.py:8`, `coordination/semantic/semantic_elements.py:17`, `coordination/selection/coordinate_audit.py:10`). Declarada en `requirements.txt:8`.
- `shapely`: motor clash, nearby_text STRtree y extractores geometricos (`coordination/core/clash.py:10`, `coordination/semantic/nearby_text.py:11`, `coordination/extraction/from_dwg_accore.py:14`). Declarada en `requirements.txt:9`, pero no instalada en el entorno usado por pytest.
- `ezdxf`: extractor DXF y tests (`coordination/extraction/from_dwg_ezdxf.py:10`, `coordination/tests/test_dxf_support.py:5`). Declarada en `requirements.txt:10`.
- `PyMuPDF`/`fitz`: PDF vector/raster y tests (`coordination/extraction/from_pdf_vector.py:9`, `coordination/extraction/from_raster_image.py:9`). Declarada en `requirements-legacy.txt:4`, no en `requirements.txt`.
- `python-dotenv`: runner principal (`coordination/scripts/run_nasas09_project_coordination.py:19`). Declarada en `requirements.txt:2`.
- `aps_integration`: integracion local APS (`coordination/extraction/from_dwg_aps.py:1` y imports internos).
- `win32com`, `pywintypes`: COM fallback Windows (`coordination/extraction/from_dwg_com.py:18`, `coordination/extraction/from_dwg_com.py:26`). No son portables en macOS y no estan en `requirements.txt`.

No encontre nuevas dependencias como `matplotlib`, `PIL/Pillow` o `svgwrite` usadas por `coordination/`. El runner silencia logger de `matplotlib` en `coordination/scripts/run_nasas09_project_coordination.py:243`, pero no lo importa. El bloqueo actual de imports es `shapely` faltante.

## 9. Mapa de imports

```text
runner
  -> coordination.core.clash
      -> coordination.core.models_25d
      -> coordination.core.registry
  -> coordination.core.clash_element_mapper
      -> coordination.semantic.semantic_elements
          -> coordination.core.models_25d
  -> coordination.extraction.from_dwg_accore
      -> coordination.extraction.from_dwg_com
      -> coordination.core.models_25d
      -> coordination.core.nasas_paths
  -> coordination.extraction.from_dwg_aps
      -> coordination.extraction.aps_cache
      -> coordination.extraction.from_aps_viewer_dump
      -> coordination.extraction.from_autodesk_properties
      -> coordination.selection.level_inference
      -> coordination.core.registry
  -> coordination.extraction.from_dwg_com
      -> coordination.core.models_25d
      -> coordination.core.nasas_paths
  -> coordination.extraction.from_dwg_ezdxf
      -> coordination.core.models_25d
      -> coordination.core.nasas_paths
  -> coordination.extraction.from_pdf_vector
      -> coordination.selection.level_inference
      -> coordination.core.models_25d
      -> coordination.core.registry
  -> coordination.extraction.from_raster_image
      -> coordination.selection.level_inference
      -> coordination.core.models_25d
      -> coordination.core.registry
  -> coordination.selection.coordinate_audit
      -> coordination.selection.fast_compare
      -> coordination.core.models_25d
  -> coordination.selection.fast_compare
      -> coordination.selection.level_inference
      -> coordination.core.models_25d
      -> coordination.core.nasas_paths
      -> coordination.core.registry
      -> coordination.selection.source_selection
  -> coordination.semantic.nearby_text
      -> shapely.geometry / shapely.strtree
  -> coordination.reporting.reporting
```

Compat:

```text
core/coordination/__init__.py
  -> coordination.core.*
  -> coordination.extraction.*
  -> coordination.selection.*
  -> coordination.semantic.semantic_elements
  -> coordination.reporting.reporting
```

## 10. Tabla final de estado

| Componente | Estado | Archivo | Tests | Integrado en runner | Notas |
|---|---|---|---|---|---|
| Motor hard clash | ✅ | `coordination/core/clash.py` | bloqueados por `shapely` | si | hard clash por planta+Z; no soft real |
| Modelos 2.5D | ✅ | `coordination/core/models_25d.py` | bloqueados por `shapely` | si | `nearby_texts` solo en metadata |
| Accore extractor | ✅ | `coordination/extraction/from_dwg_accore.py` | bloqueados por `shapely` | si | sigue saltando textos como elementos |
| COM fallback | ✅ | `coordination/extraction/from_dwg_com.py` | bloqueados por `shapely` | si | dependencia Windows opcional |
| Fast compare | ✅ | `coordination/selection/fast_compare.py` | bloqueados por `shapely` | si | scheduling/readiness activo |
| Coordinate audit | ✅ | `coordination/selection/coordinate_audit.py` | bloqueados por `shapely` | si | genera audit y pair schedule |
| Semantic mapping | ✅ | `coordination/semantic/semantic_elements.py` | bloqueados por `shapely` | si, flag `--enable-semantic-mapping` | conserva nombres; usa nearby text |
| Paso 1 nearby_text | ✅ | `coordination/semantic/nearby_text.py` | no ejecuta por `shapely` | si | implementado e integrado |
| Paso 2 tile_renderer | ❌ | no encontrado | no hay | no | no hay SVG/tiles |
| Paso 3 vision_validator | ❌ | no encontrado | no hay | no | solo existe Vision general/legacy |
| Paso 4 overlays anotados | ❌ | no encontrado | no hay | no | HTML no incrusta imagenes |
| Reporting humano | ⚠️ | `coordination/reporting/reporting.py` | bloqueados por `shapely` | si | Markdown/HTML estatico sin imagenes |
| Backward compat | ✅ | `core/coordination/__init__.py` | n/a | n/a | re-exports completos; sin imports activos detectados |
| Docs | ⚠️ | `coordination/docs/*.md` | n/a | n/a | existen, pero `GUIA_FLUJO_CLASHES.md` conserva rutas antiguas |

## 11. Blockers y recomendaciones

1. Instalar dependencias del entorno antes de validar: `shapely` falta aunque esta en `requirements.txt:9`. Mientras falte, ningun test de `coordination/tests/` se colecciona.
2. Agregar `PyMuPDF`/`fitz` al requirements principal si los tests/extractores PDF son parte del flujo activo; hoy aparece en `requirements-legacy.txt:4` pero los modulos activos lo importan.
3. Implementar Paso 2 antes de Paso 4: crear `coordination/reporting/tile_renderer.py` con `TileSpec`, `RenderedTile`, render SVG por incidente y tests dedicados.
4. Integrar tiles en `reporting.py` y runner: el HTML actual no puede embeber evidencia visual porque solo escapa Markdown a texto.
5. Para Paso 3, crear un `vision_validator` propio de coordinacion con prompt de clashes; no reutilizar directamente el prompt de `agents/vision_agent.py` porque esta orientado a inventario/presupuesto.
6. Actualizar docs post-refactor: `coordination/docs/GUIA_FLUJO_CLASHES.md` todavia menciona `core/coordination/...` en varias filas.
7. Considerar campos top-level si se van a estabilizar artefactos: `SemanticElement25D.nearby_texts`, `vision_evidence`, `tile_path` y campos lifecycle en `ClashIncident` evitarian depender de `metadata` para pasos 3/4.
