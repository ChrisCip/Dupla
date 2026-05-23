# Guía de Revisión Manual de Clashes — General
**Generado el:** 2026-05-23
**Preparado por:** Sistema de Coordinación Dupla
**Modo:** Consolidado por proyecto (automático)

## Proyectos incluidos

| Proyecto | Archivo fuente |
|---|---|
| `NASAS_09` | `aps_integration/NASAS 09/NASAS arquitectura/REVISION_CLASHES_ARQUITECTO_NASAS_09.md` |
| `SERENA_18` | `ARQUITECTURA/SERENA 18/SERENA 18/REVISION_CLASHES_ARQUITECTO_SERENA_18.md` |
| `TORTUGA_C40` | `ARQUITECTURA/TORTUGA C40/TORTUGA C40/REVISION_CLASHES_ARQUITECTO_TORTUGA_C40.md` |

---

---

> **Cómo usar este documento**
> Este reporte es tu bitácora de trabajo. El programa detectó posibles conflictos entre planos de **Arquitectura, Estructura, Eléctrico, Hidrosanitario y Mecánico**. Tu labor es abrir los DWGs, ir a cada coordenada indicada, mirar con tus propios ojos y decidir: ¿es un clash real o es ruido? Al final de cada sección hay una tabla de validación donde vas marcando.

---

## INSTRUCCIONES GENERALES

### Paso 1 — Abrir los dos archivos en AutoCAD

1. Abre AutoCAD.
2. Abre el **Plano A** (primera disciplina del par) desde `Archivo → Abrir`.
3. Abre el **Plano B** (segunda disciplina) en la misma sesión: `Archivo → Abrir` nuevamente.
4. Para ver ambos superpuestos: activa **"Ventanas en mosaico"** (`Ctrl + Alt + T`) o usa `Vista → Ventanas → Mosaico vertical`.
5. Alternativa: usa **DWG Compare** (`dwgcompare` en la línea de comandos) si tienes AutoCAD 2019+.

### Paso 2 — Usar el comando ZOOM para ir a las coordenadas

Cada clash tiene un comando AutoCAD listo. Cópialo y pégalo en la **Línea de Comandos**:
```
Z W X_MIN,Y_MIN X_MAX,Y_MAX
```
Ejemplo: `Z W 148000,-163000 158000,-154000`

> **Nota:** Todos los valores están en **milímetros**. Si tu DWG está en metros, divide entre 1,000.

### Paso 3 — Controlar las capas

1. Escribe `LA` para abrir el Administrador de Capas.
2. Apaga todas las capas (`Ctrl + A` → apaga ojo).
3. Prende solo las dos capas del clash que estás revisando.
4. Verifica si las geometrías se solapan.
5. Al terminar: `LA` → `Ctrl + A` → enciende todas.

### Paso 4 — Decisión final

| Decisión | Significado |
|---|---|
| ✅ **CLASH REAL** | Conflicto real de coordinación que hay que resolver. |
| ❌ **FALSO POSITIVO** | Ruido gráfico (marcos de hoja, cotas, anotaciones). |
| ⚠️ **PENDIENTE** | Necesitas más información antes de decidir. |

---


---

## PROYECTO — NASAS_09

_Fuente: `aps_integration/NASAS 09/NASAS arquitectura/REVISION_CLASHES_ARQUITECTO_NASAS_09.md`_

# Guía de Revisión Manual de Clashes — NASAS 09
**Generado el:** 2026-05-23
**Preparado por:** Sistema de Coordinación Dupla
**Para:** Arquitecto revisor
**Modo:** Validación campo a campo en AutoCAD

## Estado — Sin incidencias primarias

> El análisis completó 10 pares programados y no encontró conflictos geométricos entre elementos estructurales primarios (muros, losas, vigas, columnas).
>
> Esto puede indicar que el proyecto está bien coordinado en las capas detectadas, o que las capas estructurales necesitan revisión en la configuración de reglas.

---

> **Cómo usar este documento**
> Este reporte es tu bitácora de trabajo. El programa detectó posibles conflictos entre planos de **Arquitectura, Estructura, Eléctrico, Hidrosanitario y Mecánico**. Tu labor es abrir los DWGs, ir a cada coordenada indicada, mirar con tus propios ojos y decidir: ¿es un clash real o es ruido? Al final de cada sección hay una tabla de validación donde vas marcando.

---

## INSTRUCCIONES GENERALES

### Paso 1 — Abrir los dos archivos en AutoCAD

1. Abre AutoCAD.
2. Abre el **Plano A** (primera disciplina del par) desde `Archivo → Abrir`.
3. Abre el **Plano B** (segunda disciplina) en la misma sesión: `Archivo → Abrir` nuevamente.
4. Para ver ambos superpuestos: activa **"Ventanas en mosaico"** (`Ctrl + Alt + T`) o usa `Vista → Ventanas → Mosaico vertical`.
5. Alternativa: usa **DWG Compare** (`dwgcompare` en la línea de comandos) si tienes AutoCAD 2019+.

### Paso 2 — Usar el comando ZOOM para ir a las coordenadas

Cada clash tiene un comando AutoCAD listo. Cópialo y pégalo en la **Línea de Comandos**:
```
Z W X_MIN,Y_MIN X_MAX,Y_MAX
```
Ejemplo: `Z W 148000,-163000 158000,-154000`

> **Nota:** Todos los valores están en **milímetros**. Si tu DWG está en metros, divide entre 1,000.

### Paso 3 — Controlar las capas

1. Escribe `LA` para abrir el Administrador de Capas.
2. Apaga todas las capas (`Ctrl + A` → apaga ojo).
3. Prende solo las dos capas del clash que estás revisando.
4. Verifica si las geometrías se solapan.
5. Al terminar: `LA` → `Ctrl + A` → enciende todas.

### Paso 4 — Decisión final

| Decisión | Significado |
|---|---|
| ✅ **CLASH REAL** | Conflicto real de coordinación que hay que resolver. |
| ❌ **FALSO POSITIVO** | Ruido gráfico (marcos de hoja, cotas, anotaciones). |
| ⚠️ **PENDIENTE** | Necesitas más información antes de decidir. |

---

## Próximos pasos recomendados

1. Verificar que las capas ARQ y EST estén correctamente nombradas (ver `layer_role_coverage.csv` en la carpeta de salida).
2. Si el proyecto tiene capas no estándar, agregar reglas en `config/layer_rules/nasas_09.yaml`.
3. Revisar `pair_schedule_diagnostics.csv` para entender por qué cada par fue o no programado.



---

## PROYECTO — SERENA_18

_Fuente: `ARQUITECTURA/SERENA 18/SERENA 18/REVISION_CLASHES_ARQUITECTO_SERENA_18.md`_

# Guía de Revisión Manual de Clashes — SERENA 18
**Generado el:** 2026-05-23
**Preparado por:** Sistema de Coordinación Dupla
**Para:** Arquitecto revisor
**Modo:** Validación campo a campo en AutoCAD

## Estado — Sin incidencias primarias

> El análisis completó 510 pares programados y no encontró conflictos geométricos entre elementos estructurales primarios (muros, losas, vigas, columnas).
>
> Esto puede indicar que el proyecto está bien coordinado en las capas detectadas, o que las capas estructurales necesitan revisión en la configuración de reglas.

---

> **Cómo usar este documento**
> Este reporte es tu bitácora de trabajo. El programa detectó posibles conflictos entre planos de **Arquitectura, Estructura, Eléctrico, Hidrosanitario y Mecánico**. Tu labor es abrir los DWGs, ir a cada coordenada indicada, mirar con tus propios ojos y decidir: ¿es un clash real o es ruido? Al final de cada sección hay una tabla de validación donde vas marcando.

---

## INSTRUCCIONES GENERALES

### Paso 1 — Abrir los dos archivos en AutoCAD

1. Abre AutoCAD.
2. Abre el **Plano A** (primera disciplina del par) desde `Archivo → Abrir`.
3. Abre el **Plano B** (segunda disciplina) en la misma sesión: `Archivo → Abrir` nuevamente.
4. Para ver ambos superpuestos: activa **"Ventanas en mosaico"** (`Ctrl + Alt + T`) o usa `Vista → Ventanas → Mosaico vertical`.
5. Alternativa: usa **DWG Compare** (`dwgcompare` en la línea de comandos) si tienes AutoCAD 2019+.

### Paso 2 — Usar el comando ZOOM para ir a las coordenadas

Cada clash tiene un comando AutoCAD listo. Cópialo y pégalo en la **Línea de Comandos**:
```
Z W X_MIN,Y_MIN X_MAX,Y_MAX
```
Ejemplo: `Z W 148000,-163000 158000,-154000`

> **Nota:** Todos los valores están en **milímetros**. Si tu DWG está en metros, divide entre 1,000.

### Paso 3 — Controlar las capas

1. Escribe `LA` para abrir el Administrador de Capas.
2. Apaga todas las capas (`Ctrl + A` → apaga ojo).
3. Prende solo las dos capas del clash que estás revisando.
4. Verifica si las geometrías se solapan.
5. Al terminar: `LA` → `Ctrl + A` → enciende todas.

### Paso 4 — Decisión final

| Decisión | Significado |
|---|---|
| ✅ **CLASH REAL** | Conflicto real de coordinación que hay que resolver. |
| ❌ **FALSO POSITIVO** | Ruido gráfico (marcos de hoja, cotas, anotaciones). |
| ⚠️ **PENDIENTE** | Necesitas más información antes de decidir. |

---

## Próximos pasos recomendados

1. Verificar que las capas ARQ y EST estén correctamente nombradas (ver `layer_role_coverage.csv` en la carpeta de salida).
2. Si el proyecto tiene capas no estándar, agregar reglas en `config/layer_rules/serena_18.yaml`.
3. Revisar `pair_schedule_diagnostics.csv` para entender por qué cada par fue o no programado.



---

## PROYECTO — TORTUGA_C40

_Fuente: `ARQUITECTURA/TORTUGA C40/TORTUGA C40/REVISION_CLASHES_ARQUITECTO_TORTUGA_C40.md`_

# Guía de Revisión Manual de Clashes — TORTUGA C40
**Generado el:** 2026-05-23
**Preparado por:** Sistema de Coordinación Dupla
**Para:** Arquitecto revisor
**Modo:** Validación campo a campo en AutoCAD

## Estado — 16 incidencia(s) primaria(s) · 10 conflicto(s)

---

> **Cómo usar este documento**
> Este reporte es tu bitácora de trabajo. El programa detectó posibles conflictos entre planos de **Arquitectura, Estructura, Eléctrico, Hidrosanitario y Mecánico**. Tu labor es abrir los DWGs, ir a cada coordenada indicada, mirar con tus propios ojos y decidir: ¿es un clash real o es ruido? Al final de cada sección hay una tabla de validación donde vas marcando.

---

## INSTRUCCIONES GENERALES

### Paso 1 — Abrir los dos archivos en AutoCAD

1. Abre AutoCAD.
2. Abre el **Plano A** (primera disciplina del par) desde `Archivo → Abrir`.
3. Abre el **Plano B** (segunda disciplina) en la misma sesión: `Archivo → Abrir` nuevamente.
4. Para ver ambos superpuestos: activa **"Ventanas en mosaico"** (`Ctrl + Alt + T`) o usa `Vista → Ventanas → Mosaico vertical`.
5. Alternativa: usa **DWG Compare** (`dwgcompare` en la línea de comandos) si tienes AutoCAD 2019+.

### Paso 2 — Usar el comando ZOOM para ir a las coordenadas

Cada clash tiene un comando AutoCAD listo. Cópialo y pégalo en la **Línea de Comandos**:
```
Z W X_MIN,Y_MIN X_MAX,Y_MAX
```
Ejemplo: `Z W 148000,-163000 158000,-154000`

> **Nota:** Todos los valores están en **milímetros**. Si tu DWG está en metros, divide entre 1,000.

### Paso 3 — Controlar las capas

1. Escribe `LA` para abrir el Administrador de Capas.
2. Apaga todas las capas (`Ctrl + A` → apaga ojo).
3. Prende solo las dos capas del clash que estás revisando.
4. Verifica si las geometrías se solapan.
5. Al terminar: `LA` → `Ctrl + A` → enciende todas.

### Paso 4 — Decisión final

| Decisión | Significado |
|---|---|
| ✅ **CLASH REAL** | Conflicto real de coordinación que hay que resolver. |
| ❌ **FALSO POSITIVO** | Ruido gráfico (marcos de hoja, cotas, anotaciones). |
| ⚠️ **PENDIENTE** | Necesitas más información antes de decidir. |

---

## Orden de Revisión Recomendado

| # | Grupo | Capas | Incidentes | Área total (m²) | Prioridad |
|---|---|---|---|---|---|
| 1 | T-A | `SOLAR` / `SOLAR` | 10 | 18144.06 | **Empieza aquí** |
| 2 | T-B | `PLAFON` / `SOLAR` | 6 | 115.46 | Revisar |

---

## GRUPO T-A — `SOLAR` vs `SOLAR`

**10 incidente(s)** · Área total acumulada: **18144.06 m²**



### T-A1 — `incident_0000`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0000` |
| **Par** | `PLANOS ARQ TORTUGA C-40 NOV 2025.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `SOLAR` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 2304.12 m² |
| **Elementos involucrados** | 4 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 48,765 mm · Y: 35,327 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W -3441,9684 103882,64404
```

**Qué buscar:** Activa solo las capas `SOLAR` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-A2 — `incident_0008`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0008` |
| **Par** | `PLANOS ARQ TORTUGA C-40  20260129.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `SOLAR` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 2304.12 m² |
| **Elementos involucrados** | 4 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 48,765 mm · Y: 35,327 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W -3441,9684 103882,64404
```

**Qué buscar:** Activa solo las capas `SOLAR` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-A3 — `incident_0005`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0005` |
| **Par** | `PLANOS ARQ TORTUGA C-40 NOV 2025.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `SOLAR` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 1079.86 m² |
| **Elementos involucrados** | 3 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 158,521 mm · Y: 111,438 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 120062,95127 199406,130288
```

**Qué buscar:** Activa solo las capas `SOLAR` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-A4 — `incident_0013`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0013` |
| **Par** | `PLANOS ARQ TORTUGA C-40  20260129.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `SOLAR` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 1079.86 m² |
| **Elementos involucrados** | 3 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 158,521 mm · Y: 111,438 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 120062,95127 199406,130288
```

**Qué buscar:** Activa solo las capas `SOLAR` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-A5 — `incident_0004`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0004` |
| **Par** | `PLANOS ARQ TORTUGA C-40 NOV 2025.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `SOLAR` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 1079.83 m² |
| **Elementos involucrados** | 3 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 158,521 mm · Y: 42,053 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 120062,25742 199406,60903
```

**Qué buscar:** Activa solo las capas `SOLAR` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-A6 — `incident_0012`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0012` |
| **Par** | `PLANOS ARQ TORTUGA C-40  20260129.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `SOLAR` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 1079.83 m² |
| **Elementos involucrados** | 3 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 158,521 mm · Y: 42,053 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 120062,25742 199406,60903
```

**Qué buscar:** Activa solo las capas `SOLAR` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-A7 — `incident_0003`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0003` |
| **Par** | `PLANOS ARQ TORTUGA C-40 NOV 2025.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `SOLAR` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 2304.13 m² |
| **Elementos involucrados** | 1 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 157,396 mm · Y: 111,510 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 105191,85867 212514,140587
```

**Qué buscar:** Activa solo las capas `SOLAR` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-A8 — `incident_0011`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0011` |
| **Par** | `PLANOS ARQ TORTUGA C-40  20260129.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `SOLAR` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 2304.13 m² |
| **Elementos involucrados** | 1 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 157,396 mm · Y: 111,510 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 105191,85867 212514,140587
```

**Qué buscar:** Activa solo las capas `SOLAR` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-A9 — `incident_0002`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0002` |
| **Par** | `PLANOS ARQ TORTUGA C-40 NOV 2025.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `SOLAR` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 2304.09 m² |
| **Elementos involucrados** | 1 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 157,396 mm · Y: 42,125 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 105191,16482 212514,71202
```

**Qué buscar:** Activa solo las capas `SOLAR` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-A10 — `incident_0010`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0010` |
| **Par** | `PLANOS ARQ TORTUGA C-40  20260129.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `SOLAR` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 2304.09 m² |
| **Elementos involucrados** | 1 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 157,396 mm · Y: 42,125 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 105191,16482 212514,71202
```

**Qué buscar:** Activa solo las capas `SOLAR` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

## GRUPO T-B — `PLAFON` vs `SOLAR`

**6 incidente(s)** · Área total acumulada: **115.46 m²**



### T-B1 — `incident_0001`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0001` |
| **Par** | `PLANOS ARQ TORTUGA C-40 NOV 2025.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `PLAFON` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 24.63 m² |
| **Elementos involucrados** | 1 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 152,919 mm · Y: -158,375 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 145019,-165499 160819,-151252
```

**Qué buscar:** Activa solo las capas `PLAFON` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-B2 — `incident_0009`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0009` |
| **Par** | `PLANOS ARQ TORTUGA C-40  20260129.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `PLAFON` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 24.63 m² |
| **Elementos involucrados** | 1 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 152,919 mm · Y: -158,375 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 145019,-165499 160819,-151252
```

**Qué buscar:** Activa solo las capas `PLAFON` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-B3 — `incident_0006`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0006` |
| **Par** | `PLANOS ARQ TORTUGA C-40 NOV 2025.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `PLAFON` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 21.23 m² |
| **Elementos involucrados** | 1 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 163,319 mm · Y: -158,375 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 155819,-165499 170819,-151252
```

**Qué buscar:** Activa solo las capas `PLAFON` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-B4 — `incident_0014`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0014` |
| **Par** | `PLANOS ARQ TORTUGA C-40  20260129.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `PLAFON` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 21.23 m² |
| **Elementos involucrados** | 1 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 163,319 mm · Y: -158,375 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 155819,-165499 170819,-151252
```

**Qué buscar:** Activa solo las capas `PLAFON` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-B5 — `incident_0007`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0007` |
| **Par** | `PLANOS ARQ TORTUGA C-40 NOV 2025.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `PLAFON` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 11.87 m² |
| **Elementos involucrados** | 1 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 183,119 mm · Y: -159,475 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 175219,-165499 191019,-153452
```

**Qué buscar:** Activa solo las capas `PLAFON` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

### T-B6 — `incident_0015`

| Campo | Valor |
|---|---|
| **ID Programa** | `incident_0015` |
| **Par** | `PLANOS ARQ TORTUGA C-40  20260129.dwg` vs `PLANOS ESTRUCTURALES-TORTUGA C-40 2025-11-12.dwg` |
| **Capas** | `PLAFON` (ARQ) vs `SOLAR` (EST) |
| **Área de solapamiento** | 11.87 m² |
| **Elementos involucrados** | 1 |
| **Severidad** | Alta |
| **Confianza del programa** | Media |
| **Nivel** | NPT_P1 |
| **Centro del clash** | X: 183,119 mm · Y: -159,475 mm |

**Cómo llegar — Comando AutoCAD:**
```
Z W 175219,-165499 191019,-153452
```

**Qué buscar:** Activa solo las capas `PLAFON` y `SOLAR`. ¿Se solapan los elementos de ambos planos en ese punto? Verifica si la geometría es constructiva (muros, losas, vigas) o anotación (marcos, títulos, símbolos).

---

---

## Bitácora de Validación — TORTUGA C40

*Completa esta tabla a medida que revisas cada punto.*

| Código | Capas | Área (m²) | Decisión | Notas del revisor | Fecha |
|---|---|---|---|---|---|
| T-A1 (`incident_0000`) | `SOLAR` / `SOLAR` | 2304.12 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-A2 (`incident_0008`) | `SOLAR` / `SOLAR` | 2304.12 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-A3 (`incident_0005`) | `SOLAR` / `SOLAR` | 1079.86 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-A4 (`incident_0013`) | `SOLAR` / `SOLAR` | 1079.86 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-A5 (`incident_0004`) | `SOLAR` / `SOLAR` | 1079.83 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-A6 (`incident_0012`) | `SOLAR` / `SOLAR` | 1079.83 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-A7 (`incident_0003`) | `SOLAR` / `SOLAR` | 2304.13 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-A8 (`incident_0011`) | `SOLAR` / `SOLAR` | 2304.13 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-A9 (`incident_0002`) | `SOLAR` / `SOLAR` | 2304.09 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-A10 (`incident_0010`) | `SOLAR` / `SOLAR` | 2304.09 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-B1 (`incident_0001`) | `PLAFON` / `SOLAR` | 24.63 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-B2 (`incident_0009`) | `PLAFON` / `SOLAR` | 24.63 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-B3 (`incident_0006`) | `PLAFON` / `SOLAR` | 21.23 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-B4 (`incident_0014`) | `PLAFON` / `SOLAR` | 21.23 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-B5 (`incident_0007`) | `PLAFON` / `SOLAR` | 11.87 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |
| T-B6 (`incident_0015`) | `PLAFON` / `SOLAR` | 11.87 | ☐ ✅ REAL · ☐ ❌ FALSO · ☐ ⚠️ PENDIENTE | | |

---

*Reporte generado por Dupla — pipeline 2.5D con roles canónicos y tolerancias explícitas.*
