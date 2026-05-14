# Cambios recientes en coordinación: tiles, Vision y overlays

Fecha: 2026-05-14  
Repositorio: Dupla

## Resumen

Se implementó el flujo visual del pipeline de coordinación para producir tiles SVG georreferenciados, validarlos opcionalmente con un modelo de visión, generar overlays anotados y mostrar esas imágenes en los reportes humanos Markdown/HTML.

## Archivos creados

### `coordination/reporting/tile_renderer.py`

Nuevo generador de tiles SVG sin dependencias gráficas externas.

Incluye:
- `TileSpec`
- `RenderedTile`
- `compute_tile_bbox()`
- `collect_elements_in_bbox()`
- `render_tile_svg()`
- `render_incident_tile()`
- `render_all_incident_tiles()`
- `save_tile()`
- `render_annotated_tile()`
- `render_all_annotated_tiles()`

Funcionalidad:
- Renderiza geometría CAD en SVG.
- Colorea polígonos por disciplina.
- Dibuja zona de clash en rojo.
- Incluye textos CAD cercanos.
- Agrega grid, leyenda y barra de escala.
- Genera overlays anotados con severidad, resultado Vision, labels semánticos y responsable de acción.

### `coordination/semantic/vision_validator.py`

Nuevo módulo opt-in para validación visual de clashes con IA.

Incluye:
- `VisionElementResult`
- `VisionClashAssessment`
- `VisionTileResult`
- `validate_tile()`
- `validate_incident_tiles()`
- `apply_vision_results()`
- `vision_tile_result_to_dict()`

Funcionalidad:
- Construye un prompt específico de coordinación/clashes.
- Usa `COORDINATION_VISION_MODEL` o `gpt-5.1` por defecto.
- Convierte SVG a PNG si `cairosvg` está disponible.
- Si no hay `cairosvg`, envía el SVG como texto al modelo.
- Parseo robusto de JSON, incluyendo respuestas envueltas en backticks.
- No modifica `ClashIncident`; devuelve overrides por `incident_id`.

### Tests nuevos

Se añadieron:
- `coordination/tests/test_tile_renderer.py`
- `coordination/tests/test_vision_validator.py`
- `coordination/tests/test_tile_overlays.py`

Cubren:
- Cálculo de bbox y escala.
- Render SVG básico y con clash.
- Escritura de tiles.
- Prompt y parseo de Vision.
- Validación mockeada sin llamadas reales a OpenAI.
- Overlays anotados.
- HTML con tiles y semáforo.

## Archivos modificados

### `coordination/scripts/run_nasas09_project_coordination.py`

Se integró el flujo visual:

- Renderiza tiles base tras generar `primary_incidents`.
- Agrega flags:
  - `--enable-vision-validation`
  - `--max-vision-tiles`
  - `--vision-model`
- Si Vision está habilitado:
  - valida tiles renderizados,
  - escribe `vision_validation.json`,
  - genera `vision_overrides`.
- Después de construir `technical_report_context`, genera tiles anotados con:
  - severidad,
  - responsable de acción,
  - resultados Vision si existen.

### `coordination/reporting/reporting.py`

Se actualizó el reporte humano:

- Markdown ahora incluye referencias a:
  - `tiles/{incident_id}_annotated.svg`
- HTML fue enriquecido:
  - CSS inline,
  - tablas HTML reales,
  - contenedores de tiles,
  - imágenes SVG embebidas como `<img>`,
  - fallback al tile base si el anotado no existe,
  - semáforo de severidades al inicio.

## Verificación ejecutada

Pasaron:

```bash
python -m py_compile coordination/reporting/tile_renderer.py coordination/reporting/reporting.py coordination/scripts/run_nasas09_project_coordination.py coordination/tests/test_tile_overlays.py
```

```bash
python -m pytest coordination/tests/test_tile_renderer.py coordination/tests/test_tile_overlays.py coordination/tests/test_vision_validator.py coordination/tests/test_coordination_reporting.py coordination/tests/test_coordination_reporting_semantic.py -v --tb=short
```

Resultado:

```text
33 passed
```

También pasaron individualmente:

```bash
python -m pytest coordination/tests/test_vision_validator.py -v --tb=short
python -m pytest coordination/tests/test_tile_overlays.py -v --tb=short
```

## Bloqueos conocidos no relacionados

La suite completa:

```bash
python -m pytest coordination/tests/ -v --tb=short
```

sigue fallando en collection por problemas existentes del entorno/plataforma:

- `ctypes.windll` no existe en macOS al importar `coordination/extraction/from_dwg_accore.py`.
- Falta `ezdxf` en el entorno Python activo.

Estos errores no fueron introducidos por los cambios de tiles/Vision/overlays.

## Salidas nuevas del pipeline

Cuando el runner produce incidencias:

- Tiles base:
  - `tiles/{incident_id}.svg`
- Tiles anotados:
  - `tiles/{incident_id}_annotated.svg`

Cuando se usa `--enable-vision-validation`:

- Resultados Vision:
  - `vision_validation.json`

## Uso esperado

Ejemplo:

```bash
python -m coordination.scripts.run_nasas09_project_coordination \
  --analysis-profile fast_compare \
  --enable-semantic-mapping \
  --enable-vision-validation \
  --max-vision-tiles 50
```

Sin `--enable-vision-validation`, el pipeline sigue generando tiles base y anotados con severidad/responsable, pero sin assessment ni labels de Vision.
