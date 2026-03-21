# 🚀 Actualización del Pipeline Híbrido: Mejoras en Procesamiento JSON y Vision Agent

Se ha implementado una refactorización completa orientada a mejorar la compatibilidad estricta con los presupuestos estilo Presto y a solucionar bugs críticos en la interpretación de la IA. A continuación, se detallan todos los cambios realizados.

---

## 1. Correcciones en el Procesador JSON (`json_processor.py`)

El script encargado de parsear el volcado de CAD original (*Model Derivative*) de 47MB presentaba problemas detectando los tipos de objeto y extraía textos vacíos. 

**Mejoras implementadas:**
- **Detección de Tipos Precisos:** Se cambió la lógica para leer la jerarquía `properties["General"]["Name "]` (con espacio final) en lugar del nombre genérico `obj["name"]`. Esto permitió identificar correctamente *Hatches*, *Dimensions*, *Block References* y geometría ignorada.
- **Extracción de Textos Reales:** Se corrigió la ruta de extracción de contenidos; ahora el script busca directamente en `properties["Text"]["Contents"]` para MTexts y Textos.
- **Lectura de Dimensiones Universitarias:** Se eliminó el filtro rígido del layer `00-MEDICION` para buscar dimensiones genuinas en todo el modelo leyendo la propiedad `properties["Text"]["Measurement"]`.
- **Limpieza de Nombres de Bloques:** Se implementó una expresión regular para limpiar los sufijos hexadecimales (ej. `[206C611]`) del nombre de los "Block Reference".

---

## 2. Refactorización del Agente Visual (`agents/vision_agent.py`)

El agente original impulsado por GPT-4o Vision estaba "copiando" a ciegas los conteos de líneas del CAD (ej. devolver 1,040 puertas basándose en las líneas detectadas) en lugar de contar visualmente en el PNG. 

**Mejoras implementadas:**
- **Prevención de Contaminación de Contexto:** Se eliminaron todos los conteos de objetos CAD (lines/polylines) del `context` enviado al LLM. Solo se envía como referencia la tabla NPT, áreas de *Hatches* y valores de cotas reales para escalar mentalmente el plano.
- **Instrucciones Visuales Explícitas:** Se añadieron anclajes morfológicos al prompt. 
  - *Puertas:* Buscar arco de apertura + marco.
  - *Ventanas:* Buscar líneas paralelas en muros exteriores.
- **Anclaje Cognitivo:** Se incluyó un baseline estadístico real de la Torre Giualca I (*~5 apartamentos, ~29 puertas, ~7 baños*) para que el modelo calibre su lectura óptica y no alucine miles de elementos.

---

## 3. Integración Estricta con Estándar PRESTO

La salida JSON arrojada por el LLM ha sido rigurosamente tuneada para encajar a la perfección con la Base de Datos BC3:

- **21 Disciplinas Hardcodeadas:** GPT-4o está ahora forzado a agrupar los hallazgos *únicamente* usando los nombres de capítulos exactos: *Hormigón Armado, Puertas, Instalación Eléctrica, Sistema de Agua Potable*, etc.
- **Categorización Granular de Elementos:**
  - El modelo separa visualmente: *Puerta Madera Roble Principal* vs *Puerta Madera Andiroba Interior* vs *Puerta Madera Closet*.
- **Unidades Forzadas:** 
  - `ud` (Unidades) para aparatología sanitaria, puertas batientes simples y electricidad.
  - `m2` para muros (descontando vanos mentalmente), pisos, pañete y pintura.
  - `p2` para puertas de closet tipo plegables o ventanas.
  - `m` (Milímetros) estimados espacialmente para tuberías.
- **Inferencia Heurística (Sistemas Ocultos):** El modelo ahora deduce infraestructura invisible basada en la cantidad de habitaciones observadas. Si detecta 5 apartamentos con múltiples baños, el modelo calcula matemáticamente la cantidad de tomacorrientes (ej. ~6 por habitación principal) y metros de tubería de drenaje.

---

## 4. Validación Computada Cruzada (Python-Side)

Se implementó una nueva función `run_cross_validation()` que se ejecuta **después** de que GPT-4o devuelve sus conteos visuales. 

La validación ya no recae en la IA, sino en una lógica algorítmica estricta:
1. Extrae las líneas totales de los layers `A-DOOR` y `A-GLAZ` del CAD subyacente.
2. Extrae las "puertas" y "ventanas" devueltas por el análisis visual bajo todas las disciplinas aplicables.
3. Divide las Líneas vs Objetos. Si hay unas ~50-70 líneas por puerta detectada, arroja un status de `"ok"`. Si arroja más o menos, tira un `"warning"`.

Esto garantiza que la IA no vuelva a engañar al sistema devolviendo outputs falsos contaminados por el prompt de metadatos.

---

## 5. Instrucciones de Ejecución del Pipeline

Dependiendo de la fase en la que te encuentres o los datos de entrada que tengas, puedes correr el pipeline de las siguientes maneras:

### A. Para procesar un JSON CRUDO del CAD (Autodesk Extract)
Si tienes el modelo original exportado y necesitas limpiar los layers, arreglar textos vacíos y extraer métricas geométricas antes de pasarlo a la IA:
```bash
python processors/json_processor.py
```
> **Qué hace:** Filtra la metadata inservible.\n> **Output generado:** `resumen_procesado.json` en la raíz del proyecto.

### B. Para probar el Vision Agent en un plano individual (Modo Test)
Si estás probando la extracción visual en una página particular (ej: `page_08.png`) para validar que las fórmulas Presto funcionen:
```bash
python agents/vision_agent.py
```
> **Qué hace:** Consume `resumen_procesado.json` y la imagen testeada, combinando ambas datas lógicas y visuales.\n> **Output generado:** `vision_test_result.json` (un preview exacto de lo que haría en lote).

### C. Para procesar el edificio COMPLETO en Lote (Producción)
Para procesar las 14 páginas PNG simultáneamente, debes instanciar la función `run_full_vision_analysis` dentro de tu enrutador principal (`run_full_analysis.py` o similar).
```python
import json
from agents.vision_agent import run_full_vision_analysis

# 1. Cargar la data CAD previamente depurada
with open("resumen_procesado.json", "r", encoding="utf-8") as f:
    json_summary = json.load(f)

# 2. Correr el agente por cada imagen PNG del directorio
directorio_imagenes = "_legacy/vision_output/pages"
resultados_totales = run_full_vision_analysis(directorio_imagenes, json_summary)

# 3. Guardar el presupuesto consolidado
with open("presupuesto_torre_completa.json", "w", encoding="utf-8") as out:
    json.dump(resultados_totales, out, indent=2, ensure_ascii=False)
```
> **Qué hace:** Itera por cada PNG, aplica el prompt dinámico (Planta, Elevación, o Sitio), corre la validación cruzada y consolida un mega-JSON listo para Excel o para importar al .BC3 real de Presto.
