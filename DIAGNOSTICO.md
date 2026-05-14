# Diagnostico tecnico del repositorio Dupla

## 1. Resumen ejecutivo

Dupla tiene dos flujos activos con capacidades semanticas desbalanceadas: el Flujo 1 renderiza planos a imagen, llama Vision y produce un `LevelInventory` rico en tipos constructivos, nombres, medidas, materiales, fuentes, evidencia y confianza; el Flujo 2, en cambio, extrae `Element25D` desde DWG/PDF/imagen y ejecuta `clash_pairs()` con huellas geometricas, Z, disciplina, layer, tipo CAD y metadata. El problema Serena 18 descrito por el usuario, 748 grupos semanticamente anonimos, 0 nombres candidato, `nearby_text=0`, 0 hallazgos defendibles y 1021 elementos suprimidos, encaja con la arquitectura actual: la geometria ya sirve para comparar, pero la coordinacion no usa Vision antes ni durante la deteccion, no conserva texto CAD como contexto espacial cercano, y su semantic mapping opcional ocurre despues del clash con reglas conservadoras basadas en tokens de layer/bloque. No encontre en el repo artefactos del run exacto `2026-05-10`; si la cifra 748/1021 viene de esa corrida externa, la uso como evidencia aportada por el usuario, no como dato reproducido localmente.

## 2. Brecha principal: vision semantica ausente en coordinacion

### Diagrama de flujo en texto

```text
Flujo 1 - Presupuesto
PDF/imagenes
  -> dupla_run_full_analysis_local.stage_resolve_pages()
  -> render_pdf_to_images()
  -> stage_vision_analysis()
  -> agents.vision_agent.run_full_vision_analysis()
  -> agents.vision_agent.analyze_plan()
  -> _simple_to_level_inventory()
  -> level_inventory_from_dict()
  -> core.pipeline.build_hybrid_inventory()
  -> core.inventory_builder.build_level_inventory()
  -> LevelInventory + takeoffs + budget

Flujo 2 - Coordinacion
DWG/PDF/imagenes multi-disciplina
  -> scripts/run_nasas09_project_coordination.py
  -> collect/select/profile/audit/schedule
  -> _extract_fast_compare_scheduled_elements()
  -> extract_elements_from_accore_payload()/COM/ezdxf/PDF/raster
  -> Element25D(id, discipline, category, footprint, z_data, metadata)
  -> _build_fast_compare_primary_conflicts()
  -> clash_pairs()
  -> group_conflicts_into_incidents()
  -> reportes
  -> opcional: --enable-semantic-mapping post-clash
```

La divergencia esta antes de `clash_pairs()`: el Flujo 1 entra por imagen + Vision y produce inventario semantico; el Flujo 2 entra por geometria 2.5D y no llama a Vision. El runner de coordinacion importa `clash_pairs`, extractores CAD/PDF/raster y `build_semantic_elements_from_accore_payload`, pero no importa `agents.vision_agent` ni `build_hybrid_inventory` (`scripts/run_nasas09_project_coordination.py:25`, `scripts/run_nasas09_project_coordination.py:61`, `scripts/run_nasas09_project_coordination.py:82`). La opcion `--enable-semantic-mapping` se declara como capa MVP posterior a `primary_incidents` (`scripts/run_nasas09_project_coordination.py:117`) y se ejecuta despues de escribir `primary_incidents.json` (`scripts/run_nasas09_project_coordination.py:1332`, `scripts/run_nasas09_project_coordination.py:1411`).

Punto natural de inyeccion: despues de `_extract_fast_compare_scheduled_elements()` y antes de `_build_fast_compare_primary_conflicts()` (`scripts/run_nasas09_project_coordination.py:1285`, `scripts/run_nasas09_project_coordination.py:1305`), porque ahi ya existe el set de archivos programados, elementos 2.5D, cohort/level y coordenadas. Un segundo punto natural, de menor riesgo, es post-clash: usar los `primary_incidents` y `plan_bounds_mm` para renderizar recortes/overlays y validar/nombrar con Vision antes del reporte humano.

## 3. Seccion 1 - Brecha de vision semantica entre Flujo 1 y Flujo 2

### Flujo 1 desde imagen hasta inventario semantico

- `dupla_run_full_analysis_local.py` orquesta el Flujo 1 en `main()` (`dupla_run_full_analysis_local.py:693`) y resuelve paginas con `stage_resolve_pages()` (`dupla_run_full_analysis_local.py:312`).
- Si la entrada es PDF, renderiza paginas a imagenes en `render_pdf_to_images()` dentro de `stage_resolve_pages()` (`dupla_run_full_analysis_local.py:321`, `dupla_run_full_analysis_local.py:357`).
- `stage_vision_analysis()` llama `run_full_vision_analysis()` para una o varias carpetas de paginas (`dupla_run_full_analysis_local.py:382`, `dupla_run_full_analysis_local.py:411`, `dupla_run_full_analysis_local.py:424`).
- `main()` ejecuta Vision como Stage 4 antes del presupuesto (`dupla_run_full_analysis_local.py:794`) y pasa sus resultados a Stage 5 `stage_build_budget()` (`dupla_run_full_analysis_local.py:816`, `dupla_run_full_analysis_local.py:820`).
- `run_full_vision_analysis()` itera imagenes y llama `analyze_plan()` (`agents/vision_agent.py:1144`, `agents/vision_agent.py:1156`, `agents/vision_agent.py:1161`).
- `analyze_plan()` arma un request Chat Completions con texto + `image_url` base64 en detalle alto (`agents/vision_agent.py:1083`, `agents/vision_agent.py:1100`, `agents/vision_agent.py:1103`) y luego adapta el JSON simple a `LevelInventory` (`agents/vision_agent.py:1125`, `agents/vision_agent.py:1129`).
- El schema `LevelInventory` contiene `walls`, `openings`, `doors`, `windows`, `wet_areas`, `kitchens`, `stairs`, `fixtures`, `structural_elements`, `cad_hints`, `source_refs`, `assumptions`, `conflict_notes` y `confidence` (`core/schemas.py:190`).

Campos semanticos por elemento en Flujo 1:
- Todos los `InventoryEntity` tienen `id`, `source`, `source_refs`, `assumptions`, `inputs`, `conflict_notes`, `confidence` y `evidence` (`core/schemas.py:48`).
- `Wall` agrega material, sistema, interior/exterior, espesor, altura, area, si es estructural y conteo de huecos (`core/schemas.py:64`).
- `Door` agrega `type_hint`, material, dimensiones, exterior y muro relacionado (`core/schemas.py:92`).
- `Window` agrega `type_hint`, glazing, dimensiones y muro relacionado (`core/schemas.py:104`).
- `StructuralElement` agrega `element_type`, material, seccion, luz, orientacion, armado, nivel anfitrion y adyacencias (`core/schemas.py:170`).

### Flujo 2 desde DWG hasta `clash_pairs()`

- El Flujo 2 perfila candidatos, audita coordenadas y agenda pares (`scripts/run_nasas09_project_coordination.py:1152`, `scripts/run_nasas09_project_coordination.py:1192`).
- Extrae los archivos programados en `_extract_fast_compare_scheduled_elements()` (`scripts/run_nasas09_project_coordination.py:835`) y para DWG reutiliza payload Accore ya perfilado (`scripts/run_nasas09_project_coordination.py:860`).
- Los DWG se convierten a `Element25D` con `extract_elements_from_accore_payload()` (`core/coordination/from_dwg_accore.py:339`). Cada elemento recibe `source_ref` con `archivo|layer|entity_type|handle`, `category=f"{entity_type}:{layer}"`, `footprint_coords_mm`, `ZInterval`, y metadata con `layer`, `handle`, `entity_type`, `block_name`, `geometry_source`, `geometry_quality`, `geometry_role`, `bbox_mm`, `centroid_mm`, `level_id` y `discipline` (`core/coordination/from_dwg_accore.py:397`, `core/coordination/from_dwg_accore.py:409`).
- La estructura de `Element25D` es minima: `id`, `source_ref`, `discipline`, `category`, `footprint_coords_mm`, `z_data`, `metadata` (`core/coordination/models_25d.py:87`).
- El motor primario agrupa por `cohort_id` y `file_level_id`, filtra `primary_geometry_role`, y llama `clash_pairs()` (`scripts/run_nasas09_project_coordination.py:1547`, `scripts/run_nasas09_project_coordination.py:1557`, `scripts/run_nasas09_project_coordination.py:1573`).

### Que le falta a cada `Element25D` para igualar la riqueza del Flujo 1

Le faltan campos tipados de negocio que hoy solo existen en `LevelInventory`: `element_type` constructivo confiable, `element_name` publicable, funcion/sistema, material, dimensiones de producto, zona/habitacion/eje, relacion con muro/host, evidencia visual/textual, confianza semantica, source refs cruzadas CAD+Vision, y notas de conflicto. En coordinacion existe `category` y `metadata`, pero no hay contrato fuerte para esos datos (`core/coordination/models_25d.py:95`, `core/coordination/models_25d.py:101`).

El MVP `SemanticElement25D` intenta cubrir parte de esto con `element_type`, `element_name`, `semantic_type_confidence`, `name_confidence` y `classification_signals` (`core/coordination/semantic_elements.py:69`), pero se construye despues de `primary_incidents`, no alimenta `clash_pairs()` (`scripts/run_nasas09_project_coordination.py:1411`).

### Render DWG a imagen en coordinacion

No encontre en el pipeline activo de coordinacion una fase que renderice DWG a imagen y los pase por `agents/vision_agent.py`. Los extractores activos son Accore/APS/COM/ezdxf/PDF/raster (`scripts/run_nasas09_project_coordination.py:459`, `scripts/run_nasas09_project_coordination.py:528`, `scripts/run_nasas09_project_coordination.py:542`). El render a imagen existe en Flujo 1 para PDF (`dupla_run_full_analysis_local.py:357`) y en outputs historicos, pero no esta conectado al Flujo 2. Buscado en todo el repo con `rg` sobre `vision_agent`, `run_full_vision_analysis`, `rendered_pages`, `enable-semantic-mapping` y `_legacy`.

Gaps:
- Ausente Vision en Flujo 2 activo.
- Ausente puente `LevelInventory`/Vision -> `Element25D` o `SemanticElement25D`.
- Ausente texto CAD cercano (`nearby_text`) como fuente de nombres.
- El semantic mapping actual es post-clash y conservador; por diseno "do not invent human-friendly names" (`core/coordination/semantic_elements.py:3`).

## 4. Seccion 2 - Capacidad del vision agent actual

- `analyze_plan()` usa el modelo resuelto por `vision_model_id()` y el default es `gpt-5.1` (`agents/vision_agent.py:38`, `agents/vision_agent.py:58`, `agents/vision_agent.py:1083`).
- El prompt obliga a analizar plantas, cortes, elevaciones y detalles para extraer elementos constructivos de presupuesto (`agents/vision_agent.py:155`).
- Tipos que puede identificar hoy: `plan_type`, `floor_area_m2`, alturas, `walls`, `doors`, `windows`, `wet_areas`, `kitchens`, `stairs`, `structural_elements`, `floor_finishes`, `ceiling_finishes`, `electrical`, `plumbing`, `fixtures`, `exterior_works`, `annotations_and_notes` (`agents/vision_agent.py:180`).
- Para arquitectura prioriza albanileria, acabados, carpinteria, pisos y cielos; para estructura prioriza rotulos/tablas/secciones; para electricidad y sanitario prioriza conteos/salidas/puntos (`agents/vision_agent.py:168`, `agents/vision_agent.py:171`, `agents/vision_agent.py:172`).
- Tiene configuracion por disciplina de subida: arquitectura, estructura, electrico y sanitario (`agents/vision_agent.py:349`). Sanitario/plomeria se soporta explicitamente con `plumbing` y `fixtures` (`agents/vision_agent.py:365`).

Compatibilidad con `clash_pairs()`:
- No es compatible directamente. `LevelInventory` es inventario semantico cuantificable, no geometria 2.5D con poligono y Z. `clash_pairs()` necesita `footprint_coords_mm` y `ZInterval` (`core/coordination/clash.py:94`, `core/coordination/models_25d.py:96`, `core/coordination/models_25d.py:100`).
- Transformacion necesaria: asociar cada item Vision a una geometria CAD o a una region de imagen, producir `SemanticElement25D`/metadata por `Element25D`, y conservar confianza/evidencia. Sin alineacion imagen-DWG o CAD handle, Vision solo puede nombrar zonas/objetos visibles, no resolver entidades exactas.

Gaps:
- Vision esta optimizado para inventario/presupuesto, no para validar clashes.
- No produce `bbox_mm` ni `footprint_coords_mm` por elemento.
- No hay prompt de coordinacion/clash actual en `agents/vision_agent.py`; el prompt habla de cuantificacion.

## 5. Seccion 3 - `build_hybrid_inventory()` como modelo de fusion

- `build_hybrid_inventory()` normaliza payloads Vision, salta errores, convierte dicts a `LevelInventory`, y por cada nivel llama `build_level_inventory(cad_facts, vision_level, ...)` (`core/pipeline.py:285`, `core/pipeline.py:296`, `core/pipeline.py:317`, `core/pipeline.py:319`).
- Si no hay Vision, o todas las paginas fallan, cae a CAD-only (`core/pipeline.py:297`, `core/pipeline.py:328`).
- La fusion queda acoplada al presupuesto porque su salida inmediata va a `quantify_inventory()` y a takeoffs/presupuesto (`core/pipeline.py:342`, `core/pipeline.py:367`, `core/pipeline.py:418`).
- Es reutilizable como patron, no como plug-in directo: el patron util es "CAD conserva trazabilidad y medidas; Vision llena semantica y evidencia; conflictos quedan documentados". La implementacion concreta retorna `LevelInventory`, no `Element25D`.

Campos semanticos del inventario hibrido que no existen en Element25D:
- `source_refs`, `assumptions`, `inputs`, `conflict_notes`, `confidence`, `evidence` por entidad (`core/schemas.py:48`).
- `wall_system`, `material_hint`, `finish_required`, `structural`, `openings_count` (`core/schemas.py:64`).
- `type_hint`, `material_hint`, dimensiones y host wall en puertas/ventanas (`core/schemas.py:92`, `core/schemas.py:104`).
- `fixture_type`, `location_hint`, `element_type`, `reinforcement`, `host_level`, `adjacent_elements` (`core/schemas.py:141`, `core/schemas.py:170`).

Gaps:
- No hay adaptador inverso `LevelInventory -> SemanticElement25D`.
- No hay fusion CAD+Vision para coordinacion con umbrales publicables.

## 6. Seccion 4 - Texto CAD ausente

- `process_autodesk_json()` si extrae textos: detecta entidades cuyo tipo contiene `text`, guarda `layer`, `entity_type`, `handle`, `content` y `bbox` (`processors/json_processor.py:196`).
- Tambien extrae dimensiones con `text` y `bbox` (`processors/json_processor.py:209`), y devuelve todo en `cad_facts.texts` y `cad_facts.dimensions` (`processors/json_processor.py:275`).
- No encontre asociacion espacial de esos textos a entidades cercanas en `process_autodesk_json()`: solo se almacenan listas separadas (`processors/json_processor.py:167`, `processors/json_processor.py:280`).
- Flujo 2 no usa `processors/json_processor.py`; usa sus propios extractores 2.5D (`scripts/run_nasas09_project_coordination.py:61`, `scripts/run_nasas09_project_coordination.py:425`). En Accore, `DBTEXT`/`MTEXT` se listan como `ANNOTATION_TYPES` (`core/coordination/from_dwg_accore.py:28`) y se saltan durante la extraccion de elementos (`core/coordination/from_dwg_accore.py:361`).
- El perfil Accore cuenta anotaciones (`raw_annotation_count`) pero no las convierte a contexto `nearby_text` (`core/coordination/from_dwg_accore.py:211`, `core/coordination/from_dwg_accore.py:230`).
- El payload crudo Accore queda disponible para semantic mapping (`scripts/run_nasas09_project_coordination.py:997`), pero `SemanticElement25D` solo hace lookup por handle y no calcula textos cercanos (`core/coordination/semantic_elements.py:105`, `core/coordination/semantic_elements.py:210`).

Respuesta directa: si hay textos en JSON Autodesk procesado por `json_processor`, se aprovechan en Flujo 1 como hechos CAD, pero no en Flujo 2. En Flujo 2, las entidades de texto Accore estan disponibles como raw payload para perfil/lookup, pero se excluyen como elementos geometricos y no se asocian por proximidad. Esto explica `nearby_text=0` si el run dependio del extractor 2.5D actual.

Gaps:
- Falta indice espacial de `DBText`/`MText` por archivo/nivel.
- Falta `nearby_text` en `SemanticElement25D`.
- Falta usar texto como `name_confidence` o `semantic_type_reason`.

## 7. Seccion 5 - Motor de clashes actual

- `clash_pairs()` detecta hard clashes: exige interseccion 2D (`poly_a.intersects(poly_b)`), area minima, y solape Z positivo (`core/coordination/clash.py:123`, `core/coordination/clash.py:136`).
- Aunque `ClashConflict.clash_type` admite `HARD` y `SOFT`, el motor siempre crea `clash_type="HARD"` (`core/coordination/clash.py:27`, `core/coordination/clash.py:152`).
- No encontre calculo de distancia minima/holgura horizontal para soft clashes en todo el repo. `clearance_required_mm` existe en `ZInterval`, pero solo infla el intervalo vertical absoluto (`core/coordination/models_25d.py:72`, `core/coordination/models_25d.py:127`).
- No hay reglas semanticas de severidad dentro de `clash_pairs()`: el motor filtra misma disciplina y calcula geometria, confianza y fuentes (`core/coordination/clash.py:121`, `core/coordination/clash.py:146`).
- La severidad y accion se derivan despues, en reporting, desde area, miembros, solape, confianza y disciplinas (`core/coordination/reporting.py:765`, `core/coordination/reporting.py:786`, `core/coordination/reporting.py:1022`).
- Para aplicar reglas semanticas, `clash_pairs()` tendria que recibir `element_type`, sistema, funcion, material, host, layer trust, si es anotacion/proxy, y reglas de pares por disciplina/tipo.
- `group_conflicts_into_incidents()` agrupa por par de archivos, nivel y celda espacial del centroide (`core/coordination/clash.py:197`, `core/coordination/clash.py:202`, `core/coordination/clash.py:206`).
- Hay revision/cohorte documental (`revision_proximity`, `cross_revision_pair_required`), pero no tracking persistente de clashes A vs B con estado resuelto/nuevo/reabierto (`core/coordination/fast_compare.py:675`, `core/coordination/fast_compare.py:820`, `core/coordination/fast_compare.py:958`).

Gaps:
- Soft clash real ausente.
- Reglas semanticas ausentes dentro del motor.
- Tracking entre revisiones de incidencias ausente; buscado en todo el repo incluyendo `_legacy`.

## 8. Seccion 6 - Reportes y visualizacion

- El runner escribe `primary_incidents.json/md`, `debug_candidates.json`, `hotspot_incidents.json/md`, `technical_coordination_report.md`, contextos JSON y reporte humano Markdown/HTML (`scripts/run_nasas09_project_coordination.py:1332`, `scripts/run_nasas09_project_coordination.py:1404`, `scripts/run_nasas09_project_coordination.py:1471`, `scripts/run_nasas09_project_coordination.py:1490`).
- El HTML humano es estatico, generado linea a linea desde Markdown; no es visor interactivo ni overlay (`core/coordination/reporting.py:671`).
- Los incidentes si tienen coordenadas suficientes para dibujar overlays basicos: `ClashConflict` guarda centroide y bounds en mm (`core/coordination/clash.py:30`), y `ClashIncident` guarda `plan_centroid_mm` y `plan_bounds_mm` (`core/coordination/clash.py:61`).
- Los reportes imprimen ubicacion numerica `level; (x, y) mm` (`core/coordination/reporting.py:1097`).
- No encontre salida visual anotada sobre plano original, dashboard, Streamlit, React, Dash o viewer interactivo en todo el repo incluyendo `_legacy`; lo mas cercano en legacy es renderer/salida de imagen, no UI activa.

Respuesta directa: los 748 grupos se podrian mostrar visualmente si se renderiza el plano o se exporta un canvas/SVG en coordenadas CAD, porque hay `bbox_mm`/centroide y footprints. El codigo actual no lo hace.

Gaps:
- Ausente overlay visual.
- Ausente transformacion coordenada CAD -> pixel/hoja.
- Ausente UI interactiva.

## 9. Seccion 7 - Ciclo de vida y presupuesto

- `ClashIncident` no tiene `status`, `assignee`, `resolved_at`, `created_at`, `last_seen`, ni historial (`core/coordination/clash.py:50`).
- `ClashConflict` tampoco contiene lifecycle; solo ids, disciplinas, tipo, solapes, geometria, fuentes y notas (`core/coordination/clash.py:18`).
- La responsabilidad por disciplina se deriva en reporte como texto `Arquitectura + Sanitario`, no como asignacion persistente (`core/coordination/reporting.py:1042`).
- No encontre conexion entre un clash del Flujo 2 y impacto presupuestario del Flujo 1. Flujo 1 compone presupuesto desde inventario/takeoffs (`core/pipeline.py:367`), mientras Flujo 2 escribe reportes de coordinacion independientes (`scripts/run_nasas09_project_coordination.py:1516`).
- El "budget readiness package" como integracion Flujo 2 -> Flujo 1 no fue encontrado en el codigo. Si el usuario se refiere a `readiness_payload`, este es readiness de comparabilidad/coordinacion, no alimenta presupuesto (`scripts/run_nasas09_project_coordination.py:1211`, `core/coordination/reporting.py:339`).

Gaps:
- Ausente modelo abierto/asignado/resuelto.
- Ausente ownership persistente.
- Ausente `clash -> takeoff/partida/costo`.

## 10. Seccion 8 - Elementos no etiquetados y heuristicas geometricas

- `process_autodesk_json()` pasa entidades geometricas genericas a `geometry_hints` con layer, tipo, nombre, handle, longitud, area, radio y bbox (`processors/json_processor.py:128`, `processors/json_processor.py:245`).
- No clasifica visualmente una polilinea sin layer semantico como puerta/ventana/columna; devuelve hechos genericos (`processors/json_processor.py:275`).
- En presupuesto hay heuristica de muros en `inventory_builder`, pero no de puertas por arco o ventanas por lineas paralelas; el conteo de puertas/ventanas depende de block/layer tokens o Vision. No encontre heuristica "arco 90 = puerta", "rectangulo estrecho en muro = ventana" o "circulo pequeno = columna" en todo el repo incluyendo `_legacy`.
- En Accore coordinacion, `Arc` se convierte en geometria bufferizada, no en puerta (`core/coordination/from_dwg_accore.py:481`).
- Los `BlockReference` o entidades con `Bounds` se marcan como `geometry_role="suppressed"` y `suppression_reason` `container_bbox` o `bounds_fallback` (`core/coordination/from_dwg_accore.py:520`, `core/coordination/from_dwg_accore.py:523`, `core/coordination/from_dwg_accore.py:525`).
- Fast compare acumula suprimidos como todo elemento que no sea `primary_geometry_role` (`scripts/run_nasas09_project_coordination.py:958`, `core/coordination/fast_compare.py:657`) y los escribe en `debug_candidates.json` con razon de supresion (`scripts/run_nasas09_project_coordination.py:1357`).

Cuantos de los 1021 suprimidos podrian ser elementos reales: no se puede determinar solo desde el codigo. El mecanismo puede suprimir bloques reales porque `BlockReference` cae como `container_bbox`, pero el reporte no conserva suficiente semantica para distinguir bloque real vs contenedor/ruido sin inspeccionar el payload y/o render visual (`core/coordination/from_dwg_accore.py:526`).

Gaps:
- Falta clasificador geometrico/topologico para CAD mal etiquetado.
- Falta revision de suprimidos por tipo/nombre/texto cercano.
- Falta evidencia visual para rescatar elementos reales de `container_bbox`.

## 11. Seccion 9 - Codigo legado

- `_legacy/run_clash_detection.py` contiene un enfoque antiguo de clash con COM + Vision GPT-4o para validar conflictos visibles; no esta migrado al runner activo. Este hallazgo fue buscado en todo `_legacy`.
- `_legacy/cad_automation/renderer.py` y `_legacy/vision_output` muestran que hubo render/imagenes legacy, pero no estan conectados al Flujo 2 activo.
- `_legacy/cad_automation/disciplines.py` separa/analiza disciplinas por capas; el activo infiere disciplina por ruta NASAS y reglas de seleccion (`scripts/run_nasas09_project_coordination.py:75`).
- `_legacy/cad_automation/analysis.py` tenia clash por bounding boxes; el activo lo reemplazo con Shapely + Z en `core/coordination/clash.py`.
- Hay duplicacion conceptual: disciplina por capa/ruta, extraction/rendering, bbox clash, presupuesto antiguo vs pipeline activo. No encontre un mapa formal de migracion legacy -> activo.

Funcionalidad util no migrada:
- Vision orientada a coordinacion/clashes desde `_legacy/run_clash_detection.py`.
- Render/imagenes legacy como base para overlays.
- Split por layouts/disciplinas antes de extraer geometria.

Gaps:
- Legacy util no integrado.
- Sin deprecacion documentada por modulo.

## 12. Seccion 10 - Inventario tecnico

### Modelos de IA

| Modelo | Uso | Archivo:linea |
| --- | --- | --- |
| `gpt-5.1` | Vision de planos por defecto | `agents/vision_agent.py:38` |
| `OPENAI_VISION_MODEL` | Override Vision | `agents/vision_agent.py:58` |
| `gpt-5.4` | Default helper chat compartido | `core/openai_chat_models.py:28` |
| `gpt-4o` | Clasificacion BC3 por capitulo | `agents/classifier_agent.py:430` |
| `gpt-4o` | Clasificacion GPT de layers CAD | `core/inventory_builder.py:494` |
| `gpt-4o` | Generador de partidas | `agents/partida_generator.py:174` |
| `text-embedding-3-small` | Embeddings semanticos BC3 | `knowledge/bc3_embeddings.py:28` |

### APIs externas y dependencias runtime

- OpenAI Chat Completions para Vision, layer classification, matching y partida generation (`agents/vision_agent.py:93`, `agents/classifier_agent.py:430`, `core/inventory_builder.py:494`, `agents/partida_generator.py:447`).
- OpenAI Embeddings (`knowledge/bc3_embeddings.py:91`).
- Autodesk APS OAuth (`aps_integration/aps_auth.py:14`).
- Autodesk OSS (`aps_integration/oss_manager.py:13`).
- Autodesk Model Derivative (`aps_integration/model_derivative.py:23`).
- Autodesk Design Automation (`aps_integration/da_manager.py:14`).
- AutoCAD Core Console local (`core/coordination/from_dwg_accore.py:23`).
- AutoCAD COM local fallback (`scripts/run_nasas09_project_coordination.py:920`).

### Fallbacks

- Vision captura excepciones por pagina y devuelve error por pagina (`agents/vision_agent.py:1169`).
- `build_hybrid_inventory()` cae a CAD-only si no hay Vision o todas las paginas fallan (`core/pipeline.py:297`, `core/pipeline.py:328`).
- PartidaGenerator cae a matching BC3 si falla o falta API key (`core/pipeline.py:109`, `core/pipeline.py:135`).
- Matching GPT cae a token overlap si falla o falta OpenAI (`agents/classifier_agent.py:662`, `agents/classifier_agent.py:669`).
- DWG coordinacion usa Accore y luego COM; si no hay Accore payload, cae a COM en fast_compare (`scripts/run_nasas09_project_coordination.py:913`, `scripts/run_nasas09_project_coordination.py:920`).
- Runner estandar DWG intenta APS opcional, Accore, COM y ezdxf (`scripts/run_nasas09_project_coordination.py:459`, `scripts/run_nasas09_project_coordination.py:475`, `scripts/run_nasas09_project_coordination.py:494`, `scripts/run_nasas09_project_coordination.py:512`).

Gaps:
- Defaults de modelo no estan completamente centralizados: Vision usa default propio `gpt-5.1`, helpers compartidos usan `gpt-5.4`, y varios agentes siguen hardcodeados a `gpt-4o`.
- No hay fallback Vision local.

## 13. Tabla de features

| Feature | Estado | Archivo relevante | Flujo | Notas |
| --- | --- | --- | --- | --- |
| Vision semantica de planos | Implementado | `agents/vision_agent.py:1066` | 1 | Produce `LevelInventory`, no `Element25D`. |
| Prompts por disciplina en Vision | Implementado | `agents/vision_agent.py:349` | 1 | Arquitectura, estructura, electrico, sanitario. |
| Inventario `LevelInventory` | Implementado | `core/schemas.py:190` | 1 | Rico en entidades, evidencia, confianza. |
| Fusion CAD + Vision | Implementado | `core/pipeline.py:285` | 1 | Patron reusable, implementacion acoplada a presupuesto. |
| Vision en coordinacion | Ausente | `scripts/run_nasas09_project_coordination.py:25` | 2 | No importa ni llama `vision_agent`; buscado en todo el repo incluyendo `_legacy`. |
| Extraccion 2.5D DWG | Implementado | `core/coordination/from_dwg_accore.py:339` | 2 | Huella, Z, layer, handle, metadata. |
| Campos semanticos tipados en `Element25D` | Parcial | `core/coordination/models_25d.py:87` | 2 | Solo `category` + `metadata`. |
| Semantic mapping post-clash | Parcial | `scripts/run_nasas09_project_coordination.py:1411` | 2 | MVP posterior, token-based. |
| Nombres publicables de elementos | Parcial/fragil | `core/coordination/semantic_elements.py:318` | 2 | Solo con `block_name` y confianza alta; no inventa nombres. |
| Texto CAD en Flujo 1 | Implementado | `processors/json_processor.py:196` | 1 | Extrae textos/dimensiones desde Autodesk JSON. |
| Texto CAD cercano en Flujo 2 | Ausente | `core/coordination/from_dwg_accore.py:361` | 2 | Textos se saltan como anotacion; no hay `nearby_text`. |
| Hard clashes | Implementado | `core/coordination/clash.py:123` | 2 | Interseccion planta + solape Z. |
| Soft clashes | Ausente | `core/coordination/clash.py:152` | 2 | Campo existe, logica no. |
| Reglas semanticas de clash | Ausente | `core/coordination/clash.py:115` | 2 | Trata geometria de forma generica. |
| Agrupacion de incidentes | Parcial | `core/coordination/clash.py:197` | 2 | Archivo + nivel + celda espacial. |
| Coordinate audit | Implementado | `scripts/run_nasas09_project_coordination.py:1152` | 2 | Habilita pares comparables por coordenadas. |
| Elementos suprimidos | Implementado/parcial | `scripts/run_nasas09_project_coordination.py:958` | 2 | Se separan por `geometry_role`, pero sin semantica suficiente. |
| Overlays visuales | Ausente | No encontrado en el codigo | 2 | Hay coordenadas, no render anotado. |
| HTML humano | Implementado/parcial | `core/coordination/reporting.py:671` | 2 | HTML estatico, no viewer. |
| Dashboard/UI interactiva | Ausente | No encontrado en el codigo | 2 | Buscado en todo el repo incluyendo `_legacy`. |
| Lifecycle de clash | Ausente | `core/coordination/clash.py:50` | 2 | Sin abierto/asignado/resuelto. |
| Impacto en presupuesto | Ausente | No encontrado en el codigo | Ambos | Sin enlace clash -> takeoff/partida. |
| Tracking entre revisiones de clashes | Ausente | `core/coordination/fast_compare.py:675` | 2 | Hay revision proximity de archivos, no incident lifecycle. |
| Heuristicas geometricas puerta/ventana | Ausente | `core/coordination/from_dwg_accore.py:481` | Ambos | Arcos se tratan como geometria. |
| Vision legacy para clashes | Parcial/no migrado | `_legacy/run_clash_detection.py` | 2 legacy | Util como referencia, no activo. |

## 14. Plan de accion priorizado para resolver los 748 grupos sin nombre

1. Construir `nearby_text` para Flujo 2. Extraer `DBText`/`MText` del payload Accore, indexarlos por bbox/centroide, y adjuntar textos cercanos a `SemanticElement25D`. Impacto alto, esfuerzo medio; ataca directamente `nearby_text=0`.
2. Enriquecer `SemanticElement25D` antes del reporte con `element_type`, `element_name`, `name_source`, `semantic_confidence`, `nearby_text`, `block_name`, `layer`, `handle`, `bbox_mm`, `centroid_mm`. Mantener conservadurismo, pero permitir nombres cuando texto/bloque/layer coincidan.
3. Conectar Vision como validador post-clash por recortes. Usar `plan_bounds_mm`/centroide para generar un overlay/recorte por incidente o hotspot y pedir a Vision una clasificacion controlada: que elementos se ven, si el clash parece real, y que nombre publicable tiene.
4. Generar overlays visuales estaticos por incidente. Aunque no haya UI, un PNG/SVG con footprints A/B, bounds y textos cercanos permitiria auditar los 748 grupos y rescatar hallazgos.
5. Crear reglas semanticas de publishability. Ejemplos: `pipe` vs `wall/beam/column` con texto cercano y geometria primaria = candidato defendible; layer de anotacion o doble proxy = no defendible.
6. Revisar suprimidos por `container_bbox` y `bounds_fallback`. Separar bloques reales de contenedores, conservar nombres de bloque utiles y no mezclarlos con ruido tecnico.
7. Implementar soft clashes reales para MEP: distancia minima/clearance 2D/3D por tipo de sistema y elemento host.
8. Introducir lifecycle persistente: `incident_id` estable, estado, responsable, first_seen/last_seen/resolved, revision anterior y diff.
9. Conectar coordinacion con presupuesto solo despues de tener semantic mapping confiable: mapear incidente a `LevelInventory`/takeoff y marcar impacto cualitativo o cuantitativo.
10. Migrar selectivamente legacy: rescatar prompts/flujo visual de `_legacy/run_clash_detection.py` y renderer legacy como base para validacion visual, sin reactivar el clash bbox antiguo.
