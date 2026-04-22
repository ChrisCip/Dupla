# PROMPT PARA CURSOR — Fix de 4 Bloqueantes Pre-E2E (en orden de prioridad)

## REGLA ABSOLUTA

**NO modifiques NADA que no esté explícitamente listado en los 4 bloqueantes de abajo.** No refactorices, no "mejores" código que funciona, no cambies nombres de variables, no reorganices imports, no toques tests que pasan. Si algo no está mencionado aquí, no lo toques. Cada fix debe ser quirúrgico y trazable.

---

## CONTEXTO RÁPIDO

Repo: Dupla.git (~10K líneas Python)
Pipeline: Autodesk API → JSON processor → Vision AI → Quantifier → Rules Engine → BC3 Classifier → Excel Export
Catálogo BC3: `data/TGIU.bc3` (684 partidas con precios en RD$)
Presupuesto real: `data/PRES.xlsx` (1,565 partidas, 296 capítulos)
Estado: 53/55 tests OK. Auditoría pre-E2E arrojó score 15.5/40 promedio entre disciplinas.

Las 4 disciplinas y sus capítulos permitidos:
- Arquitectónica → 03, 04, 05, 08, 09
- Estructural → 01, 02
- Eléctrica → 06
- Sanitaria → 07

---

## BLOQUEANTE B4 — Cablear `upload_discipline_id` en el script local

### Problema
`dupla_run_full_analysis_local.py` (o el script equivalente que ejecuta el pipeline completo) no pasa `upload_discipline_id` al Vision Agent. Esto significa que Vision corre sin saber qué disciplina está analizando, y por tanto:
- No puede aplicar el prompt específico de disciplina
- No puede filtrar elementos irrelevantes
- `infer_source_discipline` en el classifier queda sin dato real y defaultea a "arquitectonica"

### Fix requerido

1. **Localiza** el punto en el script local donde se invoca el Vision Agent (probablemente `agents/vision_agent.py` o la llamada dentro de `core/pipeline.py`).

2. **Agrega** el parámetro `discipline_id` al flujo. El script local debe aceptar un argumento `--discipline` con valores: `arquitectonica`, `estructural`, `electrica`, `sanitaria`.

3. **Propaga** ese `discipline_id` hasta:
   - El prompt de Vision AI (para que sepa qué buscar)
   - El quantifier (para que aplique las reglas correctas)
   - El classifier (para que valide capítulo vs disciplina)
   - Los takeoffs generados (como metadata `source_discipline`)

4. **NO cambies** la interfaz de Autodesk API (`aps_integration/`). Solo el flujo interno del pipeline.

### Verificación
```python
# Esto debe funcionar después del fix:
# python dupla_run_full_analysis_local.py --discipline arquitectonica --dwg plano_arq.dwg
# python dupla_run_full_analysis_local.py --discipline electrica --dwg plano_elec.dwg

# Y el output debe tener:
# - Cada takeoff con metadata source_discipline = "arquitectonica" (o la que corresponda)
# - Vision prompt ajustado a la disciplina
# - Classifier validando que las partidas caigan en capítulos permitidos para esa disciplina
```

### Archivos a tocar (SOLO estos)
- `dupla_run_full_analysis_local.py` — agregar argparse `--discipline`
- `core/pipeline.py` — propagar `discipline_id` en el flujo
- `agents/vision_agent.py` — recibir y usar `discipline_id` en prompt selection
- `agents/quantifier_agent.py` — recibir `discipline_id` para filtro
- `agents/classifier_agent.py` — recibir `discipline_id` para validación capítulo

### Criterio de éxito
- Correr con `--discipline arquitectonica` produce takeoffs donde TODOS tienen `source_discipline == "arquitectonica"`
- Correr con `--discipline electrica` produce takeoffs donde TODOS tienen `source_discipline == "electrica"`
- Si NO se pasa `--discipline`, el sistema debe ADVERTIR en stdout (warning, no error) y continuar con inferencia actual

---

## BLOQUEANTE B1 — Partidas específicas en vez de genéricas

### Problema
El pipeline genera takeoffs con `item_type` genérico (`wall_net_area`, `door_count`, `fixture_count`) sin especificación de tipo concreto. El presupuesto real de PRES.xlsx tiene partidas como:
- "Muro Bloques 15x20x40 SNP" (no solo "muro")
- "Columna C1 0.50 x 0.50 - 16 ø1"" (no solo "columna")
- "Salida de tomacorrientes doble 110V" (no solo "fixture_count")
- "Puerta polimetálica 0.90×2.10" (no solo "door_count")

La información específica (tipo C1, espesor 15cm, voltaje 110V, dimensión 0.90×2.10) existe en los planos y Vision PUEDE extraerla. Pero se pierde en la conversión Vision → LevelInventory → Takeoff → Budget.

### Fix requerido

**NO cambies el schema de LevelInventory ni de Takeoff.** Usa los campos que YA existen para transportar la especificidad. Específicamente:

1. **En Vision Agent** — Los prompts de Vision ya piden (o deben pedir) detalles como tipo de muro, espesor, dimensiones de puerta, etc. Verifica que el output JSON de Vision incluya estos campos. Si no los incluye, ajusta el prompt para que los pida explícitamente.

   Ejemplo de lo que Vision debe devolver:
   ```json
   {
     "walls": [
       {"type": "C1", "thickness_cm": 15, "material": "bloque 6\"", "area_m2": 669.05},
       {"type": "C2", "thickness_cm": 10, "material": "bloque 4\"", "area_m2": 32.19}
     ],
     "doors": [
       {"type": "polimetalica", "width_m": 0.90, "height_m": 2.10, "count": 2},
       {"type": "madera_principal", "width_m": 1.00, "height_m": 2.10, "count": 5}
     ]
   }
   ```

2. **En el adapter Vision → LevelInventory** (dentro de `core/pipeline.py` o donde se haga la conversión) — Asegúrate de que los campos de especificidad de Vision se mapeen a los atributos del schema. Revisa:
   - `Wall` tiene `wall_type` → debe llenarse con el tipo del plano (C1, C2)
   - `Door` tiene `door_type` → debe llenarse con el tipo real (polimetálica, madera)
   - `Window` tiene `window_type` → debe llenarse
   - `Fixture` tiene `fixture_type` → debe llenarse con el tipo específico (tomacorriente doble 110V)
   - Si algún campo de especificidad NO existe en el schema, agrégalo (ej: `thickness_cm` en Wall si no existe)

3. **En el quantifier** — Cuando emite takeoffs, el `description` / `summary` del takeoff debe incluir la especificación completa, NO el item_type genérico.

   MAL:  `{"item_type": "wall_net_area", "description": "Muro", "quantity": 701.24, "unit": "m2"}`
   BIEN: `{"item_type": "wall_net_area", "description": "Muro tipo C1, bloque 6\" (15cm), mortero 1:5", "quantity": 669.05, "unit": "m2"}`
   BIEN: `{"item_type": "wall_net_area", "description": "Muro tipo C2, bloque 4\" (10cm), mortero 1:5", "quantity": 32.19, "unit": "m2"}`

   Es decir: un muro genérico de 701 m² se SEPARA en dos takeoffs específicos: C1 con 669 m² y C2 con 32 m².

4. **En el classifier** — Cuando busca match en BC3, usa la descripción específica (no el item_type) para buscar el código BC3 más cercano. "Muro tipo C1, bloque 6\" (15cm)" debe matchear diferente que "Muro tipo C2, bloque 4\" (10cm)" porque tienen códigos BC3 y precios distintos.

5. **En el composer/export** — El campo `Resumen` del Excel final debe mostrar la descripción específica, no el item_type.

### Verificación
```
# El Excel final debe tener líneas como:
# Código     | Nat     | Ud | Resumen                                      | CanPres | PrPres    | ImpPres
# TGIU0301xx | Partida | m2 | Muro tipo C1, bloque 6" (15cm), mortero 1:5  | 669.05  | 1,850.00  | 1,237,742.50
# TGIU0301xx | Partida | m2 | Muro tipo C2, bloque 4" (10cm), mortero 1:5  |  32.19  | 1,450.00  |    46,675.50

# Y NO líneas como:
# DUP-0001   | Partida | m2 | wall_net_area                                 | 701.24  | 0.00      | 0.00
```

### Archivos a tocar (SOLO estos)
- `agents/vision_agent.py` — verificar/ajustar prompts para pedir especificidad
- `core/pipeline.py` — adapter Vision → LevelInventory (mapeo de campos específicos)
- `agents/quantifier_agent.py` — separar takeoffs por tipo específico, descripción completa
- `agents/classifier_agent.py` — usar descripción específica para BC3 matching
- `budget/composer.py` o `budget/export_excel.py` — verificar que Resumen use descripción, no item_type
- `core/schemas.py` — SOLO si falta un campo necesario (ej: `thickness_cm` en Wall). No reestructurar.

### Criterio de éxito
- CERO takeoffs con descripción = item_type genérico (no más "wall_net_area" como resumen)
- Cada muro tiene su tipo (C1, C2, etc.) como parte de la descripción
- Cada puerta tiene su tipo y dimensiones
- Cada fixture eléctrico/sanitario tiene su tipo específico
- Si Vision no puede determinar el tipo → descripción = "[Tipo no identificado en plano] - muro bloque [espesor si visible]"

---

## BLOQUEANTE B3 — Gap `wet_area_fixture_count`

### Problema
`wet_area_fixture_count` está referenciado en:
- `agents/classifier_agent.py` — como item_type reconocido
- `knowledge/training_data.py` — con training pairs
- Filtros de disciplina sanitaria

Pero `agents/quantifier_agent.py` NUNCA emite un takeoff con `item_type == "wet_area_fixture_count"`. Esto significa que el classifier tiene lógica para catalogar piezas sanitarias de áreas húmedas, pero el quantifier nunca las genera. El presupuesto queda sin inodoros, lavamanos, duchas, fregaderos de baños/cocinas como partidas separadas.

### Fix requerido

1. **Localiza** en `agents/quantifier_agent.py` dónde se procesan las entidades `WetArea` y `Fixture`.

2. **Verifica** si los fixtures de áreas húmedas (toilet, sink, shower, bathtub, bidet) se están contando de alguna otra forma (quizás como `fixture_count` genérico). Si sí, el problema es que no tienen el item_type correcto. Si no, hay que agregarlos.

3. **Agrega emisión** de takeoffs `wet_area_fixture_count` para cada tipo de pieza sanitaria encontrada en áreas húmedas:
   ```python
   # Por cada WetArea que tenga fixtures:
   for fixture in wet_area.fixtures:
       takeoffs.append(Takeoff(
           item_type="wet_area_fixture_count",
           description=f"{fixture.fixture_type} en {wet_area.area_type}",  
           # ej: "Inodoro en baño", "Fregadero en cocina"
           quantity=fixture.count,
           unit="ud",
           source_discipline="sanitaria",
           level_id=wet_area.level_id,
           inputs={"fixture_type": fixture.fixture_type, "area_type": wet_area.area_type}
       ))
   ```

4. **NO dupliques** — si `fixture_count` genérico ya contaba estos mismos fixtures, elimina la duplicación. Las piezas sanitarias de áreas húmedas deben ir como `wet_area_fixture_count`, NO como `fixture_count` sin disciplina.

### Verificación
```python
# Después del fix, correr el quantifier con un inventario que tenga 3 baños con:
#   - 3 inodoros, 3 lavamanos, 3 duchas
# Debe producir:
#   - wet_area_fixture_count: "Inodoro en baño", qty=3, source_discipline="sanitaria"
#   - wet_area_fixture_count: "Lavamanos en baño", qty=3, source_discipline="sanitaria"
#   - wet_area_fixture_count: "Ducha en baño", qty=3, source_discipline="sanitaria"
# Y NO:
#   - fixture_count: "toilet", qty=3, source_discipline="" ← INCORRECTO
```

### Archivos a tocar (SOLO estos)
- `agents/quantifier_agent.py` — agregar emisión de `wet_area_fixture_count`
- Si hay deduplicación necesaria contra `fixture_count` → tocar la lógica de fixtures ahí mismo

### Criterio de éxito
- `grep -r "wet_area_fixture_count" agents/quantifier_agent.py` devuelve al menos una línea de emisión
- Test con inventario de áreas húmedas produce takeoffs con `item_type == "wet_area_fixture_count"` y `source_discipline == "sanitaria"`
- No hay fixtures sanitarios duplicados como `fixture_count` genérico

---

## BLOQUEANTE B2 — Reemplazar defaults hardcoded con valores del plano

### Problema
El sistema tiene promedios hardcoded que producen cantidades incorrectas en cualquier proyecto que no sea exactamente como el default:

| Default hardcoded | Dónde está | Impacto |
|---|---|---|
| Área húmeda = **5.0 m²** | `rules_engine/default_rules.json` → regla `wet_area_count_standard` | Impermeabilización y acabados de baño con m² inventados |
| Cocina = **4.0 m²** | `rules_engine/default_rules.json` → regla `kitchen_count_standard` | Impermeabilización cocina con m² inventados |
| Viga sección = **0.30 × 0.50** | `rules_engine/default_rules.json` → regla `beam_length_concrete_standard` | Volumen de hormigón incorrecto |
| Columna sección = **0.40 × 0.40** | `rules_engine/default_rules.json` → regla `column_*` | Volumen de hormigón incorrecto |
| Columna altura = **2.80 m** | `rules_engine/default_rules.json` → regla `column_*` | Volumen incorrecto si entrepiso ≠ 2.80 |
| Losa espesor = **0.20 m** | `rules_engine/default_rules.json` → regla `slab_area_concrete_standard` | Volumen de hormigón incorrecto |
| Acero por ratios = **100-120 kg/m³** | `agents/quantifier_agent.py` → `_REBAR_KG_PER_M3` | kg de acero estimado, no real |

### Fix requerido

**NO elimines los defaults.** Son el fallback necesario cuando el plano no da la información. Pero el sistema debe PREFERIR el dato real cuando existe, y MARCAR claramente cuando usa un default.

1. **En las reglas del Rules Engine** (`rules_engine/default_rules.json`):
   
   Para cada regla que use un default, agrega un campo `"source"` al derive:
   ```json
   {
     "id": "wet_area_count_standard",
     "match": {"item_types": ["wet_area_count"]},
     "derive": [
       {
         "item_type": "wet_area_waterproofing",
         "formula": "value * area_per_unit",
         "params": {
           "area_per_unit": 5.0,
           "area_per_unit_source": "default_estimate"
         },
         "unit": "m2"
       }
     ]
   }
   ```

   Y la lógica del rules engine debe:
   - Primero buscar en los `inputs` del takeoff si hay un `area_m2` real (del plano vía Vision)
   - Si existe → usar ese valor, `source = "plan_measurement"`
   - Si no existe → usar el default, `source = "default_estimate"`

2. **En el quantifier** — Cuando Vision reporta dimensiones específicas (ej: sección de columna 0.50×0.50 en vez del default 0.40×0.40), esos valores deben llegar como `inputs` del takeoff para que las reglas los usen.

3. **En el composer/export** — Cuando una partida usa un default, agregar un flag visible:
   ```
   # En el Excel, columna adicional "Fuente":
   # "Medido" → cantidad viene del plano
   # "Estimado (default)" → cantidad usa promedio hardcoded
   ```
   
   Esto NO es opcional. Dupla necesita saber qué valores son confiables y cuáles necesitan verificación manual.

4. **En `_REBAR_KG_PER_M3`** — No se puede eliminar sin despiece real del plano. Pero:
   - Agregar al takeoff de acero: `"source": "ratio_estimate"` y `"note": "Estimado por ratio {X} kg/m³. Requiere verificación con despiece real."`
   - El Excel debe mostrar esta nota en la partida de acero

### Verificación
```python
# Caso 1: Vision reporta baño con área real de 3.2 m²
# → wet_area_waterproofing debe tener quantity=3.2 y source="plan_measurement"

# Caso 2: Vision reporta baño SIN área
# → wet_area_waterproofing debe tener quantity=5.0 y source="default_estimate"

# Caso 3: Vision reporta columna C1 sección 0.50×0.50 altura 3.10
# → column_concrete_volume debe usar 0.50×0.50×3.10 = 0.775 m³
# → NO 0.40×0.40×2.80 = 0.448 m³

# En el Excel final:
# Toda partida con source="default_estimate" debe tener flag visible
# Toda partida con source="ratio_estimate" debe tener nota de verificación
```

### Archivos a tocar (SOLO estos)
- `rules_engine/default_rules.json` — agregar `source` params y lógica prefer-real
- `rules_engine/engine.py` (o donde se ejecutan las reglas) — implementar lógica "inputs reales > defaults"
- `agents/quantifier_agent.py` — propagar dimensiones de Vision como `inputs` en takeoffs, marcar ratios de acero
- `budget/composer.py` o `budget/export_excel.py` — agregar columna/flag de fuente de cantidad

### Criterio de éxito
- NINGÚN default se usa cuando el plano provee el dato real
- TODOS los defaults usados están marcados como `"default_estimate"` en metadata
- El Excel tiene visibilidad clara de qué es medido vs estimado
- Los ratios de acero tienen nota de "requiere verificación con despiece"

---

## ORDEN DE IMPLEMENTACIÓN

```
B4 (cablear discipline_id)     ← Hazlo PRIMERO. Es prerequisito de B1.
    │                              Sin saber la disciplina, Vision no puede
    │                              pedir los detalles correctos.
    ▼
B1 (partidas específicas)      ← Hazlo SEGUNDO. Es el de mayor impacto.
    │                              Transforma el output de genérico a útil.
    │
    ▼
B3 (wet_area_fixture_count)    ← Hazlo TERCERO. Es puntual y rápido.
    │                              Cierra un gap conocido en sanitario.
    │
    ▼
B2 (reemplazar defaults)       ← Hazlo ÚLTIMO. Es el más complejo.
                                   Requiere que B4 y B1 ya funcionen
                                   para que Vision provea datos reales.
```

## DESPUÉS DE CADA FIX

Corre los tests existentes (`pytest tests/ -q`). Si algún test falla por el cambio:
- Si el test validaba el comportamiento viejo (genérico) → actualiza el test al nuevo comportamiento (específico)
- Si el test valida algo no relacionado → NO lo toques, investiga por qué falló

## LO QUE NO DEBES HACER

- No toques `aps_integration/` — la extracción de Autodesk funciona
- No cambies el formato del catálogo BC3 ni el parser
- No reestructures carpetas ni renombres módulos
- No agregues dependencias nuevas (pip packages)
- No "mejores" código que funciona y no está en los 4 bloqueantes
- No toques tests que pasan y no están relacionados con los fixes
- Si encuentras un bug adicional NO listado aquí → repórtalo en un comentario `# TODO: [descripción]` pero NO lo arregles

# ADDENDUM — Corrección de Lógica de Precios (pegar al final del prompt de bloqueantes)

## REGLA: NO modifiques nada de los 4 bloqueantes originales (B4, B1, B3, B2) excepto la lógica de PRICING descrita aquí.

---

## CORRECCIÓN: Fuente de Precios

### El prompt anterior decía (INCORRECTO):
> "Precio viene del BC3 (RD$ 1,850.00/m²)"
> "Si no hay match en BC3 → flag SIN_PRECIO_BC3"

### Lo correcto:

El catálogo BC3 (`data/TGIU.bc3`) da **ESTRUCTURA**: capítulos, partidas, unidades, códigos. **NO es la fuente primaria de precios.**

Los precios reales vienen de **ConstruCosto** — 4 archivos CSV en `data/construcosto/`:

---

### ARCHIVO 1: `Analisis de Costos Punta Cana ConstruCosto.csv` (5,983 filas)
**Este es el archivo principal de pricing. Contiene los APUs completos.**

```
Encoding: latin1
Columnas: COD. | DESCRIPCION | CANT | UND | PU | ITBIS | SUBTOTAL | SUBTOTAL ITBIS | TOTAL | SUPLIDOR RECOMENDADO

Estructura jerárquica:
  100.00  PRELIMINARES                          ← Capítulo (sin precio)
  100.01  LETRERO DE OBRA  1.00  UND  ...  RD$104,999.99   ← Partida con precio TOTAL
          Materiales y Equipos                  ← Sub-sección
          Arte e impresión  1.00  PA  RD$40,677.97  ...     ← Desglose material
          Estructura metálica  1.00  PA  ...                ← Desglose material
          Total/UND  ...  RD$104,999.99                     ← Total de la partida
  100.02  REPLANTEO Y CHARRANCHA  1.00  M2  ...  RD$279.27  ← Siguiente partida
```

**Cómo parsear:**
- Las filas con `COD.` tipo `XXX.XX` (ej: 100.01, 200.03) son PARTIDAS con precio unitario
- Las filas sin código son DESGLOSE (materiales, MO, equipos de esa partida)
- Las filas con `COD.` tipo `XXX.00` (ej: 100.00, 200.00) son CAPÍTULOS (agrupadores, sin precio)
- El precio de la partida está en columna `TOTAL` (incluye ITBIS)
- El precio sin ITBIS está en columna `SUBTOTAL`
- La unidad está en columna `UND`

**Para matching contra partidas del pipeline:**
- Buscar fuzzy match entre la DESCRIPCION de ConstruCosto y la descripción de la partida generada
- Ejemplo: partida del pipeline "Muro tipo C1, bloque 6\" (15cm)" → buscar en ConstruCosto algo como "MURO DE BLOQUES 6\"" o "PARED DE BLOQUES 15CM"

---

### ARCHIVO 2: `Materiales e Insumos Punta Cana ConstruCosto.csv` (1,520 filas)
**Precios unitarios de materiales sueltos.**

```
Encoding: latin1
Columnas: CODIGO | DESCRIPCION | UND | PU+ITBIS | PU SIN ITBIS | RENDIMIENTOS-OBS. | SUPLIDOR RECOMENDADO

Ejemplos:
  (vacío) | Cemento Gris 94 lbs. Tipo Portland | FDA | RD$545.00 | RD$461.86 | (vacío) | MINIBANNER...
  (vacío) | Arena gruesa Itabo lavada           | M3  | RD$1,710.00 | RD$1,449.15 | ...
  (vacío) | Grava de 3/4"                       | M3  | RD$1,650.00 | RD$1,398.31 | ...
```

**Nota:** Agrupados por categoría (CEMENTOS, AGREGADOS, ACEROS, etc.). Las filas de categoría tienen solo DESCRIPCION sin precio.
**Precio a usar:** columna `PU SIN ITBIS` para el presupuesto base; `PU+ITBIS` si el proyecto requiere ITBIS incluido.

---

### ARCHIVO 3: `Mano de obra Punta Cana ConstruCosto.csv` (880 filas)
**Jornales diarios y rendimientos.**

```
Encoding: latin1
Estructura (primeras filas):
  JORNALES DIARIOS
  Maestro (MA)                              | DIA | RD$2,941.78
  Trabajador de 1ra Categoría (T1)          | DIA | RD$2,334.67
  Trabajador de 2da Categoría (T2)          | DIA | RD$1,867.44
  Trabajador de 3ra Categoría - Terminador (T3) | DIA | RD$1,636.80
```

**Uso:** Para calcular el componente de mano de obra en un APU cuando se construye desde cero. No se usa directamente para poner precio a una partida — se usa cuando el sistema necesita CONSTRUIR un APU que no existe en "Análisis de Costos".

---

### ARCHIVO 4: `Equipos y Movimientos de Tierra Punta Cana ConstruCosto.csv` (475 filas)
**Costos horarios de maquinaria + partidas de movimiento de tierra.**

```
Encoding: latin1
Columnas: COD. | DESCRIPCION | CANT | UND | PU | ITBIS | SUBTOTAL | SUBTOTAL ITBIS | TOTAL | SUPLIDOR RECOMENDADO

Ejemplos:
  100.01 | COMPRESOR DE AIRE IR 185CFM | 1.00 | HR | ... | RD$2,250.00 | Excon S.A.
```

**Misma estructura que Análisis de Costos** pero solo para equipos y movimiento de tierras.

---

## Jerarquía de búsqueda de precios (implementar en `_extract_unit_price` o equivalente)

```python
def get_price_for_partida(description: str, unit: str, region: str = "Punta Cana") -> tuple[float, str]:
    """
    Busca precio en orden jerárquico. Retorna (precio, fuente).
    
    IMPORTANTE: Los precios en los CSV tienen formato "RD$1,710.00" — 
    hay que parsear removiendo "RD$", comas, y convirtiendo a float.
    """
    
    # 1. Análisis de Costos (APU completo — fuente primaria)
    #    Buscar fuzzy match en columna DESCRIPCION de filas con COD. tipo XXX.XX
    #    Precio: columna SUBTOTAL (sin ITBIS) de la fila de la partida
    #    Este es el más confiable porque tiene el desglose completo
    price = search_analisis_costos(description, unit)
    if price > 0:
        return price, f"ConstruCosto APU {region}"
    
    # 2. Materiales (si la partida es un material puro, no una actividad compuesta)
    #    Buscar fuzzy match en columna DESCRIPCION
    #    Precio: columna PU SIN ITBIS
    price = search_materiales(description, unit)
    if price > 0:
        return price, f"ConstruCosto Material {region}"
    
    # 3. Equipos (si la partida es un equipo o movimiento de tierra)
    price = search_equipos(description, unit)
    if price > 0:
        return price, f"ConstruCosto Equipo {region}"
    
    # 4. BC3 catalog (último recurso — puede tener precios pero no actualizados)
    price = search_bc3(description, unit)
    if price > 0:
        return price, "BC3 TGIU (fallback)"
    
    # 5. Sin precio
    return 0, "PRECIO_PENDIENTE"
```

## Parsing de precios del CSV

```python
def parse_rd_price(value: str) -> float:
    """
    Convierte formato ConstruCosto a float.
    
    Ejemplos:
      "RD$1,710.00"   → 1710.00
      "RD$545.00"     → 545.00
      "RD$88,983.05"  → 88983.05
      ""              → 0.0
      None            → 0.0
    """
    if not value or not isinstance(value, str):
        return 0.0
    cleaned = value.replace("RD$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
```

## Lo que cambia en el Excel final

En el bloqueante B1, donde el prompt decía:
```
# TGIU0301xx | Partida | m2 | Muro tipo C1, bloque 6" (15cm) | 669.05 | 1,850.00 | 1,237,742.50
```

Ahora debe ser:
```
# Código     | Nat     | Ud | Resumen                         | CanPres | PrPres     | ImpPres        | Fuente Precio
# TGIU0301xx | Partida | m2 | Muro tipo C1, bloque 6" (15cm)  | 669.05  | 1,850.00   | 1,237,742.50   | ConstruCosto APU Punta Cana
# TGIU0301xx | Partida | m2 | Muro tipo C2, bloque 4" (10cm)  |  32.19  | 1,450.00   |    46,675.50   | ConstruCosto APU Punta Cana
# TGIU0701xx | Partida | ud | Inodoro ECO                     |  21.00  | 8,500.00   |   178,500.00   | ConstruCosto Material Punta Cana
# DUP-0042   | Partida | ml | Tubería PVC 4" drenaje           |  85.00  | 0.00       |     0.00       | PRECIO_PENDIENTE
```

**El código BC3 sigue viniendo del catálogo BC3** (matching semántico para asignar TGIU0301xx).
**El precio viene de ConstruCosto** (búsqueda fuzzy en los CSV).
**Ambas fuentes son independientes** y se combinan en la partida final.

## Archivos a tocar para implementar esto

- `agents/classifier_agent.py` → `_extract_unit_price` — reordenar jerarquía: ConstruCosto primero, BC3 como fallback
- Crear (si no existe) un parser dedicado: `processors/construcosto_parser.py` — lee los 4 CSV con encoding latin1, normaliza precios, expone funciones de búsqueda
- `budget/export_excel.py` → agregar columna "Fuente Precio" al Excel final
- NO tocar el parser BC3 — sigue sirviendo para la estructura/códigos de partida

