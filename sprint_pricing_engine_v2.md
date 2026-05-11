# Sprint: Motor de Pricing Flexible + Baseline GEBSA IV
**Rama:** ai_training
**Duración:** 3 semanas (15 días hábiles)
**Equipo:** Ciprian (dev + ingeniería fuerte), Miji (dev + ingeniería)

---

## CONTEXTO: Por qué pricing primero

El pipeline genera 383 partidas para GEBSA IV. El presupuesto real tiene 607 con 415 precios distintos. El output tiene 87 precios — todos sacados del catálogo BC3 genérico.

Arreglar Vision o cuantificación sin pricing correcto es inútil: un presupuesto con cantidades perfectas pero precios de catálogo no le sirve al constructor. En cambio, un presupuesto con detección al 70% pero precios reales del constructor ya es una herramienta de trabajo.

La constructora tiene un Excel con 3 hojas que contienen todo lo necesario:
- **"analisis may25"** → 204 APUs completos (partida → materiales + MO + cantidades = precio unitario)
- **"Lista de precios may25"** → ~500 materiales con precios actualizados
- **"MO 25"** → ~600 actividades de mano de obra con precios
El excel esta en esta ruta: data\Lista de precios-analisis-MO.xlsx

El sistema necesita ingerir este formato (y cualquier otro similar) como input del proyecto.

---

## SEMANA 1 — Pricing Store + Ingestion (Día 1–5)

### Ciprian — Track: Schema y parseo del Excel del constructor

**Día 1: Definir el schema interno de pricing**

Crear `pricing/schemas.py` con tres modelos:

```python
@dataclass
class MaterialPrice:
    code: str                    # "1.1" o código interno
    description: str             # "Acero Ø3/8,1/2,3/4 G60"
    unit: str                    # "QQ", "M2", "FDA", etc.
    unit_price: float            # precio unitario en DOP
    category: str                # "ACEROS-MALLAS-ALAMBRES"
    updated_date: str | None     # fecha de actualización
    source: str                  # nombre del archivo fuente

@dataclass 
class LaborRate:
    code: str                    # "1.1", "2.0"
    description: str             # "EXCAVACION EN TIERRA"
    unit: str                    # "M³", "M²", "días"
    unit_price: float            # precio por unidad
    category: str                # "EXCAVACIONES"
    source: str

@dataclass
class APUBreakdown:
    code: str                    # "6.01"
    description: str             # "COLUMNAS C1 (0.30X0.20)"
    unit: str                    # "M³", "ML", "M²"
    unit_price_total: float      # precio unitario calculado
    category: str                # "COLUMNAS"
    components: list[APUComponent]  # desglose
    source: str

@dataclass
class APUComponent:
    description: str             # "Cemento gris"
    quantity: float              # 7.0
    unit: str                    # "FDA"
    unit_price: float            # 540.75
    subtotal: float              # 3785.25
    component_type: str          # "material" | "labor" | "equipment" | "overhead"

@dataclass
class PricingStore:
    materials: dict[str, MaterialPrice]
    labor: dict[str, LaborRate]
    apus: dict[str, APUBreakdown]
    metadata: dict               # proyecto, fecha, fuente
```

**Día 2–3: Parser del Excel del constructor**

Crear `pricing/excel_price_loader.py`:

```python
def load_constructor_pricing(excel_path: str) -> PricingStore:
    """
    Parsea el Excel del constructor (formato Dupla Constructora).
    Detecta automáticamente las 3 hojas:
    - Hoja con "analisis" en el nombre → APUs
    - Hoja con "lista" o "precios" → materiales
    - Hoja con "MO" o "mano" → mano de obra
    """
```

El parser debe ser robusto a:
- Números de fila como float (3.0199999 en vez de 3.02) — redondear a 2 decimales
- Filas vacías entre partidas
- Formato inconsistente (a veces "FDA", a veces "Fda", a veces "fd")
- Sub-partidas sin precio total explícito (hay que sumar componentes)

Tests concretos contra el Excel real:
- Parsear "analisis may25" y obtener ≥190 APUs de 204
- Parsear "Lista de precios may25" y obtener ≥450 materiales
- Parsear "MO 25" y obtener ≥500 actividades
- Verificar: APU "HORMIGON 140 KG/CM2" = 7,121.15 DOP/M3
- Verificar: APU "COLUMNAS C1 (0.30X0.20)" tiene componentes de hormigón + acero + encofrado + MO

**Día 4: Serialización y caché**

El PricingStore debe poder:
- Serializarse a JSON para caché (no re-parsear el Excel cada corrida)
- Cargarse desde JSON en <100ms
- Guardarse en `data/pricing_cache/{project_id}_pricing.json`

**Día 5: Tests unitarios del parser**

- Crear `tests/test_pricing_loader.py`
- Usar el Excel real como fixture de test
- Verificar que el round-trip (Excel → PricingStore → JSON → PricingStore) no pierde datos

---

### Miji — Track: Integración al pipeline + comparador

**Día 1–2: Integrar PricingStore al pipeline**

El pipeline hoy hace esto en `core/pipeline.py`:
```python
snapshot = _load_construcosto_if_available()  # ← ConstruCosto genérico
budget = build_final_budget(..., construcosto_snapshot=snapshot)
```

Modificar para que acepte PricingStore del constructor:
```python
# En dupla_run_gebsa.py, agregar argumento:
parser.add_argument("--pricing-excel", type=str, help="Excel de precios del constructor")

# En process_discipline(), antes de build_budget_from_sources:
if pricing_excel:
    pricing_store = load_constructor_pricing(pricing_excel)
    shared["pricing_store"] = pricing_store
```

Modificar `build_final_budget()` para que cuando un PricingStore está disponible:
1. Busque match por descripción entre takeoff y APU del constructor
2. Si hay match: use el precio del APU y genere la descomposición (~D) con componentes reales
3. Si no hay match: fallback al precio del catálogo BC3 (comportamiento actual)

El match entre takeoff y APU puede ser:
- Exacto por keywords: "columna" + "0.30x0.20" → "COLUMNAS C1 (0.30X0.20)"
- Por embeddings si hay ambigüedad (ya existe la infraestructura)

**Día 3–4: Script de comparación output vs GIV real**

Crear `scripts/compare_gebsa.py`:

```bash
python scripts/compare_gebsa.py \
    --output-dir output/presupuesto_arquitectura.bc3 output/presupuesto_estructura.bc3 ... \
    --real data/GIV00001.bc3
```

Output:
```
COMPARACIÓN GEBSA IV — Output vs Real
======================================

COBERTURA:
  Partidas output: 383
  Partidas real: 607
  Matcheadas: 245 (40%)
  Solo en output: 138
  Solo en real: 362

PRECISIÓN DE PRECIOS (sobre matcheadas):
  Dentro de ±10%: 45 (18%)
  Dentro de ±25%: 89 (36%)
  Dentro de ±50%: 156 (64%)
  Fuera de ±50%: 89 (36%)

PRECISIÓN DE CANTIDADES (sobre matcheadas):
  [similar breakdown]

TOP 10 PARTIDAS CON MAYOR DELTA DE IMPORTE:
  1. Hormigón columnas: output $X vs real $Y (Δ = $Z)
  ...
```

El matching entre output y real se hace por:
- Similitud de descripción (embeddings o fuzzy matching)
- Mismo tipo de elemento + misma unidad
- NO por código (son esquemas diferentes)

**Día 5: Correr comparación y documentar baseline**

Producir `BASELINE_GEBSA_V1.md` con los números reales. Este es el punto de referencia para medir todo lo que sigue.

---

## SEMANA 2 — Pricing Match + Wiring (Día 6–10)

### Ambos — Focus: Hacer que el pricing del constructor realmente funcione

**Ciprian (Día 6–8): APU Matcher con IA**

El problema central: el pipeline genera "Columna C-1, sección 0.40×0.40 m" y necesita encontrar el APU correcto del constructor.

Crear `pricing/apu_matcher.py`:

```python
class APUMatcher:
    def __init__(self, pricing_store: PricingStore):
        self.store = pricing_store
        self.embeddings = None  # lazy load
    
    def match(self, takeoff: QuantityTakeoff) -> APUBreakdown | None:
        """
        Intenta matchear un takeoff con un APU del constructor.
        
        Estrategia:
        1. Keyword match directo (elemento + dimensiones)
        2. Si no: embedding similarity > 0.85
        3. Si no: None (usar fallback de catálogo)
        """
    
    def match_batch(self, takeoffs: list[QuantityTakeoff]) -> dict[str, APUBreakdown | None]:
        """Match múltiples takeoffs de una vez (más eficiente para embeddings)."""
```

Reglas de match por tipo de elemento:
- **Columnas**: match por sección (0.30x0.20 → C1, 0.40x0.20 → C2)
- **Vigas**: match por sección + tipo (amarre, enrase, dintel)
- **Muros bloques**: match por espesor + refuerzo (8" 3/8@0.40)
- **Losas**: match por tipo + espesor (plana H=0.12, aligerada 20cm)
- **Pañetes**: match por ubicación (interior, exterior, techo, vigas)
- **Pisos**: match por material (coralina 30x60, porcelanato)

El match no necesita ser perfecto — necesita ser correcto en >70% de las partidas de alto impacto económico (estructura y acabados principales).

**Miji (Día 6–8): Wiring del APUMatcher al budget composer**

Modificar `budget/composer.py` para que:
1. Reciba el APUMatcher como parámetro
2. Para cada takeoff matcheado, genere la línea de presupuesto con:
   - Precio del APU del constructor (no del catálogo)
   - Descomposición (~D) con componentes reales del APU
   - Flag indicando source: "constructor_apu" vs "bc3_catalog"
3. El Excel de salida tenga una columna adicional: "Fuente precio"

**Ambos (Día 9–10): Re-correr pipeline con pricing del constructor**

```bash
python dupla_run_gebsa.py --only arquitectura --pricing-excel "data/Lista_de_precios-analisis-MO.xlsx"
```

Comparar output nuevo vs GIV real:
- ¿Cuántas partidas ahora matchean un APU del constructor?
- ¿Mejoró la precisión de precios?
- ¿Los ~D tienen componentes reales?

---

## SEMANA 3 — Quantificación + Re-medición (Día 11–15)

### Ciprian (Día 11–13): Cablear rebar.py y volumetría básica

Ahora que el pricing está conectado, las cantidades importan más.

**Día 11: Conectar rebar.py al quantifier de estructura**

`disciplines/estructura/quantifier.py` hoy filtra. Debe calcular:

```python
from .rebar import parse_reinforcement, calculate_main_bar_weight, calculate_stirrup_weight

def quantify(levels):
    takeoffs = []
    for level in levels:
        for elem in level.structural_elements:
            inputs = elem.inputs or {}
            
            # Hormigón: geometría directa
            if elem.element_type in ("column", "beam"):
                w = float(inputs.get("section_width_m", 0))
                h = float(inputs.get("section_height_m", 0))
                length = float(inputs.get("length_m") or inputs.get("span_m", 0))
                count = int(inputs.get("count", 1))
                if w > 0 and h > 0 and length > 0:
                    vol = w * h * length * count
                    takeoffs.append(QuantityTakeoff(
                        item_key=f"{elem.id}_concrete",
                        item_type=f"{elem.element_type}_concrete_volume",
                        unit="m3",
                        quantity=round(vol, 3),
                        formula=f"{w}×{h}×{length}×{count}",
                    ))
            
            # Acero: rebar.py
            main_bars_notation = inputs.get("reinforcement_main_bars")
            stirrups_notation = inputs.get("reinforcement_stirrups")
            if main_bars_notation:
                parsed = parse_reinforcement(main_bars_notation, stirrups_notation)
                weight = calculate_main_bar_weight(parsed.main_bars, length)
                takeoffs.append(QuantityTakeoff(
                    item_key=f"{elem.id}_rebar",
                    item_type=f"{elem.element_type}_reinforcement_kg",
                    unit="kg",
                    quantity=round(weight["total_kg"] * count, 2),
                    formula=f"rebar({main_bars_notation}, L={length}m) × {count}",
                ))
    
    return takeoffs
```

**Día 12–13: Volumetría básica para zapatas y losas**

Mismo patrón: geometría directa desde los inputs de Vision, sin estimaciones.

### Miji (Día 11–13): Mejorar el comparador + dashboard de métricas

Extender `compare_gebsa.py` para:
- Comparar por disciplina (no solo global)
- Separar errores de identificación vs errores de pricing
- Generar reporte markdown legible para presentar al cliente

### Ambos (Día 14–15): Re-medición final y decisión

Correr pipeline completo con:
- Pricing del constructor activo
- rebar.py cableado
- Volumetría básica implementada

Comparar los 3 puntos:
1. **Baseline semana 1** (output original)
2. **Post-pricing semana 2** (precios reales, mismas cantidades)
3. **Post-quantificación semana 3** (precios reales + cantidades calculadas)

Esto muestra exactamente cuánto aporta cada mejora.

---

## Entregables del sprint

1. `pricing/schemas.py` — Schema del PricingStore
2. `pricing/excel_price_loader.py` — Parser del Excel del constructor
3. `pricing/apu_matcher.py` — Matcher IA takeoff → APU
4. `scripts/compare_gebsa.py` — Comparador output vs real
5. `disciplines/estructura/quantifier.py` — Quantifier real (no wrapper)
6. `BASELINE_GEBSA_V1.md` — Medición inicial
7. `BASELINE_GEBSA_V2.md` — Medición post-sprint

---

## Lo que este sprint NO incluye (siguiente sprint)

- Organización por edificio/nivel (el real tiene Bloque A/B + niveles — el pipeline aún no)
- Mejoras a Vision prompts (viene después de que pricing + quantities funcionen)
- Interfaz web para subir Excels (primero funciona desde CLI)
- Soporte para otros formatos de pricing que no sea el del constructor actual
- ConstruCosto como fuente secundaria de precios
