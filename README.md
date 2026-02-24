# Dupla Hybrid CAD Analysis Pipeline 🏗️

Un sistema de análisis integral de presupuestos de obra que fusiona la extracción de datos nativos de CAD (AutoCAD/Civil 3D) con Inteligencia Artificial (GPT-4o) para generar presupuestos detallados, detección de interferencias (clashes) y cálculos automáticos basados en modelos constructivos.

## Funcionalidades Principales

1. **Lectura de Catálogos (BC3 y XLS):** Parsea bases de datos estándar de la industria (FIEBDC/BC3 de Presto) y presupuestos históricos en Excel para usarlos como fuente de aprendizaje de precios y partidas.
2. **Análisis Nativo de CAD (COM):** Se conecta directamente a la instancia activa de Civil 3D/AutoCAD y extrae dimensiones geométricas reales (áreas, longitudes, conteos) de miles de entidades clasificadas por capa.
3. **Detección de Clashes Híbrida:**
   - *Nativa:* Analiza intersecciones de *bounding boxes* entre disciplinas (Ej: Estructura vs Arquitectura).
   - *Visual (IA):* Analiza planos renderizados (PDF/PNG) mediante GPT-4o Vision para identificar conflictos lógicos.
4. **Presupuestación Asistida por IA:** Genera un presupuesto segmentado en 9 capítulos constructivos cruzando las mediciones nativas del CAD con las partidas del BC3, utilizando GPT-4o para el *matching* inteligente y estimación algorítmica.

## Arquitectura del Proyecto

```text
Dupla/
│
├── learning_input/          # 📥 Carpeta de aprendizaje: coloca aquí tus .bc3 y .xlsx
├── analysis_output/         # 📤 Resultados del análisis: presupuestos y reportes
│   └── dump/                # 💾 Carpeta de volcado: JSONs intermedios de diagnóstico
├── vision_output/           # 📸 Datos visuales: imágenes renderizadas para OCR/Clash
│   └── pdf_pages/           # 📄 Páginas PDF convertidas a PNG
│
├── run_full_analysis.py     # 🚀 Script Principal: Ejecuta el pipeline integral
├── cad_automation/          # ⚙️ Módulo core de automatización COM
│   ├── config.py            # Reglas de mapeo de capas (Discipline/Entity)
│   ├── models.py            # Clases de datos (BoundingBox, LayerStats)
│   └── engine.py            # Motor de conexión COM con AutoCAD
└── .env                     # 🔑 Contiene la clave de OpenAI (OPENAI_API_KEY)
```

## Requisitos Previos

- **Python 3.9+** instalado en tu sistema.
- **AutoCAD o Civil 3D** instalado (versiones 2021-2025 probadas). Debe estar **abierto y ejecutándose** durante el análisis.
- Una **clave de API de OpenAI** (con acceso a `gpt-4o`).

### Instalación de Dependencias

Ejecuta en tu terminal el siguiente comando para instalar las librerías necesarias:

```powershell
pip install pywin32 openai python-dotenv openpyxl
```

Configura tu archivo `.env` en la raíz del proyecto (`Dupla/.env`):
```text
OPENAI_API_KEY=tu_clave_api_sk_aqui...
```

## Guía de Uso Rápido

### 1. Preparar el Entorno
Abre **Civil 3D o AutoCAD** y carga el plano `.dwg` que deseas analizar (por ejemplo, el modelo completo de la torre). Asegúrate de no tener ningún comando activo en el CAD (presiona `ESC` un par de veces).

### 2. Alimentar el Sistema (Aprendizaje)
Copia tus bases de datos a la carpeta `learning_input/`. El sistema aprenderá de ellos:
- Archivos **BC3** (Exportados desde Presto).
- Archivos **XLS o XLSX** (Presupuestos en Excel).

### 3. Ejecutar el Pipeline
Abre una terminal en la carpeta raíz (`Dupla/`) y ejecuta:

```powershell
python run_full_analysis.py
```

### 4. ¿Qué ocurre durante la ejecución?
El pipeline (que puede tardar entre 5 y 15 minutos dependiendo del tamaño del CAD) ejecuta 5 fases consecutivas:
- **[Fase 1] Lectura:** Parsea el BC3 (cientos de partidas) y los presupuestos Excel.
- **[Fase 2] Análisis DWG:** Iteración profunda sobre el objeto COM extrayendo propiedades geométricas de todas las capas.
- **[Fase 3] Clashes:** Detección de interferencias físicas (Bounding Box) y análisis de visión si hay planos disponibles.
- **[Fase 4] IA Presupuestaria:** Solicita a GPT-4o que asigne códigos Presto a las cantidades CAD, dividido en 9 módulos lógicos (tierras, estructura, arquitectura, sanitarias, etc.).
- **[Fase 5] Consolidación:** Agrupa la data y genera los *outputs*.

### 5. Revisar los Resultados
Ve a la carpeta `analysis_output/`. Encontrarás:
- `ANALISIS_INTEGRAL_YYYYMMDD_HHMMSS.txt`: El reporte exhaustivo y legible para humanos con todos los cálculos y *clashes*.
- `ANALISIS_INTEGRAL_YYYYMMDD_HHMMSS.json`: Versión estructurada para exportación o bases de datos posteriores.
- `DWG_ANALYSIS_YYYYMMDD_HHMMSS.txt`: Desglose puramente técnico de lo encontrado en el CAD (sin precios).

## Mapeo de Capas (Cad Automation)
El éxito del matching depende de cómo estén nombradas las capas en el `.dwg`. El archivo `cad_automation/config.py` define los prefijos principales:
- `A-*`: Arquitectura (Muros, Pisos, Puertas)
- `S-*`: Estructura (Columnas, Vigas, Losas)
- `E-*`: Eléctrico
- `P-*`: Plomería/Sanitarios

## Solución de Problemas (Troubleshooting)

**Error `(-2147352567, 'Exception occurred.')` o `Failed to get the Document object`:**
Esto sucede si AutoCAD bloquea el puerto COM. 
- *Solución:* Ve a la ventana de AutoCAD, presiona `ESC` tres veces para asegurarte de que no haya ningún cuadro de diálogo ni comando a medias, y vuelve a ejecutar el script.

**Las partidas no se asignan correctamente:**
- Revisa que en el `learning_input/` el archivo BC3 contenga los precios correctos (`~C|...`). 
- Verifica que el modelo de AutoCAD esté dibujado en unidades de **Metros**.

---
*Desarrollado para la estimación y optimización integral de proyectos constructivos.*
