# Guía de Revisión Manual de Clashes — NASAS 09
**Generado el:** 2026-05-28
**Preparado por:** Sistema de Coordinación Dupla
**Para:** Arquitecto revisor
**Modo:** Validación campo a campo en AutoCAD

## Estado — Sin incidencias primarias

> El análisis completó 0 pares programados y no encontró conflictos geométricos entre elementos estructurales primarios (muros, losas, vigas, columnas).
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
