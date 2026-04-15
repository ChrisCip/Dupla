# Dupla — Especificación de Requisitos de Software (SRS)

**Versión:** 1.1
**Fecha:** 2026-04-11
**Estado:** Borrador

---

## 1. Introducción

### 1.1 Propósito

Dupla es un sistema de presupuestación y cuantificación de obra (quantity takeoff) orientado a flujos de trabajo en construcción hispanohablantes. El sistema procesa planos de construcción en formato DWG (vía Autodesk Platform Services) y conjuntos de PDF organizados por disciplina (vía análisis de visión con IA), para generar presupuestos de obra con trazabilidad completa de cada cantidad y precio unitario.

### 1.2 Alcance

El sistema cubre el ciclo completo desde la ingesta de planos hasta la exportación del presupuesto final:

- Ingesta y validación de archivos DWG (limpios, organizados por vistas/niveles)
- Ingesta de conjuntos de PDF clasificados por disciplina
- Motores de análisis especializados por disciplina (arquitectónico/terminaciones, estructural, eléctrico, sanitario)
- Cuantificación determinista con fórmulas trazables y cubicación detallada
- Sistema de precios unitarios compuestos con análisis de composición (no limitado a catálogo BC3)
- Composición jerárquica de presupuesto por capítulos
- Exportación a Excel y BC3/FIEBDC

### 1.3 Definiciones y acrónimos


| Término                             | Definición                                                                             |
| ----------------------------------- | -------------------------------------------------------------------------------------- |
| APS                                 | Autodesk Platform Services — plataforma cloud para procesamiento de archivos CAD       |
| BC3 / FIEBDC                        | Formato estándar español de intercambio de datos de construcción y presupuestos        |
| CAD Facts                           | Datos normalizados extraídos de archivos DWG vía Model Derivative                      |
| Cubicación                          | Cálculo volumétrico detallado de elementos constructivos                               |
| PRES                                | Plantilla de presupuesto de referencia (archivo Excel con historial)                   |
| Precio Unitario                     | Costo por unidad de medida, compuesto por materiales, mano de obra, equipos y overhead |
| Takeoff                             | Cuantificación/medición de una partida de obra                                         |
| LevelInventory                      | Modelo de datos que representa el inventario constructivo por nivel                    |
| Análisis de Precios Unitarios (APU) | Descomposición detallada del costo unitario de cada partida                            |
| Construcosto                        | Publicación periódica de costos de construcción en RD, por región y trimestre          |
| Pricing Snapshot                    | Archivo JSON con precios congelados para un proyecto específico                        |


### 1.4 Stack tecnológico


| Componente         | Tecnología                            |
| ------------------ | ------------------------------------- |
| Lenguaje principal | Python 3.10+                          |
| Plugin AutoCAD     | C# (.NET Framework 4.8)               |
| IA / Vision        | OpenAI GPT-4o, text-embedding-3-small |
| Plataforma CAD     | Autodesk Platform Services (REST API) |
| Exportación        | openpyxl (Excel), BC3/FIEBDC nativo   |
| PDF rendering      | PyMuPDF (fitz)                        |
| Persistencia       | Archivos (JSON, JSONL, NPZ, Excel)    |


---

## 2. Descripción general del sistema

### 2.1 Perspectiva del producto

Dupla es una herramienta de línea de comandos / librería Python que opera como pipeline batch. No es una aplicación web multi-usuario. Recibe archivos de planos como entrada y genera presupuestos de construcción como salida.

### 2.2 Usuarios del sistema

- Ingenieros presupuestistas de construcción
- Supervisores de obra
- Oficinas de presupuesto (contexto dominicano/hispanohablante)

### 2.3 Principios de diseño

- Los módulos activos son project-agnostic: no asumen datos de ningún proyecto específico
- La salida de visión es inventory-first, no discipline-first
- Cada cantidad lleva fórmula trazable y metadata de auditoría obligatoria
- COM/AutoCAD automation es legacy y no se usa en el flujo activo
- La volumetría debe ser precisa y detallada, especialmente en estructura y terminaciones
- Los precios unitarios deben ser compuestos y desglosables, no solo valores planos

---

## 3. Requisitos de entrada

### 3.1 Entrada de archivos DWG

#### RF-DWG-01: Requisitos de limpieza

Los archivos DWG deben cumplir las siguientes condiciones antes de ser procesados:

- **Sin ruido**: Los DWG no deben contener layers basura, bloques no-constructivos residuales, xrefs rotos, ni geometría de borrador que contamine la extracción.
- **Layers significativos**: Cada layer debe contener información constructiva real. Layers de ayuda temporal, marcos de impresión, y anotaciones no-constructivas deben estar eliminados o en layers claramente identificables como no-constructivos.
- **Sin geometría duplicada**: No debe haber entidades superpuestas que dupliquen mediciones.

#### RF-DWG-02: Organización por vistas y niveles

Los DWG deben estar organizados de una de estas dos formas:

**Opción A — Vista por nivel (preferida):**
Cada nivel del edificio está en una vista (layout/viewport) separada dentro del DWG. El sistema extrae propiedades por vista y genera un `LevelInventory` independiente por cada una.

**Opción B — Todo en Model Space:**
Todos los niveles están en Model Space pero con separación clara:

- Layers con nomenclatura que identifique el nivel (ej. `N1-MUROS`, `N2-MUROS`)
- O separación espacial clara con textos identificadores de nivel

#### RF-DWG-03: Flujo de procesamiento

```text
DWG limpio
  → Upload a APS (OSS)
  → Model Derivative (traducción a JSON, vistas 2D)
  → Extracción de propiedades por vista/GUID
  → json_processor.py → CAD Facts normalizados
     (layers, texts, dimensions, hatches, blocks, geometry_hints)
  → Validación de calidad del DWG
```

#### RF-DWG-04: Validación pre-procesamiento

El sistema debe validar antes de procesar:


| Validación                                                                     | Acción si falla                |
| ------------------------------------------------------------------------------ | ------------------------------ |
| DWG tiene al menos 1 vista con geometría extractable                           | Rechazar con error             |
| Layers no son 100% de anotación/ruido                                          | Warning + continuar con subset |
| Geometría tiene dimensiones en rango razonable (no nanométrica ni kilométrica) | Warning + excluir outliers     |
| Bloques referenciados existen                                                  | Warning por bloques rotos      |


### 3.2 Entrada de archivos PDF por disciplina

#### RF-PDF-01: Clasificación por disciplina

El usuario debe proveer un conjunto de PDFs clasificados por disciplina. El sistema enruta cada PDF al motor de análisis especializado correspondiente:


| Disciplina                         | Archivos esperados                                                           | Motor destino        |
| ---------------------------------- | ---------------------------------------------------------------------------- | -------------------- |
| **Arquitectónico / Terminaciones** | Plantas arquitectónicas, cortes, elevaciones, detalles de acabados           | Motor Arquitectónico |
| **Estructural**                    | Plantas estructurales, cuadros de columnas/vigas/zapatas, detalles de armado | Motor Estructural    |
| **Eléctrico**                      | Plantas eléctricas, diagramas unifilares, cuadros de carga                   | Motor Eléctrico      |
| **Sanitario**                      | Plantas sanitarias, isométricos, detalles de conexiones                      | Motor Sanitario      |


#### RF-PDF-02: Procesamiento de PDFs

```text
PDF por disciplina
  → PyMuPDF render a imágenes (200 DPI, cache por hash)
  → Detección de tipo de plano (planta, corte, elevación, detalle, diagrama)
  → Enrutamiento al motor de visión especializado por disciplina
  → Inventario parcial por disciplina
  → Merge con inventario CAD → inventario híbrido unificado
```

#### RF-PDF-03: Metadatos requeridos por PDF

Cada PDF debe acompañarse de:

- **Disciplina**: arquitectónico | estructural | eléctrico | sanitario
- **Nivel(es) cubierto(s)** (opcional): si el PDF cubre un nivel específico o es general
- **Tipo de vista** (opcional): planta | corte | elevación | detalle | diagrama

---

## 4. Motores de análisis por disciplina

### 4.1 Motor Arquitectónico / Terminaciones

#### RF-ARQ-01: Elementos a extraer


| Categoría              | Elementos                                                                 | Mediciones requeridas                                                                    |
| ---------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Muros**              | Tipo (bloque 6", 8", 4", concreto, drywall), ubicación (int/ext)          | Longitud (m), altura (m), espesor (m), área bruta (m²), área neta (m²) descontando vanos |
| **Acabados de muros**  | Pañete/revoque, pintura, cerámica, papel tapiz                            | Área por cara (m²), tipo de acabado, número de caras                                     |
| **Pisos**              | Tipo de acabado por zona (porcelanato, cerámica, mármol, terrazo, vinilo) | Área por tipo (m²), perímetro de zócalo (m)                                              |
| **Cielos**             | Tipo (yeso, suspendido, expuesto, madera)                                 | Área (m²), tipo de sistema                                                               |
| **Puertas**            | Tipo (principal, interior, baño, servicio, closet), material              | Cantidad, dimensiones (ancho × alto), marco, herrajes                                    |
| **Ventanas**           | Tipo (corrediza, fija, celosía, proyectante), material, vidrio            | Cantidad, dimensiones, tipo de vidrio                                                    |
| **Impermeabilización** | Áreas húmedas (pisos y muros), cubiertas                                  | Área (m²), tipo de membrana, altura en muros                                             |
| **Carpintería**        | Closets, muebles de cocina (sup/inf), topes                               | Cantidad, metro lineal, material                                                         |


#### RF-ARQ-02: Casos particulares de terminaciones

El motor de terminaciones debe manejar estos casos con detalle:

- **Acabado diferenciado por zona**: Un mismo nivel puede tener porcelanato en sala, cerámica en baños, y terrazo en áreas de servicio. El motor debe identificar y cuantificar por separado.
- **Muros con doble acabado**: Cara interior pañete + pintura, cara exterior pañete + pintura exterior. Cada cara se cuenta por separado.
- **Muros de áreas húmedas**: Cerámica hasta cierta altura (típicamente 1.80m o 2.10m en duchas) + pintura el resto. El motor debe distinguir la porción cerámica vs pintura.
- **Zócalos y remates**: Metro lineal de zócalo por tipo de piso.
- **Goterones y botaguas**: En ventanas y elementos salientes exteriores.
- **Juntas de dilatación**: En pisos de áreas grandes.

### 4.2 Motor Estructural

#### RF-EST-01: Elementos a extraer y cubicar


| Elemento            | Mediciones de cubicación                                                                                                        |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Columnas**        | Sección (ancho × alto), longitud/altura, volumen de hormigón (m³), área de encofrado (m²), peso de acero (kg) por tipo de barra |
| **Vigas**           | Sección (ancho × alto), luz/longitud, volumen de hormigón (m³), encofrado (2 lados + fondo), acero por diámetro                 |
| **Losas**           | Espesor, área (m²), volumen de hormigón (m³), encofrado inferior (m²), acero (malla + bastones)                                 |
| **Zapatas**         | Tipo (aislada, corrida, combinada), dimensiones, volumen (m³), acero, encofrado lateral                                         |
| **Muros de corte**  | Espesor, altura, longitud, volumen (m³), acero horizontal + vertical                                                            |
| **Dinteles**        | Sección, longitud, volumen, acero                                                                                               |
| **Vigas de amarre** | Sección, perímetro, volumen, acero                                                                                              |
| **Escaleras**       | Espesor de losa, huella, contrahuella, ancho, desarrollo, volumen (m³)                                                          |


#### RF-EST-02: Volumetría detallada — Hormigón armado

La cubicación de hormigón debe ser precisa y considerar:

- **Volumen neto**: Descontar intersecciones entre elementos (ej. donde una viga se encuentra con una columna, no contar el volumen dos veces).
- **Tipo de hormigón**: Identificar f'c (210, 250, 280 kg/cm²) por elemento cuando esté especificado en los planos.
- **Vaciados separados**: Zapatas, columnas hasta losa, vigas + losa se vacían por separado — la cubicación debe reflejar esto.
- **Bloques de relleno en losas**: Las losas nervadas tienen bloques de poliestireno o cerámicos que reducen el volumen de hormigón real.

#### RF-EST-03: Volumetría detallada — Acero de refuerzo

El cálculo de acero NO debe usar ratios genéricos (kg/m³) como valor final. Debe:

- **Leer el despiece del plano** cuando esté disponible: diámetros (#3, #4, #5, #6, #8), longitudes de barra, cantidad, ganchos, traslapes.
- **Calcular peso por diámetro**: Usar tabla de pesos lineales estándar (ej. #3 = 0.560 kg/m, #4 = 0.994 kg/m, #5 = 1.552 kg/m, #6 = 2.235 kg/m, #8 = 3.973 kg/m).
- **Incluir factor de desperdicio**: Típicamente 5-8% en barras, 10-12% en malla.
- **Incluir traslapes**: Longitud de desarrollo según diámetro y f'c del hormigón.
- **Separar acero longitudinal y estribos/ligaduras** en vigas y columnas.
- **Malla electrosoldada en losas**: Tipo de malla (ej. 6×6-10/10) con su peso por m².

> **Nota sobre estado actual:** El cuantificador actual usa ratios fijos (vigas=100 kg/m³, columnas=120, losas=80, zapatas=60). Estos valores son aceptables como **estimación preliminar** pero el SRS exige que se implementen cálculos detallados por despiece como capacidad objetivo.

#### RF-EST-04: Encofrado

- **Vigas**: 2 laterales + fondo (excluye cara superior). Fórmula: `(2 × h + b) × L`
- **Columnas**: 4 caras. Fórmula: `2 × (b + h) × L`
- **Losas**: Cara inferior + costillas laterales si aplica.
- **Zapatas**: Lateral solamente. Perímetro × profundidad.
- **Incluir** puntales, parales, tablero de fondo para losas como partidas relacionadas.

#### RF-EST-05: Casos particulares estructurales

- **Columnas con capiteles**: Volumen adicional del capitel como partida separada.
- **Vigas con cartelas**: Volumen del ensanche como adición.
- **Losas inclinadas** (rampas, escaleras): Calcular espesor perpendicular al plano, no vertical.
- **Muros de sótano/contención**: Empuje lateral → mayor cuantía de acero, impermeabilización exterior.
- **Uniones viga-columna (nudos)**: Confinamiento adicional de estribos en nudos sísmicos.

### 4.3 Motor Eléctrico

#### RF-ELE-01: Elementos a extraer


| Categoría           | Elementos                                                                                               | Medición                                             |
| ------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| **Puntos de uso**   | Tomacorrientes (110V, 220V), interruptores (sencillo/doble/triple/dimmer), salidas de datos/TV/teléfono | Cantidad por tipo y circuito                         |
| **Luminarias**      | Techo, pared, empotrada, exterior, emergencia                                                           | Cantidad por tipo                                    |
| **Cableado**        | Por calibre (AWG 12, 10, 8, 6, 4, 2) y tipo (THHN, THWN)                                                | Longitud (m) por calibre, incluyendo subidas/bajadas |
| **Tubería conduit** | EMT, PVC eléctrico, por diámetro (½", ¾", 1", 1¼")                                                      | Longitud (m) por diámetro                            |
| **Paneles**         | Panel principal, subpaneles, capacidad (circuitos, amperaje)                                            | Cantidad por tipo                                    |
| **Breakers**        | Por capacidad (15A, 20A, 30A, 40A, 50A, etc.)                                                           | Cantidad por tipo                                    |
| **Acometida**       | Tipo, calibre, longitud desde medidor                                                                   | Longitud, calibre                                    |
| **Puesta a tierra** | Varilla, cable, conexiones                                                                              | Cantidad y longitud                                  |
| **Detectores**      | Humo, CO, movimiento                                                                                    | Cantidad por tipo                                    |
| **Especiales**      | Abanicos de techo, conexión A/C, timbre, intercomunicador                                               | Cantidad por tipo                                    |


#### RF-ELE-02: Casos particulares eléctricos

- **Recorrido de tubería**: El motor debe estimar longitudes de tubería y cableado basándose en distancias en planta + subidas/bajadas (típicamente se agrega 10-15% para verticales y curvas).
- **Circuitos**: Identificar circuitos separados (iluminación, tomacorrientes, A/C, cocina) con su cableado independiente.
- **Carga por circuito**: Para dimensionamiento de breakers y calibre de cable.
- **Cajas de conexión**: Cantidad basada en número de derivaciones.

### 4.4 Motor Sanitario

#### RF-SAN-01: Elementos a extraer


| Categoría                | Elementos                                                       | Medición                                                 |
| ------------------------ | --------------------------------------------------------------- | -------------------------------------------------------- |
| **Red de agua fría**     | Tuberías por diámetro (½", ¾", 1"), material (PVC, CPVC, cobre) | Longitud (m) por diámetro y material                     |
| **Red de agua caliente** | Tuberías por diámetro, material (CPVC, cobre)                   | Longitud (m) por diámetro                                |
| **Red de drenaje**       | Tuberías por diámetro (2", 3", 4", 6"), material (PVC)          | Longitud (m) por diámetro                                |
| **Ventilación**          | Tuberías de ventilación por diámetro                            | Longitud (m)                                             |
| **Piezas sanitarias**    | Inodoro, lavamanos, ducha, bañera, bidet, urinario, fregadero   | Cantidad por tipo y calidad (estándar/premium/económico) |
| **Válvulas**             | Llaves de paso, check, reguladoras                              | Cantidad por tipo y diámetro                             |
| **Registros**            | Registros de piso, pared, limpieza                              | Cantidad por tipo                                        |
| **Equipos**              | Calentador de agua, cisterna, bomba, tanque presurizado         | Cantidad y capacidad                                     |
| **Drenaje pluvial**      | Bajantes, canales, desagües de techo                            | Longitud y cantidad                                      |


#### RF-SAN-02: Casos particulares sanitarios

- **Puntos de agua**: Cada pieza sanitaria tiene puntos de agua fría (y caliente si aplica) que requieren acometida con su válvula y tubería.
- **Trampas**: Cada desagüe requiere trampa (P-trap o S-trap) como partida independiente.
- **Pendientes de drenaje**: Las tuberías de drenaje tienen pendiente mínima (1-2%) que afecta la longitud real vs horizontal.
- **Conexión a red pública**: Punto de conexión, tubería de acometida, llave de registro.
- **Sistema de bombeo**: Si hay cisterna, incluir bomba, tubería de succión/descarga, tablero de control, flotadores.

---

## 5. Sistema de precios unitarios

### 5.1 Problemática del catálogo BC3

#### RF-PU-01: Limitaciones del BC3 como fuente de precios

El formato BC3/FIEBDC exportado desde Presto presenta las siguientes limitaciones:

1. **Precios planos**: El registro `~C` del BC3 contiene el **precio final** del concepto, no necesariamente la descomposición completa de cómo se compone ese precio.
2. **Descomposición parcial**: El registro `~D` contiene la jerarquía padre-hijo con factores y rendimientos, pero depende de cómo se haya configurado la exportación en Presto. Puede venir completa, parcial, o vacía.
3. **Catálogo cerrado**: El presupuesto queda limitado a las partidas que existan en el BC3 cargado. Si una partida identificada en los planos no tiene equivalente en el catálogo, queda sin precio o con un match aproximado.
4. **Sin fórmulas de cubicación**: El BC3 no contiene las fórmulas usadas para calcular cantidades — solo los valores resultantes en los registros `~M` (mediciones).
5. **Precios desactualizados**: Los precios del BC3 son una fotografía del momento de la exportación y no se actualizan automáticamente.

#### RF-PU-02: Estrategia de precios unitarios propuesta

El sistema debe soportar un enfoque híbrido de precios unitarios:

**Nivel 1 — Análisis de Precios Unitarios (APU) propios:**
Cada partida debe poder tener su APU descompuesto en:


| Componente       | Descripción                                                                   |
| ---------------- | ----------------------------------------------------------------------------- |
| **Materiales**   | Lista de materiales con cantidad, unidad, precio unitario, desperdicio        |
| **Mano de obra** | Categorías (maestro, oficial, ayudante), rendimiento (jornada/unidad), jornal |
| **Equipos**      | Tipo de equipo, rendimiento, costo horario                                    |
| **Transporte**   | Flete de materiales si aplica                                                 |
| **Overhead**     | Gastos generales, administración, utilidad (%)                                |


**Nivel 2 — BC3 como referencia secundaria:**
El catálogo BC3 se usa como:

- Fuente de referencia para precios cuando no hay APU propio
- Validación cruzada contra precios calculados por APU
- Base de datos de descripciones/resúmenes estándar de partidas

**Nivel 3 — Precios históricos (PRES):**
El archivo PRES.xlsx de referencia se usa como:

- Fuente de training pairs para matching de partidas similares
- Referencia de precios de proyectos anteriores
- Base para estimaciones rápidas cuando no hay APU ni BC3

#### RF-PU-03: Estructura del APU

Cada precio unitario compuesto debe tener esta estructura:

```text
PARTIDA: Hormigón armado en columnas f'c=210 kg/cm²
UNIDAD: m³
────────────────────────────────────────────────────
MATERIALES
  Cemento Portland tipo I       8.50 sacos × $XXX    = $XXX
  Arena lavada                  0.55 m³   × $XXX    = $XXX
  Grava ¾"                     0.75 m³   × $XXX    = $XXX
  Agua                         0.19 m³   × $XXX    = $XXX
  Subtotal materiales                                = $XXX
  Desperdicio (5%)                                   = $XXX

MANO DE OBRA
  Maestro albañil              0.15 jorn  × $XXX    = $XXX
  Oficial                      0.50 jorn  × $XXX    = $XXX
  Ayudante                     1.00 jorn  × $XXX    = $XXX
  Subtotal mano de obra                              = $XXX

EQUIPOS
  Mezcladora 1 saco            0.25 hora  × $XXX    = $XXX
  Vibrador de concreto         0.25 hora  × $XXX    = $XXX
  Subtotal equipos                                   = $XXX

SUBTOTAL DIRECTO                                     = $XXX
Gastos generales (12%)                               = $XXX
Utilidad (8%)                                        = $XXX
ITBIS (18%)                                          = $XXX
────────────────────────────────────────────────────
PRECIO UNITARIO TOTAL                                = $XXX
```

### 5.2 Precios por disciplina

#### RF-PU-04: Precios unitarios estructurales

Las partidas estructurales requieren APUs particularmente detallados porque la volumetría es crítica:

- **Hormigón**: Precio por m³ varía según f'c. La dosificación cambia (más cemento para mayor resistencia).
- **Acero**: Precio por kg varía según diámetro (las barras más gruesas tienen mayor precio por kg por el proceso de fabricación). Incluir alambre de amarre como porcentaje.
- **Encofrado**: Precio por m² varía según tipo (madera vs metálico), reutilizaciones esperadas, y complejidad (losa plana vs nervada vs irregular).
- **Aditivos**: Retardantes, acelerantes, plastificantes — se usan según condiciones del proyecto.

#### RF-PU-05: Precios unitarios de terminaciones

Las terminaciones tienen la mayor variabilidad de precios:

- **Pisos**: El porcelanato importado puede costar 10× más que la cerámica nacional. El sistema debe permitir especificar calidad/marca.
- **Pintura**: Distinguir entre primera mano (sellador), manos de acabado, tipo de pintura (mate, satinada, semi-brillo), marca.
- **Pañete**: Distinguir pañete de base (grueso) vs fino. Maestro vs repello.
- **Impermeabilización**: Membrana líquida vs lámina asfáltica vs manta geotextil — precios y rendimientos muy diferentes.

#### RF-PU-06: Precios unitarios eléctricos

- **Cableado**: Precio por metro incluyendo tubería, cable, fijaciones. Varía mucho por calibre.
- **Puntos**: Cada punto eléctrico es un APU compuesto (caja, tubería, cable, placa, dispositivo).
- **Panel + breakers**: Como conjunto instalado.

#### RF-PU-07: Precios unitarios sanitarios

- **Tuberías**: Precio por metro lineal incluyendo accesorios (codos, tees, reducciones) como porcentaje (típicamente 15-25% del costo de tubería recta).
- **Piezas sanitarias**: Precio incluyendo instalación, accesorios de conexión, sellado.
- **Equipos**: Cisterna, bomba, calentador — incluir instalación y conexiones.

### 5.3 Fuente de datos: Construcosto

#### RF-PU-08: Archivos de referencia de Construcosto

La fuente primaria de precios de mercado es **Construcosto** (publicación periódica de costos de construcción en República Dominicana). Construcosto publica **4 archivos** por periodo y por región, y los 4 son requeridos:


| Archivo                                                   | Contenido                                                                                                                                      | Rol en Dupla                                                                                                                                                                    |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Materiales e Insumos para la Construcción**             | Precios de mercado de todos los insumos: cemento, arena, grava, bloques, acero, cerámica, cables, tuberías, pintura, madera, etc.              | **Catálogo base de insumos**. Sin este archivo no se puede armar ningún APU. Es la fuente de precios unitarios de cada material individual.                                     |
| **Mano de Obra para la Construcción**                     | Jornales por categoría de trabajador: maestro albañil, oficial, ayudante, plomero, electricista, soldador, operador de equipos, etc.           | **Componente de mano de obra** de cada APU. Define cuánto cuesta la labor por jornada para cada especialidad.                                                                   |
| **Análisis de Costos para la Construcción**               | APUs ya armados: descomposición completa de cada partida constructiva en materiales + mano de obra + equipos con cantidades y rendimientos     | **APUs de referencia** listos para usar. Son la base principal del presupuesto. Cada APU referencia insumos del catálogo de materiales y jornales del catálogo de mano de obra. |
| **Análisis de Costos de Equipos y Movimientos de Tierra** | Costos horarios de equipos (retroexcavadora, grúa, bomba, mixer, compactador, camión) + partidas de excavación, relleno, compactación, acarreo | **Componente de equipos** de cada APU + partidas de **movimiento de tierra** (excavación, relleno, compactación) que no están en los otros 3 archivos.                          |


#### RF-PU-09: Relación entre los 4 archivos

Los archivos de Construcosto tienen una relación jerárquica:

```text
ANÁLISIS DE COSTOS (APU completo por partida)
  ├── referencia precios de → MATERIALES E INSUMOS
  ├── referencia jornales de → MANO DE OBRA
  └── referencia costos de  → EQUIPOS Y MOVIMIENTOS DE TIERRA
```

Los 4 son necesarios porque:

1. **Los APUs ya armados** (Análisis de Costos) sirven como referencia directa cuando la partida coincide con lo que Construcosto publica.
2. **El catálogo de materiales** permite actualizar precios individualmente — si sube el cemento, se actualiza un solo insumo y todos los APUs que lo usan se recalculan.
3. **Los jornales de mano de obra** permiten crear APUs custom para partidas que Construcosto no cubre, usando los rendimientos por categoría de trabajador.
4. **Los costos de equipos** alimentan el componente de equipos de los APUs y cubren las partidas de movimiento de tierra que son independientes de las otras disciplinas.

#### RF-PU-10: Regionalización de precios

Construcosto publica precios **por región geográfica** (Santo Domingo, Punta Cana, Santiago, etc.). Los precios varían entre regiones por diferencias en fletes, disponibilidad de materiales, y costos de mano de obra local.

El sistema debe:

- Registrar la **región** como metadata obligatoria del snapshot de precios
- Permitir cargar archivos de Construcosto de cualquier región
- Advertir si la región del snapshot no coincide con la ubicación del proyecto
- No mezclar precios de diferentes regiones en un mismo presupuesto sin advertencia explícita

### 5.4 Persistencia de precios — Estrategia stateless con snapshots

#### RF-PU-11: Arquitectura stateless con pricing snapshots

Dado que Dupla es un pipeline stateless (archivos entran, archivos salen), los precios se manejan como **snapshots congelados por proyecto**:

```text
proyecto_torre_x/
├── planos/
│   ├── arquitectonico.pdf
│   ├── estructural.pdf
│   ├── electrico.pdf
│   └── sanitario.pdf
├── dwg/
│   └── planta_tipo.dwg
├── pricing_snapshot.json    ← precios congelados para ESTE proyecto
├── apus_override.json       ← APUs custom si el proyecto requiere algo especial
└── output/
    ├── presupuesto.xlsx
    └── presupuesto.bc3
```

#### RF-PU-12: Catálogo maestro vs. snapshot de proyecto

El sistema opera con dos niveles de datos de precios:

**Nivel 1 — Catálogo maestro (compartido):**
Repositorio central con los datos importados de Construcosto, organizado por periodo y región:

```text
data/
└── pricing/
    ├── construcosto/
    │   ├── 2026_Q1_santo_domingo/
    │   │   ├── materiales_insumos.json
    │   │   ├── mano_obra.json
    │   │   ├── analisis_costos.json
    │   │   └── equipos_mov_tierra.json
    │   ├── 2026_Q1_punta_cana/
    │   │   ├── materiales_insumos.json
    │   │   ├── mano_obra.json
    │   │   ├── analisis_costos.json
    │   │   └── equipos_mov_tierra.json
    │   └── 2026_Q2_santo_domingo/
    │       └── ...
    └── custom_apus/
        ├── estructura.json
        ├── terminaciones.json
        ├── electrico.json
        └── sanitario.json
```

**Nivel 2 — Snapshot de proyecto (congelado):**
Al iniciar un presupuesto, se genera un snapshot que congela los precios para ese proyecto:

```text
python -m dupla.pricing snapshot \
    --source data/pricing/construcosto/2026_Q1_santo_domingo/ \
    --custom-apus data/pricing/custom_apus/ \
    --output proyecto_torre_x/pricing_snapshot.json \
    --region "santo_domingo" \
    --date "2026-04-10"
```

#### RF-PU-13: Estructura del pricing snapshot

```json
{
  "metadata": {
    "source": "construcosto",
    "period": "2026_Q1",
    "region": "santo_domingo",
    "snapshot_date": "2026-04-10",
    "currency": "RD$",
    "construcosto_files": [
      "materiales_insumos.json",
      "mano_obra.json",
      "analisis_costos.json",
      "equipos_mov_tierra.json"
    ]
  },
  "insumos": {
    "hormigon_premezclado_210": {
      "descripcion": "Hormigón 210 Kg/cm2 (incluye bomba y colocación)",
      "unidad": "m3",
      "precio": 7330.51,
      "precio_bruto": 8650.00,
      "fuente": "construcosto_materiales"
    },
    "cemento_gris": {
      "descripcion": "Cemento Portland Gris",
      "unidad": "fda",
      "precio": 461.86,
      "fuente": "construcosto_materiales"
    },
    "arena_itabo_gruesa": {
      "descripcion": "Arena Itabo gruesa lavada",
      "unidad": "m3",
      "precio": 1449.15,
      "fuente": "construcosto_materiales"
    },
    "grava_3_4": {
      "descripcion": "Grava 3/4\"",
      "unidad": "m3",
      "precio": 1398.31,
      "fuente": "construcosto_materiales"
    }
  },
  "mano_obra": {
    "maestro_albañil": {"jornal": 2500.00, "unidad": "dia", "fuente": "construcosto_mo"},
    "oficial": {"jornal": 1800.00, "unidad": "dia", "fuente": "construcosto_mo"},
    "ayudante": {"jornal": 1200.00, "unidad": "dia", "fuente": "construcosto_mo"},
    "plomero": {"jornal": 2200.00, "unidad": "dia", "fuente": "construcosto_mo"},
    "electricista": {"jornal": 2200.00, "unidad": "dia", "fuente": "construcosto_mo"}
  },
  "equipos": {
    "bombeado_hormigon": {
      "descripcion": "Bombeado y colocación de hormigón",
      "unidad": "m3",
      "precio": 2700.00,
      "fuente": "construcosto_equipos"
    },
    "instalacion_bomba": {
      "descripcion": "Instalación de bomba en sitio",
      "unidad": "ud",
      "precio": 14580.00,
      "fuente": "construcosto_equipos"
    }
  },
  "apus": {
    "hormigon_simple_1_3_5_ligadora": {
      "codigo": "102.02",
      "descripcion": "Hormigón 1:3:5 con ligadora",
      "unidad": "m3",
      "fuente": "construcosto_analisis",
      "componentes": [
        {"tipo": "material", "insumo_key": "cemento_gris", "cantidad": 6.50, "unidad": "fda"},
        {"tipo": "material", "insumo_key": "arena_itabo_gruesa", "cantidad": 0.52, "unidad": "m3"},
        {"tipo": "material", "insumo_key": "grava_3_4", "cantidad": 0.86, "unidad": "m3"},
        {"tipo": "material", "insumo_key": "agua", "cantidad": 60.0, "unidad": "gl"},
        {"tipo": "mano_obra", "descripcion": "Ligado y vaciado con ligadora", "cantidad": 1.0, "unidad": "m3", "precio": 1018.48}
      ],
      "subtotal_materiales": 6066.68,
      "subtotal_mano_obra": 966.43,
      "subtotal_equipos": 0.0,
      "total": 7033.11
    }
  },
  "overrides": {}
}
```

#### RF-PU-14: Flujo de resolución de precios en el pipeline

Cuando el pipeline necesita asignar un precio a una partida cuantificada:

```text
1. ¿Existe APU override en el proyecto?     → Usar override
2. ¿Existe APU en el snapshot (Construcosto)? → Usar APU de Construcosto
3. ¿Existe match BC3 con score alto?          → Usar precio del BC3
4. ¿Existe partida similar en PRES?           → Usar precio histórico de PRES
5. Ninguna de las anteriores                  → Marcar como "precio pendiente"
```

Cada precio asignado lleva metadata de su fuente:


| Campo              | Descripción                                                                                                 |
| ------------------ | ----------------------------------------------------------------------------------------------------------- |
| `price_source`     | `apu_override` / `construcosto_apu` / `construcosto_insumo` / `bc3_catalog` / `pres_historical` / `pending` |
| `price_confidence` | Alto (APU propio/Construcosto), Medio (BC3), Bajo (PRES/estimación)                                         |
| `price_region`     | Región del precio aplicado                                                                                  |
| `price_period`     | Periodo de referencia del precio                                                                            |


#### RF-PU-15: Ventajas de la estrategia stateless con snapshots

- **Reproducibilidad**: Correr el mismo proyecto meses después produce el mismo resultado con el snapshot original
- **Independencia**: Cada proyecto es auto-contenido, no depende de base de datos externa
- **Override por proyecto**: Si un cliente tiene precios negociados con un proveedor, se modifica el snapshot sin afectar otros proyectos
- **Auditoría**: El snapshot es un archivo JSON versionable que documenta exactamente qué precios se usaron
- **Migración futura**: Si Dupla evoluciona a webapp, el catálogo maestro migra a base de datos sin cambiar el pipeline

---

## 6. Cuantificación y trazabilidad

### 6.1 Principios de cuantificación

#### RF-QTY-01: Trazabilidad obligatoria

Cada cantidad generada debe llevar:


| Campo         | Descripción                                                                |
| ------------- | -------------------------------------------------------------------------- |
| `item_key`    | Identificador único de la medición                                         |
| `item_type`   | Tipo de partida (wall_net_area, beam_concrete_volume, etc.)                |
| `unit`        | Unidad de medida (m, m², m³, kg, unit)                                     |
| `quantity`    | Valor numérico calculado                                                   |
| `formula`     | Fórmula textual reproducible                                               |
| `inputs`      | Diccionario con todos los valores de entrada usados                        |
| `assumptions` | Lista de suposiciones aplicadas (dimensiones asumidas, defaults)           |
| `trace`       | Origen: entity IDs fuente, pasos de cálculo, evidencia, notas de conflicto |


#### RF-QTY-02: Jerarquía de fuentes de datos

Cuando hay datos disponibles de múltiples fuentes:

1. **Dato explícito del plano** (cota, dimensión leída) → prioridad máxima
2. **Dato de CAD** (extraído de DWG vía APS) → prioridad alta
3. **Dato de visión** (inferido por GPT-4o del PDF) → prioridad media
4. **Default del sistema** (dimensiones estándar) → prioridad baja, siempre documentado como assumption

#### RF-QTY-03: Detalles de cubicación por disciplina

**Muros:**

```
Área bruta = longitud × altura
Área neta  = área bruta - Σ(áreas de vanos)
Volumen    = longitud × altura × espesor
Acabado    = área neta × caras (1 o 2 según interior/exterior)
```

**Hormigón armado:**

```
Volumen viga    = luz × ancho_sección × alto_sección
Volumen columna = altura_entrepiso × ancho × profundidad
Volumen losa    = área × espesor (ajustar por nervaduras si aplica)
Volumen zapata  = largo × ancho × profundidad
```

**Acero de refuerzo (detallado):**

```
Peso barra = (longitud_corte + 2×gancho + traslape) × peso_lineal[diámetro]
Peso total = Σ(cantidad × peso_barra) × (1 + factor_desperdicio)
Alambre    = 2-3% del peso total de acero
```

**Encofrado:**

```
Viga:    (2×alto + ancho_fondo) × longitud
Columna: 2×(ancho + profundidad) × altura
Losa:    área inferior (+ laterales de nervaduras si nervada)
Zapata:  perímetro × profundidad
```

---

## 7. Arquitectura del pipeline

### 7.1 Flujo general

```text
                         ┌──────────────┐
                         │   USUARIO    │
                         └──────┬───────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                  ▼
       ┌────────────┐   ┌────────────┐    ┌─────────────┐
       │   DWGs     │   │  PDFs por  │    │  Precios    │
       │  (limpios) │   │ Disciplina │    │  (APU/BC3/  │
       └─────┬──────┘   └─────┬──────┘    │   PRES)     │
             │                │           └──────┬──────┘
             ▼                ▼                   │
       ┌───────────┐   ┌──────────────┐          │
       │ Validador │   │ Router de    │          │
       │ DWG       │   │ Disciplina   │          │
       │ (limpieza │   └──┬──┬──┬──┬──┘          │
       │  + vistas)│      │  │  │  │             │
       └─────┬─────┘      │  │  │  │             │
             │            ▼  ▼  ▼  ▼             │
             │      ┌────┐┌───┐┌───┐┌────┐       │
             │      │ARQ ││EST││ELE││SAN │       │
             │      │    ││   ││   ││    │       │
             │      └──┬─┘└─┬─┘└─┬─┘└──┬─┘       │
             │         └──┬─┘    └──┬──┘         │
             ▼            ▼         ▼             │
       ┌───────────┐  ┌─────────────────┐        │
       │ APS/Model │  │ Inventarios     │        │
       │ Derivative│  │ por disciplina  │        │
       │ → CAD     │  └────────┬────────┘        │
       │   Facts   │           │                 │
       └─────┬─────┘           │                 │
             │                 │                 │
             └────────┬────────┘                 │
                      ▼                          │
            ┌──────────────────┐                 │
            │ Inventario       │                 │
            │ Híbrido Unificado│                 │
            │ (por nivel)      │                 │
            └────────┬─────────┘                 │
                     ▼                           │
            ┌──────────────────┐                 │
            │ Cuantificadores  │                 │
            │ por disciplina   │                 │
            │ (fórmulas        │                 │
            │  específicas)    │                 │
            └────────┬─────────┘                 │
                     ▼                           │
            ┌──────────────────┐                 │
            │ Motor de reglas  │                 │
            │ (expansión de    │                 │
            │  partidas        │                 │
            │  derivadas)      │                 │
            └────────┬─────────┘                 │
                     ▼                           ▼
            ┌────────────────────────────────────────┐
            │  Matching de partidas contra precios   │
            │  (APU propio → BC3 → PRES → genérico)  │
            └────────────────┬───────────────────────┘
                             ▼
            ┌──────────────────────────┐
            │  Composición de          │
            │  presupuesto por         │
            │  capítulos               │
            └───────────┬──────────────┘
                        ▼
              ┌─────────┼─────────┐
              ▼         ▼         ▼
          ┌────────┐ ┌───────┐ ┌───────┐
          │ Excel  │ │  BC3  │ │ JSON  │
          └────────┘ └───────┘ └───────┘
```

### 7.2 Módulos del sistema


| Módulo                               | Responsabilidad                                                     | Estado actual                                                       |
| ------------------------------------ | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `processors/json_processor.py`       | Normalizar JSON de Autodesk a CAD facts                             | Implementado                                                        |
| `agents/vision_agent.py`             | Análisis de imágenes con GPT-4o Vision                              | Implementado (motor único, necesita especialización por disciplina) |
| `core/inventory_builder.py`          | Construir inventario desde CAD facts + visión                       | Implementado                                                        |
| `core/pipeline.py`                   | Orquestación del pipeline completo                                  | Implementado                                                        |
| `agents/quantifier_agent.py`         | Cuantificación determinista                                         | Implementado (motor único, necesita especialización y detalle)      |
| `agents/classifier_agent.py`         | Matching contra catálogo BC3                                        | Implementado                                                        |
| `rules_engine/`                      | Expansión de partidas derivadas                                     | Implementado                                                        |
| `budget/composer.py`                 | Composición de capítulos y líneas                                   | Implementado                                                        |
| `budget/export_excel.py`             | Exportación Excel                                                   | Implementado                                                        |
| `budget/export_bc3.py`               | Exportación BC3/FIEBDC                                              | Implementado                                                        |
| `processors/bc3_parser.py`           | Parsing de catálogos BC3                                            | Implementado                                                        |
| `knowledge/bc3_embeddings.py`        | Embeddings semánticos para matching                                 | Implementado                                                        |
| `knowledge/feedback_store.py`        | Correcciones humanas                                                | Implementado                                                        |
| `**engines/architectural.py**`       | Motor de análisis arquitectónico/terminaciones                      | **Por implementar**                                                 |
| `**engines/structural.py`**          | Motor de análisis estructural (volumetría detallada)                | **Por implementar**                                                 |
| `**engines/electrical.py`**          | Motor de análisis eléctrico                                         | **Por implementar**                                                 |
| `**engines/plumbing.py`**            | Motor de análisis sanitario                                         | **Por implementar**                                                 |
| `**pricing/apu_engine.py`**          | Motor de análisis de precios unitarios compuestos                   | **Por implementar**                                                 |
| `**pricing/price_catalog.py`**       | Catálogo maestro de precios (materiales, MO, equipos)               | **Por implementar**                                                 |
| `**pricing/snapshot.py`**            | Generador de pricing snapshots por proyecto desde catálogo maestro  | **Por implementar**                                                 |
| `**pricing/construcosto_loader.py`** | Importador de archivos Construcosto (materiales, MO, APUs, equipos) | **Por implementar**                                                 |
| `**pricing/price_resolver.py`**      | Resolución de precios con fallback (APU → BC3 → PRES → pendiente)   | **Por implementar**                                                 |
| **Validador DWG**                    | Verificación de limpieza y organización de DWGs                     | **Por implementar**                                                 |
| **Router de disciplina**             | Clasificación y enrutamiento de PDFs al motor correcto              | **Por implementar**                                                 |


---

## 8. Estructura de capítulos del presupuesto

### 8.1 Árbol de capítulos

```text
01  ESTRUCTURA
    01.01  Hormigón armado
           01.01.01  Zapatas
           01.01.02  Columnas
           01.01.03  Vigas
           01.01.04  Losas
           01.01.05  Muros de corte
           01.01.06  Escaleras (estructura)
    01.02  Encofrados
           01.02.01  Encofrado de zapatas
           01.02.02  Encofrado de columnas
           01.02.03  Encofrado de vigas
           01.02.04  Encofrado de losas
    01.03  Acero de refuerzo
           01.03.01  Acero en zapatas
           01.03.02  Acero en columnas
           01.03.03  Acero en vigas
           01.03.04  Acero en losas
           01.03.05  Malla electrosoldada
           01.03.06  Alambre de amarre

02  ALBAÑILERÍA
    02.01  Muros y divisiones
           02.01.01  Bloques de 6"
           02.01.02  Bloques de 8"
           02.01.03  Bloques de 4"
           02.01.04  Muros de hormigón
           02.01.05  Divisiones drywall

03  IMPERMEABILIZACIÓN
    03.01  Impermeabilización de fundaciones
    03.02  Impermeabilización de áreas húmedas
    03.03  Impermeabilización de cubiertas

04  TERMINACIONES
    04.01  Terminación de superficies (pañete/revoque)
           04.01.01  Pañete interior
           04.01.02  Pañete exterior
    04.02  Terminación de pisos
           04.02.01  Pisos cerámica/porcelanato
           04.02.02  Pisos especiales
           04.02.03  Zócalos
    04.03  Techos y cielos
    04.04  Terminaciones de áreas húmedas
    04.05  Pintura
           04.05.01  Pintura interior
           04.05.02  Pintura exterior
    04.06  Escaleras (acabados)

05  CARPINTERÍAS
    05.01  Puertas
           05.01.01  Puertas de madera
           05.01.02  Puertas metálicas
           05.01.03  Marcos y herrajes
    05.02  Ventanas
    05.03  Closets y muebles fijos

06  INSTALACIONES ELÉCTRICAS
    06.01  Acometida y paneles
    06.02  Cableado y tubería
    06.03  Puntos eléctricos (tomacorrientes, interruptores)
    06.04  Iluminación
    06.05  Sistemas especiales (datos, TV, detección)
    06.06  Puesta a tierra

07  INSTALACIONES SANITARIAS
    07.01  Red de agua fría
    07.02  Red de agua caliente
    07.03  Red de drenaje
    07.04  Ventilación sanitaria
    07.05  Piezas sanitarias
    07.06  Equipos (cisterna, bomba, calentador)
    07.07  Drenaje pluvial

08  OBRAS EXTERIORES
    08.01  Aceras y rampas
    08.02  Estacionamiento
    08.03  Muros de contención / cercas
    08.04  Portones y accesos
    08.05  Jardinería y áreas verdes

09  GASTOS GENERALES
    09.01  Dirección técnica
    09.02  Seguros y fianzas
    09.03  Permisos y licencias
    09.04  Limpieza final
```

---

## 9. Modelo de datos

### 9.1 Entidades principales (core/schemas.py)

**Contexto:**

- `ProjectContext` — id, nombre, paths a JSON/imágenes/BC3, unidad de medida, metadata

**Inventario (por nivel):**

- `LevelInventory` — contenedor de nivel con todas las entidades constructivas
- `InventoryEntity` (base) — id, level_id, source (json|vision|hybrid), confidence, evidence, assumptions
- `Wall`, `Opening`, `Door`, `Window`, `WetArea`, `Kitchen`, `Stair`, `Fixture`, `StructuralElement`

**Cuantificación:**

- `QuantityTakeoff` — item_key, item_type, unit, quantity, formula, inputs, trace
- `QuantityTrace` — source_entity_ids, steps, evidence, conflict_notes, metadata

**Presupuesto:**

- `BudgetCandidate` — takeoff_key, bc3_code, summary, unit, score, rationale, source
- `BudgetChapter` — chapter_id, code, title, level, parent_id, path, child_ids, line_keys
- `BudgetLine` — line_id, takeoff_key, chapter_id, code, nat, unit, summary, quantity, unit_price
- `BudgetRow` — row_type (chapter|line|subtotal), code, unit, summary, quantity, unit_price, amount

### 9.2 Entidades nuevas requeridas

**Precios unitarios compuestos (por implementar):**

- `UnitPriceAnalysis` — partida, unidad, lista de componentes (materiales, MO, equipos), overhead, precio total
- `MaterialComponent` — nombre, unidad, cantidad, precio unitario, desperdicio
- `LaborComponent` — categoría, rendimiento, jornal
- `EquipmentComponent` — tipo, rendimiento, costo horario
- `PriceCatalog` — catálogo maestro de precios base de materiales, mano de obra y equipos

---

## 10. Interfaces externas

### 10.1 Autodesk Platform Services (REST API)


| Endpoint                            | Uso                                              |
| ----------------------------------- | ------------------------------------------------ |
| `authentication/v2/token`           | OAuth2 2-legged (client_credentials)             |
| `oss/v2/buckets/...`                | Almacenamiento de archivos DWG                   |
| `modelderivative/v2/designdata/...` | Traducción DWG → JSON, extracción de propiedades |
| `da/us-east/v3/...`                 | Design Automation (plugin AutoCAD cloud)         |


### 10.2 OpenAI API


| Servicio               | Uso                                     |
| ---------------------- | --------------------------------------- |
| GPT-4o Vision          | Análisis de planos de cada disciplina   |
| GPT-4o Chat            | Clasificación de partidas, matching BC3 |
| text-embedding-3-small | Búsqueda semántica en catálogos         |


### 10.3 Formatos de archivo


| Tipo    | Dirección   | Formatos                        |
| ------- | ----------- | ------------------------------- |
| Entrada | DWG         | DWG (vía APS)                   |
| Entrada | Planos      | PDF (renderizado a imágenes)    |
| Entrada | Catálogo    | BC3/FIEBDC, Excel (PRES)        |
| Entrada | Precios     | APU (JSON/Excel), BC3           |
| Salida  | Presupuesto | Excel (.xlsx), BC3/FIEBDC, JSON |


---

## 11. Requisitos no funcionales

### RNF-01: Trazabilidad

Cada cantidad generada debe llevar fórmula reproducible, metadata de origen, y lista de suposiciones aplicadas.

### RNF-02: Agnosticismo de proyecto

Los módulos activos no deben asumir datos de proyecto específico (alturas fijas, conteos de apartamentos, tablas NPT hardcodeadas).

### RNF-03: Tolerancia a fallos

- Fallo de visión en un plano no detiene el pipeline
- Fallo en embeddings continúa sin ellos
- Fallo en training pairs continúa con lista vacía

### RNF-04: Configuración por entorno

Variables sensibles (CLIENT_ID, CLIENT_SECRET, OPENAI_API_KEY, APS_BUCKET_NAME) via `.env`.

### RNF-05: Extensibilidad

- Motor de reglas configurable vía JSON
- Metodología de oficina inyectable como markdown
- Motores de disciplina como módulos independientes pluggables
- Catálogo de precios actualizable independientemente

### RNF-06: Precisión en volumetría

- Cubicación estructural con error máximo aceptable de 5% vs cálculo manual detallado
- Cantidades de acero deben aproximarse al despiece real cuando los datos están disponibles
- Áreas de acabados deben descontar vanos, columnas embebidas, y elementos que reducen la superficie

### RNF-07: Auditoría

- Cada partida del presupuesto debe ser rastreable hasta el plano o dato de origen
- Los precios unitarios deben mostrar su composición (APU) o fuente (BC3, PRES, estimación)
- Los assumptions y defaults aplicados deben ser explícitos y revisables

---

## 12. Seguridad y autenticación

- **APS**: OAuth2 2-legged con client credentials
- **OpenAI**: API key vía variable de entorno
- Sin autenticación de usuario (pipeline batch/offline)
- Credenciales nunca en código fuente, siempre en `.env`

---

## 13. Glosario de fórmulas por disciplina

### 13.1 Estructura


| Partida                    | Fórmula                                                     | Unidad |
| -------------------------- | ----------------------------------------------------------- | ------ |
| Hormigón en zapata aislada | `largo × ancho × profundidad`                               | m³     |
| Hormigón en zapata corrida | `longitud × ancho × profundidad`                            | m³     |
| Hormigón en columna        | `ancho × profundidad × altura_entrepiso`                    | m³     |
| Hormigón en viga           | `ancho × alto × luz`                                        | m³     |
| Hormigón en losa maciza    | `área × espesor`                                            | m³     |
| Hormigón en losa nervada   | `(área × espesor) - volumen_bloques_relleno`                | m³     |
| Encofrado columna          | `2 × (ancho + profundidad) × altura`                        | m²     |
| Encofrado viga             | `(2 × alto + ancho) × luz`                                  | m²     |
| Encofrado losa             | `área_inferior`                                             | m²     |
| Acero (detallado)          | `Σ(cant × (long_corte + ganchos + traslape) × peso_lineal)` | kg     |
| Acero (estimación)         | `volumen_hormigón × ratio_kg_m3`                            | kg     |


### 13.2 Albañilería


| Partida         | Fórmula                                                              | Unidad   |
| --------------- | -------------------------------------------------------------------- | -------- |
| Muro de bloques | `longitud × altura × espesor` (volumen) o `longitud × altura` (área) | m³ o m²  |
| Bloques por m²  | `área / (0.40 × 0.20)` (para bloques estándar 8"×16")                | unidades |


### 13.3 Terminaciones


| Partida                   | Fórmula                                                       | Unidad |
| ------------------------- | ------------------------------------------------------------- | ------ |
| Pañete en muros           | `área_neta × caras`                                           | m²     |
| Pintura                   | `área_neta × caras × manos` (considerar rendimiento por mano) | m²     |
| Cerámica en pisos         | `área_piso + desperdicio(5-10%)`                              | m²     |
| Cerámica en muros húmedos | `perímetro_baño × altura_cerámica`                            | m²     |
| Zócalo                    | `perímetro_habitación - ancho_puertas`                        | m      |


### 13.4 Eléctrico


| Partida         | Fórmula                                                      | Unidad |
| --------------- | ------------------------------------------------------------ | ------ |
| Punto eléctrico | `cantidad` (compuesto: caja + cable + tubería + dispositivo) | ud     |
| Cableado        | `distancia_horizontal + subida/bajada + 15%`                 | m      |
| Tubería conduit | `longitud_cableado` (paralela al cable)                      | m      |


### 13.5 Sanitario


| Partida         | Fórmula                                                  | Unidad |
| --------------- | -------------------------------------------------------- | ------ |
| Tubería agua    | `longitud_recorrido + 15%(accesorios)`                   | m      |
| Punto de agua   | `cantidad` (compuesto: tubería + válvula + conexión)     | ud     |
| Pieza sanitaria | `cantidad` (compuesto: pieza + instalación + conexiones) | ud     |


---

## 14. Apéndice: Estado actual vs. requerido


| Capacidad               | Estado actual                          | Estado requerido                                                                         |
| ----------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------- |
| Motores por disciplina  | Un solo motor para todo                | 4 motores especializados                                                                 |
| Entrada de PDF          | Todos al mismo motor de visión         | Clasificados por disciplina, enrutados al motor correcto                                 |
| Validación DWG          | Sin validación de limpieza             | Validación de layers, ruido, vistas                                                      |
| Acero de refuerzo       | Ratios genéricos (kg/m³)               | Despiece por diámetro con traslapes y desperdicio                                        |
| Precios unitarios       | Solo precio plano del BC3              | APU compuesto (materiales + MO + equipos + overhead)                                     |
| Fuente de precios       | BC3 estático cargado por corrida       | Construcosto (4 archivos: materiales, MO, APUs, equipos) + BC3 + PRES como fallback      |
| Persistencia de precios | Sin persistencia (stateless puro)      | Pricing snapshots congelados por proyecto con metadata de región/periodo                 |
| Regionalización         | Sin soporte                            | Precios por región (Santo Domingo, Punta Cana, Santiago, etc.) con advertencia de mezcla |
| Volumetría estructural  | Fórmulas básicas de sección × longitud | Cubicación detallada con intersecciones, nervaduras, capiteles                           |
| Acabados                | Reglas genéricas de caras              | Acabado diferenciado por zona, alturas parciales en húmedos                              |
| Eléctrico/sanitario     | Solo conteo de fixtures                | Longitudes de tubería/cableado, circuitos, diámetros                                     |
| Organización DWG        | Sin requisitos de limpieza             | DWG limpio, vistas por nivel o model space organizado                                    |


