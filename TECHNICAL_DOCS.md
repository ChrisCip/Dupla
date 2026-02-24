# Documentación Técnica: Pipeline Integral Dupla

Esta guía profundiza en las mecánicas internas de los módulos que componen el script `run_full_analysis.py`. Está orientada a analistas de datos, ingenieros de costos y desarrolladores que busquen mantener, extender o depurar el sistema híbrido de análisis CAD/Presupuestos.

---

## 1. Módulos de Aprendizaje (Parsers)

El sistema soporta una ingesta de datos dual para "aprender" los costos históricos y los catálogos estandarizados.

### 1.1 Parser FIEBDC/BC3 (`parse_bc3`)
El estándar español FIEBDC-3 (común en Presto, Arquímedes, etc.) almacena la base de datos de construcción en texto plano separado por barras `|`, precedido de tildes `~`.
- **~C (Conceptos):** El script extrae el `Código` (ignorando jerarquías secundarias tras el `#`), la `Unidad`, el `Resumen` y el `Precio`.
- **~D (Descomposición):** Extrae la estructura padre-hijo (Capítulo -> Partida -> Subpartida).
- **~T (Textos):** Textos largos descriptivos.
- **Salida:** Clasifica a los conceptos en `Partidas` (tienen precio > 0 y unidad) y `Capítulos` (no tienen unidad y agrupan otras).

### 1.2 Parser XLSX (`parse_xlsx`)
Extrae de manera difusa datos de cualquier tabla de Excel usando heurísticas de cabecera.
- Busca filas que contengan palabras clave (*partida, descripción, unidad, cantidad, precio, importe*).
- Una vez anclada la cabecera, mapea las columnas internamente leyendo dinámicamente cada hoja (`sheet`) del libro.
- Ignora filas sin datos útiles, devolviendo una lista plana de diccionarios.

---

## 2. Análisis Nativo CAD (Win32COM)

Utilizando la librería `win32com.client`, el pipeline accede a la instancia activa de *AutoCAD.Application*.

**Proceso de Barrido:**
1. Apunta a `ActiveDocument.ModelSpace` y cuenta el ecosistema (`Count`).
2. Itera secuencialmente tratando de capturar las métricas de:
   - **Longitud** (`Length`)
   - **Área** (`Area`)
   - **Bounding Box** (`GetBoundingBox()`) usando los puntos mínimo y máximo.
3. Se agrupa la estadística sumatoria bajo un diccionario clasificado por el identificador geométrico de su respectiva capa (`Layer`), omitiendo entidades tipo *BlockReference, Text o MText* para evitar falsos positivos en longitud.

---

## 3. Algoritmos de Detección de Interferencias (Clashes)

El sistema emplea un enfoque híbrido en dos vertientes:

### 3.1 Detección Geométrica (Nativa Bounding-Box)
Se abstrae cada entidad a un prisma rectangular bidimensional `[min_x, min_y]` a `[max_x, max_y]`.
- Se itera comparando pares de disciplinas predefinidos (Ej. *"A" vs "S"*).
- La condición fundamental de intersección planar se calcula con: `min_a_x <= max_b_x And max_a_x >= min_b_x ...`
- Se calcula un ratio de *Overlap* porcentual derivado del área compartida sobre el área del elemento más pequeño.
- Se cataloga la Severidad en función del overlap absoluto: *CRÍTICO (>80%)*, *MAYOR (>50%)*, *MENOR (<50%)*.

### 3.2 Detección Semántica/Visual (Visión OCR y GPT-4o)
El sistema extrae cualquier imagen PNG del subdirectorio `vision_output/pdf_pages/` (planos renderizados) formatea el bitstream local en *base64* y lo inyecta directo en un prompt visual. El modelo razona la arquitectura renderizada analizando inconsistencias visuales que la geometría "nativa" falla en catalogar.

---

## 4. Estrategia de Consolidación Presupuestaria (Generación IA)

Para sortear las limitaciones severas de *Token Limits* impuestos por la ventanilla de contexto de *GPT-4o* (Max Out: 4096), ejecutamos una estrategia probabilística estructurada tipo "Chunking":

1. **Segmentación Contextual:** Los requerimientos de la métrica (capas extraídas, partidas base de conocimiento) se fraccionan temáticamente en *9 Capítulos Lógicos* (Movimiento de tierras, Estructura, ...).
2. **Prompts Escalonados:** El script efectúa **9 llamadas seriales repetidas** dictando reglas asertivas que ponderan emparejar lo medido o en caso contrario *Estimar* fundamentándolo en la volumetría de la obra (`~3426m2`, `14niveles`). Todo bajo un "Strict JSON Mode".
3. **Control de Fallos:** Múltiples heurísticas de `json.loads` mitigan fallos clásicos generativos originados en "hallucinaciones de bloque de código" implementando Regex corrector para comas huérfanas o bloques inestables.

## 5. Salida Estructurada Local (Dump Lifecycle)

De naturaleza investigativa, la ejecución persiste todos los "snapshots" volátiles en `analysis_output/dump/`. De este modo si una consulta API colapsa o una capa mal interpretada distorsionó un presupuesto de $20 MM a $0, el desarrollador rastreará las capas afectadas dentro de `dwg_layers.json` o la respuesta generativa cruda en `raw_*.txt`. 
