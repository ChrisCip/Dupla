# Dupla - Project Overview

**Fecha:** Abril 11, 2026  
**Estado:** Arquitectura activa, en fase de estabilización de permisos APS  
**Lenguaje:** Python 3.10+  
**Licencia:** N/A (proyecto interno)

---

## 1. Qué es Dupla

Dupla es un **sistema integral de presupuestación de obras** que convierte planos de construcción (DWG/PDF) en líneas presupuestarias trazables y exportables. 

**Propósito:** Automatizar la cuantificación de proyectos constructivos y su asignación a catálogos de presupuesto (FIEBDC/BC3 de Presto), eliminando trabajo manual repetitivo y errores de interpretación.

**Entrada:** Planos CAD (DWG) + imágenes/PDFs del mismo proyecto  
**Salida:** Presupuesto estructurado (Excel listo para revisar + BC3 para importar en Presto)

---

## 2. Arquitectura general

Dupla funciona con una arquitectura **JSON-first basada en APS** (Autodesk Platform Services), NO en COM/AutoCAD local.

### Flujo end-to-end:

```
┌─────────────────────────────────────────────────────────────┐
│                    DUPLA PIPELINE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. APS EXTRACTION                                         │
│     DWG → Autodesk Model Derivative → JSON de hechos CAD  │
│                                                             │
│  2. VISION PAGES                                           │
│     PDF/imágenes → renderizadas si es necesario           │
│                                                             │
│  3. VISION ANALYSIS (GPT-4o)                              │
│     Cada página → inventario constructivo (muros, puertas, │
│     ventanas, estructura, etc.)                           │
│                                                             │
│  4. KNOWLEDGE INPUTS                                       │
│     Cargar BC3 + PRES.xlsx (training) + embeddings        │
│                                                             │
│  5. BUILD BUDGET                                           │
│     ├─ Merge CAD + visión → inventario híbrido            │
│     ├─ Cuantificación determinística con fórmulas         │
│     ├─ Expansión por reglas                               │
│     └─ Matching a partidas BC3 (LLM + semantic)           │
│                                                             │
│  6. EXCEL EXPORT                                           │
│     → dupla_budget_ready_full.xlsx (listo para revisar)   │
│                                                             │
│  7. BC3 EXPORT (opcional)                                 │
│     → dupla_budget_ready_full.bc3 (importable en Presto)  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Módulos clave

### 3.1 **APS Integration** (`aps_integration/`)

**Responsabilidad:** Comunicación con Autodesk Platform Services

| Archivo | Función | Notas |
|---------|---------|-------|
| `aps_auth.py` | Autenticación OAuth 2-legged | Obtiene token de CLIENT_ID/CLIENT_SECRET |
| `model_derivative.py` | Traducción de DWG a SVF2 y extracción de propiedades | API polling, reintentos automáticos |
| `oss_manager.py` | Gestión de buckets y upload de archivos | Signed URLs, directorio seguro |

**Estado:** ✅ Funcional pero requiere permisos de Autodesk habilitados para Model Derivative

---

### 3.2 **Processors** (`processors/`)

**Responsabilidad:** Parseo normalización de datos de entrada

| Archivo | Entrada | Salida | Notas |
|---------|---------|--------|-------|
| `json_processor.py` | JSON bruto de Model Derivative | Hechos CAD normalizados | Extrae capas, textos, cotas, hatch, bloques, geometría. Sin mapeo a presupuesto todavía |
| `bc3_parser.py` | Archivo .bc3 (FIEBDC) | Dict con conceptos, partidas, jerarquía | Parser robusto de formato heredado |

**Estado:** ✅ Estable

---

### 3.3 **Agents** (`agents/`)

**Responsabilidad:** Toma de decisiones y transformaciones complejas

| Archivo | Entrada | Salida | Notas |
|---------|---------|--------|-------|
| `vision_agent.py` | Imágenes de planos | LevelInventory (muros, puertas, ventanas, etc.) | GPT-4o Vision, 2 pasos: primero cuenta simple, luego mapea a esquemas |
| `quantifier_agent.py` | LevelInventory | QuantityTakeoff[] | Fórmulas determinísticas (no LLM). Cada cantidad es trazable |
| `classifier_agent.py` | QuantityTakeoff[] + BC3 | BudgetCandidate[] | GPT-4o + fallback token-overlap. Segmentación por capítulos |

**Estado:** 🟡 Funcional. Vision funciona sin issues; classifier funciona pero depende de modelo disponible

---

### 3.4 **Core** (`core/`)

**Responsabilidad:** Orquestación, esquemas tipados, tuberías

| Archivo | Descripción |
|---------|-------------|
| `pipeline.py` | Funciones helper para orquestación (`build_budget_from_sources`, etc.) |
| `schemas.py` | Dataclasses tipadas: `ProjectContext`, `LevelInventory`, `Wall`, `Door`, `QuantityTakeoff`, `BudgetCandidate`, etc. |
| `inventory_builder.py` | Merge de inventario CAD + visión (conflicto resolution, hints de material) |
| `stage.py` | Motor de ejecución por etapas con timing y manejo de errores (`PipelineRunner`, `StageResult`) |
| `logging_config.py` | Setup de logging |

**Estado:** ✅ Estable

---

### 3.5 **Budget** (`budget/`)

**Responsabilidad:** Composición del presupuesto final y exportes

| Archivo | Función |
|---------|---------|
| `composer.py` | Arma estructura de capítulos, líneas, subtotales. Genera códigos internos (DUP-xxxx) para partidas sin BC3 |
| `chapter_rules.py` | Reglas de clasificación y asignación de capítulos por tipo de takeoff |
| `export_excel.py` | Genera XLSX con estilo, fórmulas Excel, reviewer sheet |
| `export_bc3.py` | Genera BC3 (FIEBDC) importable en Presto |

**Estado:** ✅ Estable

---

### 3.6 **Rules Engine** (`rules_engine/`)

**Responsabilidad:** Expansión de partidas derivadas

| Archivo | Función |
|---------|---------|
| `__init__.py` | Motor con registry de reglas. Aplica transformaciones: ej. `wall_net_area` → `wall_finish_paint` |
| `registry.py` | Definición de reglas (criterios de match + derivadas) |
| `default_rules.json` | Reglas por defecto cargables |

**Estado:** 🟡 Funcional pero reglas aún limitadas (TODO: expandir para acabados, asamblies)

---

### 3.7 **Knowledge** (`knowledge/`)

**Responsabilidad:** Contexto inteligente, embeddings, calibración

| Archivo | Función |
|---------|---------|
| `bc3_embeddings.py` | Embeddings semánticos (OpenAI `text-embedding-3-small`). Búsqueda cóseno en BC3 |
| `pres_expansion.py` | Inyección de líneas plantilla desde PRES.xlsx cuando no hay match CAD exacto |
| `training_data.py` | Extracción de pares entrada/salida desde PRES.xlsx para few-shot de GPT-4o |
| `methodology_generator.py` | Genera contexto auto-construido desde BC3/PRES para mejorar prompts de visión |
| `feedback_store.py` | (Future) almacenamiento de correcciones usuario para reentrenamiento |

**Estado:** ✅ Embeddings funcionales; PRES expansion funcionando; feedback_store es scaffolding

---

## 4. Flujo detallado

### Etapa 1: APS Extraction
```
DWG local
  ↓
[get_aps_token] → obtiene token OAuth
  ↓
[create_bucket] → verifica/crea bucket en OSS (Object Storage Service)
  ↓
[upload_file_to_bucket] → sube DWG con signed URL
  ↓
[extract_dwg_data]
  ├─ [translate_to_svf2] → job de traducción a Model Derivative
  ├─ [wait_for_translation] → polling hasta success/failed/timeout
  └─ [extract_properties] → descarga JSON de propiedades
  ↓
[process_autodesk_json] → normaliza en hechos CAD (layers, texts, etc.)
  ↓
hechos_cad.json (normalizado)
```

### Etapa 2-3: Vision Analysis
```
PDF o imágenes
  ↓
[render_pdf_to_images] → si es PDF, renderiza a PNG (PyMuPDF)
  ↓
Para cada página:
  [run_full_vision_analysis + GPT-4o]
  ├─ Input: imagen + CAD hints (layers, scale, etc.) + metodología
  ├─ Output: JSON con counts (walls, doors, etc.)
  └─ Mapea a LevelInventory schema
  ↓
vision_inventory_results.json
```

### Etapa 4: Knowledge Inputs
```
BC3_PATH (TGIU.bc3)
  ↓
[parse_bc3] → conceptos, partidas, jerarquía
  ↓
Si BC3 tiene items:
  ├─ [build_bc3_embeddings] → vectores de embedding (caché local)
  └─ → EmbeddingIndex para búsqueda semántica

Si XLSX_TRAINING_PATH existe:
  ├─ [extract_training_pairs] → pares entrada/salida reales
  └─ → few-shot examples para GPT-4o
```

### Etapa 5: Build Budget
```
cad_facts + vision_results
  ↓
[build_hybrid_inventory]
  ├─ Merge CAD-derived + vision-derived entities
  └─ Conflict resolution (prefiere JSON, anota conflictos)
  ↓
hybrid_levels: LevelInventory[]
  ↓
[quantify_inventory] → determinístico
  ├─ Para cada wall: area = length * height - openings_area
  ├─ Para estructura: volume = section_w * section_h * length
  └─ Formula + trace metadata en cada takeoff
  ↓
base_takeoffs: QuantityTakeoff[]
  ↓
[rules_engine.apply] → expansión
  └─ wall_net_area → wall_finish_paint (derivada)
  ↓
expanded_takeoffs: QuantityTakeoff[]
  ↓
[match_takeoffs_to_bc3]
  ├─ Segmenta por capítulo (item_type → cap. 01-09)
  ├─ Para cada capítulo: GPT-4o asigna best BC3 code
  └─ Fallback: token-overlap si no hay OpenAI
  ↓
candidates_by_takeoff: dict[item_key → BudgetCandidate[]]
  ↓
[build_final_budget] & [compose_budget]
  ├─ Arma capítulos, líneas, subtotales
  ├─ Genera códigos internos (DUP-xxxx) para sin BC3
  └─ Fórmulas Excel para cálculo dinámico
  ↓
budget_output.json (estructura final)
```

### Etapa 6-7: Exportes
```
budget_output.json
  ├─ [export_budget_workbook] → .xlsx con formato, fórmulas
  └─ [export_budget_bc3] → .bc3 (FIEBDC) para Presto
  ↓
dupla_budget_ready_full.xlsx
dupla_budget_ready_full.bc3
```

---

## 5. Estado actual

### ✅ Hecho

- **APS integration** completa (auth, upload, Model Derivative)
- **CAD normalization** robusta (json_processor)
- **Vision analysis** con GPT-4o (2 pasos, evita LLM schema hallucinations)
- **Hybrid inventory merge** con conflict detection
- **Deterministic quantification** con fórmulas trazables
- **Rules engine scaffold** funcional (expansión básica)
- **BC3 parsing** FIEBDC completo
- **Semantic embeddings** con OpenAI (caché local)
- **BC3 matching** dual: GPT-4o + token-overlap fallback
- **Budget composition** multi-capítulo con subtotales
- **Excel export** con estilo y fórmulas
- **Pipeline orchestration** con etapas y reporte
- **26 tests** (integración, inventario, cuantificación, reglas, embeddings, composer)

### 🟡 Parcial/En desarrollo

- **Rules engine**: Expansiones son básicas. TODO: acabados, asamblies, deducción de aberturas
- **PRES expansion**: Funciona pero NO es la vía predeterminada (flag `PRES_TEMPLATE_TAKEOFFS=False`)
- **BC3 hierarchy parsing**: Parser existe pero TODO: casos edge de decomposición FIEBDC
- **Unit family validation**: Existe pero no está integrado al guardrail de composer

### ⚠️ Bloqueado

- **APS Model Derivative**: Requiere "ProductAccessRequiresCapacity" habilitado en tu tenant de Autodesk. Ver sección [Instalación & Configuración](#6-instalación--configuración).

### ❌ No hecho / Futura

- **Feedback loop**: feedback_store.py es solo scaffolding; no hay reentrenamiento
- **Multilingual BC3**: Todo está calibrado para español (dominicano)
- **Vector search con synonyms**: Embeddings existen; TODO: inyectar diccionario de sinónimos
- **Domain-specific rules library**: Hoy es manual; debería ser declarativo + facil de extender

---

## 6. Instalación & Configuración

### 6.1 Requisitos

- Python 3.10+
- Windows/Linux/Mac (recomendado Windows para PDF rendering)

### 6.2 Setup

```bash
# Clonar repo
cd /ruta/a/Dupla

# Crear virtual env (opcional pero recomendado)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# (Opcional) Si necesitas legacy COM:
pip install -r requirements-legacy.txt
```

### 6.3 Variables de entorno (.env)

```env
# OpenAI API
OPENAI_API_KEY=sk-proj-...

# Autodesk APS
CLIENT_ID=...
CLIENT_SECRET=...
APS_BUCKET_NAME=dupla_bucket_unique_v2
```

**Importante:** APS requiere que tu tenant de Autodesk tenga permisos para Model Derivative. Contactar a Autodesk si ves error `ProductAccessRequiresCapacity`.

---

## 7. Cómo ejecutar

### Opción 1: Pipeline completo local (más común)

```bash
python dupla_run_full_analysis_local.py
```

**Edita CONFIG en el archivo antes:**
- `PROJECT_NAME`, `PROJECT_ID`
- `DWG_PATH`, `PDF_PATH`, `IMAGES_DIR`
- `BC3_PATH` (ej: `./data/TGIU.bc3`)
- `XLSX_TRAINING_PATH` (ej: `./data/PRES.xlsx`, opcional)
- `OUTPUTS_DIR`, `OUTPUT_NAME`

**Salida:**
- `pipeline_report.json` (etapas, tiempos, errores)
- `dupla_debug.log` (logs detallados)
- `dupla_budget_ready_full.xlsx` (presupuesto)
- `dupla_budget_ready_full.bc3` (BC3 para Presto)

### Opción 2: Componente por componente (desarrollo)

```python
from processors.json_processor import process_autodesk_json
from processors.bc3_parser import parse_bc3
from agents.vision_agent import run_full_vision_analysis
from core.pipeline import build_budget_from_sources
from core.schemas import ProjectContext

# 1. Procesar JSON de APS
cad_facts = process_autodesk_json("path/to/autodesk_raw.json")

# 2. Parsear BC3
bc3_catalog = parse_bc3("./data/TGIU.bc3")

# 3. Visión
vision_results = run_full_vision_analysis("path/to/images/", cad_facts)

# 4. Budget
context = ProjectContext(project_name="Mi Proyecto", ...)
budget = build_budget_from_sources(context, cad_facts, vision_results, bc3_catalog)
```

---

## 8. Estructura del repo

```
Dupla/
├── README.md                             # Intro rápida
├── TECHNICAL_DOCS.md                     # Docs de APS/JSON (desactualizado)
├── README_NUEVOS_CAMBIOS.md              # Changelog de migración com a APS
├── PROJECT_OVERVIEW.md                   # ← ESTE ARCHIVO
├── dupla_run_full_analysis_local.py      # ← ENTRADA PRINCIPAL
│
├── aps_integration/
│   ├── aps_auth.py
│   ├── model_derivative.py
│   ├── oss_manager.py
│   └── DuplaExtractor/                   # (legacy)
│
├── agents/
│   ├── vision_agent.py
│   ├── quantifier_agent.py
│   ├── classifier_agent.py
│   └── __init__.py
│
├── processors/
│   ├── json_processor.py
│   ├── bc3_parser.py
│   ├── json_extractor.py
│   ├── text_extractor.py
│   └── __init__.py
│
├── core/
│   ├── pipeline.py
│   ├── schemas.py
│   ├── inventory_builder.py
│   ├── stage.py
│   ├── logging_config.py
│   └── __init__.py
│
├── budget/
│   ├── composer.py
│   ├── chapter_rules.py
│   ├── export_excel.py
│   ├── export_bc3.py
│   ├── pres_structural_filter.py
│   └── __init__.py
│
├── rules_engine/
│   ├── __init__.py
│   ├── registry.py
│   └── default_rules.json
│
├── knowledge/
│   ├── bc3_embeddings.py
│   ├── pres_expansion.py
│   ├── training_data.py
│   ├── methodology_generator.py
│   ├── feedback_store.py
│   ├── office_methodology.md
│   ├── corrections.jsonl
│   ├── cache/                            # (embeddings caché)
│   └── __init__.py
│
├── config/
│   ├── layer_mapping.py
│   └── __init__.py
│
├── tests/
│   ├── test_pipeline_integration.py
│   ├── test_quantifier_agent.py
│   ├── test_inventory_builder.py
│   ├── test_budget_composer.py
│   ├── test_bc3_embeddings.py
│   ├── test_bc3_parser.py
│   ├── test_pres_expansion.py
│   ├── test_training_data.py
│   └── ... (19 tests más)
│
├── data/
│   └── TGIU.bc3                          # Catálogo de presupuesto
│
├── output/
│   └── prueba_web_01/                    # Resultados de ejecuciones
│
├── _legacy/
│   ├── README_LEGACY_COM.md
│   ├── cad_automation/                   # Legacy COM automation
│   └── ... (scripts viejos)
│
├── requirements.txt                      # Dependencias activas
├── requirements-legacy.txt               # Dependencias opcionales COM
└── .env                                  # ← CONFIGURA ESTO
```

---

## 9. Dependencias clave

| Librería | Versión | Propósito |
|----------|---------|----------|
| `openai` | ≥1.0 | GPT-4o Vision & Embeddings |
| `python-dotenv` | ≥1.0 | Carga .env |
| `requests` | ≥2.31 | HTTP a APS |
| `openpyxl` | ≥3.1 | Excel generation |
| `pymupdf` (fitz) | ≥1.24.0 | PDF rendering |
| `pytest` | ≥7.0 | Testing |
| `numpy` | (indirect) | Embeddings vectors |

---

## 10. Troubleshooting

### Error: "ProductAccessRequiresCapacity"
**Causa:** Tu app de Autodesk no tiene acceso a Model Derivative.  
**Solución:** Contacta a Autodesk o usa datos pre-procesados (JSON local) saltando etapa 1.

### Error: "Only the bucket creator is allowed"
**Causa:** Bucket existente creado por otra app.  
**Solución:** Cambia `APS_BUCKET_NAME` en .env a un nombre único.

### Error: "OPENAI_API_KEY not configured"
**Causa:** Variable de entorno faltante.  
**Solución:** Asegúrate de que `.env` esté en la raíz y que `load_dotenv()` se ejecute.

### Vision análisis muy lento
**Causa:** GPT-4o procesa página por página.  
**Solución:** Reduce PDFs a <20 páginas o usa imágenes directamente.

### BC3 no encontrado
**Causa:** Ruta relativa incorrecta.  
**Solución:** Asegúrate que `BC3_PATH` sea relativo a REPO_ROOT (raíz del proyecto).

---

## 11. Testing

```bash
# Todos los tests
pytest tests/

# Test específico
pytest tests/test_pipeline_integration.py -v

# Coverage
pytest --cov=core --cov=agents tests/
```

---

## 12. Roadmap & TODOs

### Corto plazo (próximas 2-4 semanas)
- [ ] Estabilizar APS (permisos/capacidad con Autodesk)
- [ ] Expand rules engine (acabados, assemblies)
- [ ] Integrar unit validation en composer
- [ ] Mejorar BC3 hierarchy parsing

### Mediano plazo (1-2 meses)
- [ ] Feedback loop de correcciones usuario
- [ ] Diccionario de sinónimos BC3
- [ ] Soporte multiidioma (español/inglés mínimo)
- [ ] Dashboard web para monitoreo

### Largo plazo (3+ meses)
- [ ] Machine learning fine-tuning en openai (si viable)
- [ ] RAG sobre histórico de proyectos
- [ ] Integración directa con Presto API
- [ ] Mobile app para revisión de presupuestos

---

## 13. Contactos & Recursos

**Creador original:** Chris (chris@example.com)  
**Documentación oficial:** [README.md](README.md), [TECHNICAL_DOCS.md](TECHNICAL_DOCS.md)  
**Autodesk APS Docs:** https://developer.autodesk.com/  
**OpenAI API:** https://platform.openai.com/  
**Presto (FIEBDC):** https://auspresto.com  

---

## 14. Notas finales

- **Este proyecto NO depende de COM/AutoCAD local**: Es cloud-first via Autodesk APS.
- **Cada cantidad es trazable**: Todas las fórmulas quedan grabadas en `trace` metadata.
- **Determinístico donde es posible**: Visión y matching son LLM, pero cuantificación es pura matemática.
- **Modular y testeable**: Cada etapa puede ejecutarse independientemente.
- **Historicamente calibrado**: PRES.xlsx + training_data.py permiten pocos-shots inteligentes.

---

**Última actualización:** 2026-04-11  
**Próxima revisión recomendada:** 2026-05-01
