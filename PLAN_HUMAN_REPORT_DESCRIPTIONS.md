# Plan: Descripciones humanas en coordination_report_human.md

## Objetivo

El reporte `coordination_report_human.md` actualmente muestra los clashes con información técnica cruda:

```
- `incident_0001` | razon: low confidence signal
  layers: `PLAFON / SOLAR`
  accion: Revisar el par directamente y revisar con validacion acotada.
```

Queremos que salga así:

```
- `incident_0001` | razon: low confidence signal
  **descripcion probable:** posible interferencia de plafón con losa solar
  layers: `PLAFON / SOLAR`
  accion: Verificar si el plafón (PLAFON) interfiere con la losa solar (SOLAR) en este nivel, luego revisar con validacion acotada.
```

---

## Archivo a modificar

**`coordination/reporting/reporting.py`** — único archivo con cambios.  
No tocar: `technical_coordination_report.md`, schemas JSON, ni ningún otro módulo.

---

## Cambios a implementar

### Paso 1 — Agregar tabla `_LAYER_ELEMENT_LABELS` (módulo level)

Tabla estática de lookup layer → label legible en español. Sin dependencias externas.

```python
_LAYER_ELEMENT_LABELS: dict[str, str] = {
    "SOLAR":      "losa solar",
    "PLAFON":     "plafón",
    "PLAFONES":   "plafón",
    "VIGA":       "viga",
    "VIGAS":      "viga",
    "COLUMNA":    "columna",
    "COLUMNAS":   "columna",
    "MURO":       "muro",
    "MUROS":      "muro",
    "PUERTA":     "puerta",
    "PUERTAS":    "puerta",
    "VENTANA":    "ventana",
    "VENTANAS":   "ventana",
    "LOSA":       "losa",
    "LOSAS":      "losa",
    "CIMIENTO":   "cimiento",
    "ZAPATA":     "zapata",
    "ESCALERA":   "escalera",
    "ESCALERAS":  "escalera",
    "TUBERIA":    "tubería",
    "TUBERIAS":   "tubería",
    "TUB":        "tubería",
    "DUCTO":      "ducto",
    "DUCTOS":     "ducto",
    "DRENAJE":    "drenaje",
    "SANIT":      "instalación sanitaria",
    "PANEL":      "tablero eléctrico",
    "LUMIN":      "luminaria",
}
```

---

### Paso 2 — Nueva función `_layer_to_element_label(layer: str) -> str`

Busca el token más largo de `_LAYER_ELEMENT_LABELS` que esté contenido en `layer.upper()`.  
Si no hay match, devuelve el layer original sin modificar (nunca inventa).

```python
def _layer_to_element_label(layer: str) -> str:
    normalized = layer.upper()
    best_key = max(
        (key for key in _LAYER_ELEMENT_LABELS if key in normalized),
        key=len,
        default=None,
    )
    return _LAYER_ELEMENT_LABELS[best_key] if best_key else layer
```

---

### Paso 3 — Nueva función `_human_clash_description(layer_a, layer_b) -> str | None`

Regla: si al menos uno de los dos layers tuvo un match en la tabla (su label es distinto al layer original), armar una frase. Si ninguno matcheó, devolver `None` — no inventar texto.

Pares con frase específica (prioridad sobre la genérica):

| Label A contiene | Label B contiene | Frase |
|---|---|---|
| puerta | viga | "posible choque de puerta con viga" |
| puerta | columna | "posible choque de puerta con columna" |
| plafón | losa solar | "posible interferencia de plafón con losa solar" |
| plafón | viga | "posible interferencia de plafón con viga" |
| plafón | losa | "posible interferencia de plafón con losa" |
| tubería | losa | "posible paso de tubería a través de losa" |
| tubería | viga | "posible cruce de tubería con viga" |
| muro | viga | "posible traslape de muro con viga" |
| escalera | losa | "posible traslape de escalera con losa" |

Si ningún par específico aplica, frase genérica:  
`f"posible interferencia de {label_a} con {label_b}"`

La comparación de pares debe ser **order-insensitive** (A/B o B/A dan el mismo resultado).

```python
def _human_clash_description(layer_a: str, layer_b: str) -> str | None:
    label_a = _layer_to_element_label(layer_a)
    label_b = _layer_to_element_label(layer_b)
    # Si ninguno matcheó, no generar descripción
    if label_a == layer_a and label_b == layer_b:
        return None
    labels = frozenset({label_a, label_b})
    _SPECIFIC_PHRASES: list[tuple[frozenset[str], str]] = [
        (frozenset({"puerta", "viga"}),           "posible choque de puerta con viga"),
        (frozenset({"puerta", "columna"}),         "posible choque de puerta con columna"),
        (frozenset({"plafón", "losa solar"}),      "posible interferencia de plafón con losa solar"),
        (frozenset({"plafón", "viga"}),            "posible interferencia de plafón con viga"),
        (frozenset({"plafón", "losa"}),            "posible interferencia de plafón con losa"),
        (frozenset({"tubería", "losa"}),           "posible paso de tubería a través de losa"),
        (frozenset({"tubería", "viga"}),           "posible cruce de tubería con viga"),
        (frozenset({"muro", "viga"}),              "posible traslape de muro con viga"),
        (frozenset({"escalera", "losa"}),          "posible traslape de escalera con losa"),
    ]
    for pair, phrase in _SPECIFIC_PHRASES:
        if pair.issubset(labels):
            return phrase
    return f"posible interferencia de {label_a} con {label_b}"
```

> Nota: `_SPECIFIC_PHRASES` puede definirse como constante a nivel de módulo para evitar recrearla en cada llamada.

---

### Paso 4 — Enriquecer `_incident_card()` con campo `human_description`

En la función `_incident_card()`, después de calcular `layers`, agregar:

```python
"human_description": _human_clash_description(
    layers[0] if layers else "",
    layers[1] if len(layers) > 1 else "",
),
```

El campo queda en el dict del card. Si es `None`, simplemente no se muestra.

---

### Paso 5 — Enriquecer `_recommended_action()` para usar element labels

Agregar parámetro `layers: tuple[str, str] = ("", "")`.

Cuando ambos layers tienen un label conocido (distinto al layer original), insertar los nombres en el texto de acción:

Antes:
```
"Revisar el par directamente y revisar con validacion acotada."
```

Después (ejemplo con PLAFON / SOLAR, disciplines ARCH/STRUC):
```
"Verificar si el plafón (PLAFON) interfiere con la losa solar (SOLAR) en este nivel, luego revisar con validacion acotada."
```

La lógica: si `label_a != layer_a` o `label_b != layer_b`, reemplazar el prefijo genérico "Revisar el par directamente" con `f"Verificar si {label_a} ({layer_a}) interfiere con {label_b} ({layer_b}) en este nivel"`. El sufijo de urgencia (`urgency`) no cambia.

Actualizar el call en `_incident_card()`:
```python
"recommended_action": _recommended_action(
    disciplines=disciplines,
    severity=severity,
    layers=layers,
),
```

---

### Paso 6 — Actualizar `render_coordination_human_report_markdown()`

En los dos loops de incidents (`defendable` y `validation`), cuando `card["human_description"]` no es `None`, insertar una línea adicional en el bloque del incident:

```python
line = (
    f"- `{card['incident_id']}` | razon: {card['validation_reason']}"
    f"\n  nivel: `{card['level_id']}`"
    ...
)
# NUEVO: insertar descripcion_probable si existe
if card.get("human_description"):
    line = line.replace(
        f"\n  nivel:",
        f"\n  **descripcion probable:** {card['human_description']}\n  nivel:",
    )
```

---

## Criterio de aceptación

Correr el run de TORTUGA y verificar en `coordination_report_human.md`:

1. **Al menos un incident** con `layers: PLAFON / SOLAR` tiene la línea:  
   `**descripcion probable:** posible interferencia de plafón con losa solar`

2. **Ningún incident** tiene descripción que sea una repetición literal del nombre del layer (e.g., `"posible interferencia de PLAFON con SOLAR"` no es válido).

3. **Los incidents sin match** en la tabla no tienen línea `descripcion probable` (sin texto vacío ni placeholder).

4. `technical_coordination_report.md` y todos los JSONs de salida **no cambian**.

5. Los tests existentes en `tests/` pasan sin modificación.

---

## Guardrails

- NO tocar `render_coordination_report_markdown()` (reporte técnico).
- NO cambiar schemas JSON de salida.
- NO agregar dependencias externas.
- NO inventar nombres de habitaciones, ejes o personas.
- Si `human_description` es `None`, no emitir la línea — nunca poner string vacío.
- La tabla `_LAYER_ELEMENT_LABELS` es estática en código, no cargada de archivo.
