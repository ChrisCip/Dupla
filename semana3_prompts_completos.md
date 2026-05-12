# SEMANA 3 — Prompts Claude Code (Correr en orden)

Cada bloque es un prompt para Claude Code. Correr uno, verificar, commit, siguiente.

---

## BLOQUE 1 — Fix geometría duplicada (CRÍTICO)

### Prompt Claude Code:

```
@core/inventory_builder.py El inventario tiene un bug crítico de geometría duplicada. 

PROBLEMA: build_level_inventory() se llama una vez por cada página del PDF (9 páginas para GEBSA IV). Pero recibe el mismo cad_facts para TODAS las páginas porque la extracción APS devuelve la geometría del DWG completo, no separada por nivel. Resultado: json-wall-a-wall tiene 3328.82m en CADA uno de los 9 niveles = 29,959m total cuando debería ser ~3,328m.

EVIDENCIA: En budget_output.json, hybrid_inventory tiene 9 niveles con las mismas 24 paredes JSON con las mismas longitudes exactas.

FIX REQUERIDO en _build_json_walls() y _build_json_structural_elements():

1. Añadir parámetro total_levels: int a ambas funciones
2. Si total_levels > 1, dividir TODAS las longitudes/áreas/volúmenes del CAD entre total_levels:
   - length = raw_length / total_levels
   - Esto es una aproximación pero es 9x mejor que duplicar todo
3. Propagar total_levels desde build_level_inventory() — añadir parámetro ahí también
4. En dupla_run_gebsa.py donde se llama build_level_inventory en loop, pasar total_levels=len(pages) o el número de niveles del proyecto

TAMBIÉN: en _build_json_walls(), las paredes con length < 0.5m después de dividir entre niveles deben descartarse (son ruido del DWG).

NO cambies la lógica de merge CAD↔Vision, solo la distribución de geometría.
```

### Verificación terminal:
```bash
python -c "
import json
# Si tienes budget_output.json del último run, verifica que las longitudes cambien
# Después de re-correr el pipeline:
# python dupla_run_gebsa.py --only arquitectura --pricing-excel 'data/Lista de precios-analisis-MO.xlsx'
print('Verificar post-run: longitudes deben ser ~1/9 del valor anterior')
print('json-wall-a-wall debería ser ~370m por nivel, no 3328m')
"
```

---

## BLOQUE 2 — Fix merge CAD↔Vision (CRÍTICO)

### Prompt Claude Code:

```
@core/inventory_builder.py La función _merge_entities() en línea ~311 matchea entidades JSON y Vision por id o por _entity_signature(). Pero los IDs nunca coinciden: los muros CAD tienen id="json-wall-a-wall" y los muros Vision tienen id="muro_int_bloque6". Resultado: ambos se agregan al inventario como entradas separadas = doble conteo.

PROBLEMA REAL: No se puede hacer match 1:1 entre muros CAD y Vision porque representan cosas diferentes:
- CAD: 24 layers con geometría (longitudes) pero sin clasificación
- Vision: 3 tipos de muro con clasificación (bloque6, bloque8) pero geometría limitada

FIX: Cambiar la estrategia de merge de muros. En build_level_inventory(), DESPUÉS de hacer _merge_entities para walls:

1. Separar los muros resultantes en dos grupos:
   - json_only: muros con source="json" que NO matchearon con Vision (material_hint es None)
   - vision_classified: muros con source="vision" o "hybrid" que SÍ tienen material_hint

2. Si hay vision_classified para esta página:
   - Calcular la longitud total de json_only muros
   - Calcular la proporción de cada tipo de Vision (ej: 60% bloque6, 40% bloque8)
   - REDISTRIBUIR la longitud de json_only entre los tipos de Vision según proporción
   - Crear muros enriquecidos con: geometría del JSON + clasificación del Vision
   - Descartar los json_only originales (ya están redistribuidos)

3. Si NO hay vision_classified para esta página:
   - Dejar los json_only como están (no hay info de Vision para enriquecer)
   - Pero agregar assumption: "Muro sin clasificar por Vision, tipo de bloque desconocido"

Ejemplo concreto del resultado esperado:
ANTES: [json-wall-a-wall (370m, material=None), json-wall-mb (105m, material=None), muro_int_bloque6 (30m, masonry)]
DESPUÉS: [muro_int_bloque6_enriched (370+105=475m * proporción, masonry, bloque6, espesor 15cm)]

El punto es que los muros Vision dan la CLASIFICACIÓN y los muros JSON dan la GEOMETRÍA. El merge debe combinar ambos, no concatenarlos.
```

### Verificación terminal:
```bash
# Después de re-correr:
python -c "
import json
with open('output/LAST_RUN/budget_output.json') as f:  # ajustar path
    data = json.load(f)
inv = data['hybrid_inventory']
for i, level in enumerate(inv[:3]):
    walls = level.get('walls', [])
    classified = [w for w in walls if w.get('material_hint')]
    unclassified = [w for w in walls if not w.get('material_hint')]
    print(f'Level {i}: {len(walls)} walls, {len(classified)} classified, {len(unclassified)} unclassified')
    for w in classified[:3]:
        print(f'  {w[\"id\"][:40]} material={w.get(\"material_hint\")} length={w.get(\"length_m\",0):.1f}m')
"
```

---

## BLOQUE 3 — Fix descripciones y unidades en el quantifier

### Prompt Claude Code:

```
@disciplines/arquitectura/engine.py @disciplines/arquitectura/quantifier.py El quantifier de arquitectura produce takeoffs con descripción "Muro tipo json-wall-a-wall" y unidad m3 para muros de bloques. Ambos están mal.

PROBLEMA 1 - DESCRIPCIONES: El takeoff_description usa el id del muro (nombre del layer CAD) en vez de una descripción de construcción. Si el muro tiene material_hint y inputs con espesor/tipo, la descripción debe reflejar eso.

FIX: En el quantifier (o donde se genera takeoff_description para muros), cambiar la lógica:

```python
# ANTES:
takeoff_description = f"Muro tipo {wall.id}"

# DESPUÉS:
def _wall_description(wall) -> str:
    parts = ["Muro"]
    material = wall.material_hint or wall.inputs.get("material_hint")
    thickness = wall.thickness_m or wall.inputs.get("thickness_cm")
    wall_system = wall.wall_system or wall.inputs.get("wall_system")
    location = wall.interior_exterior_hint or wall.inputs.get("interior_exterior_hint")
    
    if wall_system and "masonry" in wall_system:
        if thickness:
            th_cm = float(thickness) * 100 if float(thickness) < 1 else float(thickness)
            parts.append(f"bloques {int(th_cm)}cm")
        else:
            parts.append("bloques")
    elif wall_system and "drywall" in wall_system:
        parts.append("sheetrock/drywall")
    elif wall_system and "concrete" in wall_system:
        parts.append("hormigón armado")
    
    if location:
        parts.append(location)
    
    if not material and not wall_system:
        parts.append(f"(layer: {wall.id})")  # fallback al layer solo si no hay nada mejor
    
    return " ".join(parts)
```

PROBLEMA 2 - UNIDADES: Los muros de bloques se presupuestan por m2 (área de muro), no por m3 (volumen). El quantifier debe producir:
- wall_masonry_area → m2 (largo × alto) — para presupuestar bloques y pañete
- wall_volume → m3 SOLO para muros de hormigón armado

FIX: En el quantifier, cuando item_type es wall-related:
- Si material es masonry/bloques: unit = "m2", quantity = length × height
- Si material es concrete/hormigón: unit = "m3", quantity = length × height × thickness
- Si material es desconocido: unit = "m2" por defecto (la mayoría de muros residenciales son bloques)
```

### Verificación terminal:
```bash
# Post-run, verificar en el Excel output:
# 1. Descripciones deben decir "Muro bloques 15cm interior" no "Muro tipo json-wall-a-wall"
# 2. Unidades deben ser m2 para muros de bloques, no m3
python -c "
import json
with open('output/LAST_RUN/budget_output.json') as f:
    data = json.load(f)
for t in data['takeoffs'][:20]:
    if 'wall' in t.get('item_type', ''):
        desc = t.get('inputs', {}).get('takeoff_description', '')
        print(f'{t[\"item_type\"]:30s} {t[\"unit\"]:4s} {t[\"quantity\"]:10.2f} {desc[:60]}')
"
```

---

## BLOQUE 4 — Fix APU Matcher para leer descripción real

### Prompt Claude Code:

```
@pricing/apu_matcher.py El APUMatcher tiene match rate = 0% porque _signature_from_inputs busca campos estructurados (location, tile_size) que no existen en los takeoffs reales. Los datos útiles están en takeoff_description y context_tags.

FIX: Modificar _signature_from_inputs (o el método equivalente que genera la signature para matching) para:

1. SIEMPRE leer takeoff_description de inputs si existe
2. SIEMPRE leer context_tags de inputs si existe
3. SIEMPRE leer material_hint de inputs si existe
4. Parsear takeoff_description para extraer:
   - Tipo de bloque: buscar "bloque" + número (6, 8, 12, 15, 20)
   - Espesor: buscar "espesor" + número + "cm"
   - Ubicación: buscar "interior", "exterior", "caseta", etc.
   - Material: buscar "masonry", "hormigón", "concreto", "bloques"
   - Sección: buscar patrón NxN o N×N (para columnas/vigas)

5. Usar esta info parseada para matchear contra los APUs del constructor. Ejemplos:
   - "Muro bloques 15cm interior" → busca APU con "bloque" + "15" o "6\"" o "6 IN"
   - "Muro bloques 20cm exterior" → busca APU con "bloque" + "20" o "8\"" o "8 IN"
   - "Columna sección 0.30×0.20 m" → busca APU con "columna" + "0.30" o "C1"

6. En los APUs del constructor, las equivalencias de espesor son:
   - 10cm = bloques 4" (4 pulgadas)
   - 15cm = bloques 6" (6 pulgadas)  
   - 20cm = bloques 8" (8 pulgadas)
   - 30cm = bloques 12" (12 pulgadas)

Después de implementar, re-corre el matching contra budget_output.json SIN re-correr el pipeline:

python -c "
from pricing.excel_price_loader import load_constructor_pricing
from pricing.apu_matcher import APUMatcher
import json

store = load_constructor_pricing('data/Lista de precios-analisis-MO.xlsx')
matcher = APUMatcher(store)

with open('RUTA_AL_ULTIMO_budget_output.json') as f:
    data = json.load(f)

matched = 0
total = 0
for t in data['takeoffs']:
    if t.get('item_type') in ('wall_gross_area', 'wall_net_area', 'wall_volume', 'wall_finish_plaster', 'column_concrete_volume'):
        total += 1
        result = matcher.match_from_inputs(t.get('inputs', {}), t.get('item_type', ''))
        if result:
            matched += 1
            print(f'MATCH: {t[\"inputs\"].get(\"takeoff_description\",\"\")[:50]} → {result.description[:50]}')
        else:
            print(f'MISS:  {t[\"inputs\"].get(\"takeoff_description\",\"\")[:50]}')

print(f'Match rate: {matched}/{total} = {matched/total*100:.1f}%')
"

Guarda el output en output/apu_matching_v3_log.txt
```

### Verificación terminal:
```bash
# El test ya está en el prompt. Buscar match rate > 30%
cat output/apu_matching_v3_log.txt | tail -5
```

---

## BLOQUE 5 — Re-correr pipeline completo y comparar

### Prompt Claude Code:

```
@scripts/compare_gebsa.py @dupla_run_gebsa.py Correr el pipeline completo para las 4 disciplinas con los fixes aplicados y generar BASELINE_GEBSA_V3.md.

Pasos:
1. Correr cada disciplina:
   python dupla_run_gebsa.py --only arquitectura --pricing-excel "data/Lista de precios-analisis-MO.xlsx"
   python dupla_run_gebsa.py --only estructura --pricing-excel "data/Lista de precios-analisis-MO.xlsx"
   python dupla_run_gebsa.py --only electrico --pricing-excel "data/Lista de precios-analisis-MO.xlsx"
   python dupla_run_gebsa.py --only sanitario --pricing-excel "data/Lista de precios-analisis-MO.xlsx"

2. Correr comparación contra GIV real:
   python scripts/compare_gebsa.py --output-dir output/ --real "data/GIV00001 (1).bc3" --output-file output/BASELINE_GEBSA_V3.md

3. En BASELINE_GEBSA_V3.md agregar sección "CAMBIOS VS V2":
   - Cantidades: ¿bajaron las cantidades absurdas de muros? (V2 tenía 18,641 m2 pañete)
   - Descripciones: ¿cuántas partidas ahora tienen descripción con tipo de bloque vs "Muro" genérico?
   - APU Match: ¿cuántas partidas usan precio del constructor vs catálogo BC3?
   - Unidades: ¿muros ahora en m2 en vez de m3?
```

### Verificación terminal:
```bash
cat output/BASELINE_GEBSA_V3.md
```

---

## BLOQUE 6 — Cablear rebar.py al quantifier de estructura

### Prompt Claude Code:

```
@disciplines/estructura/quantifier.py @disciplines/estructura/rebar.py El quantifier de estructura es un wrapper vacío que filtra takeoffs del monolítico. Tiene 37 líneas. rebar.py tiene 309 líneas con un parser de notación de refuerzo dominicano + catálogo ASTM A615 completo que NADIE usa.

FIX: Reescribir disciplines/estructura/quantifier.py para que calcule cantidades reales:

1. HORMIGÓN (columnas y vigas):
   - Leer section_width_m, section_height_m, length_m o span_m, count de los inputs
   - Volumen = width × height × length × count
   - Generar takeoff con unit="m3", formula explícita

2. ACERO (usando rebar.py):
   - Leer reinforcement_main_bars y reinforcement_stirrups de los inputs
   - Si existen: llamar parse_reinforcement() y calculate_main_bar_weight() de rebar.py
   - Generar takeoff con unit="kg", formula con notación original

3. ENCOFRADO:
   - Columnas: perímetro × altura × count = m2
   - Vigas: (2×alto + ancho_inferior) × longitud × count = m2

4. LOSAS:
   - Leer area_m2, thickness_m de inputs
   - Volumen hormigón = area × thickness
   - Acero estimado por ratio si no hay notación (120 kg/m3 para losa, ajustable)

5. Si los inputs no tienen los campos necesarios, fallback al quantifier monolítico actual (no romper lo que funciona).

Ejemplo de output esperado para una columna C1 0.30×0.20, 3m, 4#6+2#5, Est.3/8@0.15, count=8:
- column_concrete_volume: 0.30×0.20×3.0×8 = 1.44 m3
- column_reinforcement_kg: rebar(4#6+2#5, L=3.0) × 8 = X kg  
- column_formwork_area: (0.30+0.20)×2 × 3.0 × 8 = 24.0 m2

Importar desde rebar.py:
from .rebar import parse_reinforcement, ASTM_A615_CATALOG
```

### Verificación terminal:
```bash
python -c "
from disciplines.estructura.quantifier import quantify
# Si no puedes importar fácilmente, al menos verifica que rebar se importa:
from disciplines.estructura.rebar import parse_reinforcement, ASTM_A615_CATALOG
print(f'ASTM catalog: {len(ASTM_A615_CATALOG)} bar sizes')
parsed = parse_reinforcement('4#6+2#5', '3/8@0.15')
print(f'Parsed: {parsed}')
"
```

---

## BLOQUE 7 — Volumetría básica zapatas/vigas

### Prompt Claude Code:

```
@disciplines/estructura/quantifier.py Extender el quantifier de estructura con volumetría para zapatas y vigas según las fórmulas reales del constructor.

ZAPATA AISLADA:
- Volumen hormigón = largo × ancho × peralte × cantidad
- Hormigón de limpieza = largo × ancho × 0.05 × cantidad (5cm de lechada)
- Encofrado = perímetro × peralte × cantidad
- Acero: si hay notación de refuerzo, usar rebar.py; si no, ratio 80 kg/m3

VIGA DE AMARRE / DINTEL:
- Volumen hormigón = ancho × alto × longitud × cantidad
- Encofrado = (2 × alto + ancho) × longitud × cantidad (3 caras)
- Acero: si hay notación, usar rebar.py; si no, ratio 100 kg/m3

VIGA AÉREA:
- Volumen hormigón = ancho × alto × longitud × cantidad
- Encofrado = (2 × alto + ancho_inferior) × longitud × cantidad (fondo + 2 laterales)
- Apuntalamiento: longitud × cantidad en ML (partida separada)

Los inputs vienen del Vision/CAD como:
- section_width_m, section_height_m (o section como "0.30x0.40")
- span_m o length_m
- count
- reinforcement_main_bars, reinforcement_stirrups
- element_subtype: "zapata", "viga_amarre", "dintel", "viga_aerea"

Si section viene como string "0.30x0.40", parsearlo a width=0.30, height=0.40.

Cada takeoff debe tener formula explícita para trazabilidad:
formula="0.30×0.40×5.20×6 = 3.744 m³"
```

### Verificación terminal:
```bash
python -c "
# Verificar que las fórmulas producen resultados correctos
# Zapata Z-1: 1.80×1.80×0.45, qty=8
vol = 1.80 * 1.80 * 0.45 * 8
limpieza = 1.80 * 1.80 * 0.05 * 8
encofrado = (1.80*4) * 0.45 * 8
print(f'Zapata Z-1 (x8): hormigón={vol:.3f} m3, limpieza={limpieza:.3f} m3, encofrado={encofrado:.2f} m2')
# Esperado: 11.664 m3, 1.296 m3, 25.92 m2
"
```

---

## BLOQUE 8 — Re-correr y generar baseline final

### Prompt Claude Code:

```
Correr el pipeline completo con TODOS los fixes y generar el baseline final de la semana 3.

1. Correr las 4 disciplinas:
python dupla_run_gebsa.py --only arquitectura --pricing-excel "data/Lista de precios-analisis-MO.xlsx"
python dupla_run_gebsa.py --only estructura --pricing-excel "data/Lista de precios-analisis-MO.xlsx"
python dupla_run_gebsa.py --only electrico --pricing-excel "data/Lista de precios-analisis-MO.xlsx"
python dupla_run_gebsa.py --only sanitario --pricing-excel "data/Lista de precios-analisis-MO.xlsx"

2. Comparar:
python scripts/compare_gebsa.py --output-dir output/ --real "data/GIV00001 (1).bc3" --output-file output/BASELINE_GEBSA_V3_FINAL.md

3. Agregar al reporte estas métricas adicionales:
- Comparación V1 vs V2 vs V3_FINAL en tabla
- Match rate del APUMatcher por disciplina
- Cuántas partidas tienen fórmula explícita vs ratio estimado
- Cuántos takeoffs usan rebar.py vs "acero estimado"
- Top 5 partidas con mejor mejora de precio vs V1

Guardar en output/BASELINE_GEBSA_V3_FINAL.md
```

### Verificación terminal:
```bash
cat output/BASELINE_GEBSA_V3_FINAL.md
# Comparar los números clave:
# - Partidas matcheadas: V1=69 → V3 target >120
# - Precios ±25%: V1=4.3% → V3 target >20%
# - APU match rate: V1=0% → V3 target >30%
# - Cantidades ±50%: V1=20.3% → V3 target >40%
```

---

## ORDEN DE EJECUCIÓN

```
BLOQUE 1 → commit → BLOQUE 2 → commit → re-correr pipeline → verificar cantidades
    ↓
BLOQUE 3 → commit → BLOQUE 4 → commit → BLOQUE 5 (re-correr + comparar)
    ↓
BLOQUE 6 → commit → BLOQUE 7 → commit → BLOQUE 8 (baseline final)
```

Los bloques 1-2 son los más impactantes. Si solo corres esos y re-corres el pipeline, ya deberías ver las cantidades bajar de 18,000 m² a rangos razonables y los muros con descripción de tipo de bloque.

Los bloques 6-7 (rebar + volumetría) solo aplican a la disciplina de estructura. Si estructura no es prioridad esta semana, puedes posponerlos.

El bloque 4 (APU matcher) depende de que los bloques 1-3 estén funcionando — si las descripciones siguen siendo "Muro" genérico, el matcher no va a encontrar nada.
