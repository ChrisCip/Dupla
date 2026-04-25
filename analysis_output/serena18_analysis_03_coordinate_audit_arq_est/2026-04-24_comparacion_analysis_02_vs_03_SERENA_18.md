# Comparacion `analysis_02` vs `analysis_03` - SERENA 18

- Fecha: 2026-04-24
- Proyecto: `SERENA 18`
- `analysis_02`: `analysis_output/serena18_analysis_02_core_mixed_native`
- `analysis_03`: `analysis_output/serena18_analysis_03_coordinate_audit_arq_est`

## Resumen corto

`analysis_02` fue una corrida de **deteccion masiva**. Sirvio para encontrar zonas y pares sospechosos, pero mezclo entregas, disciplinas y sistemas de coordenadas, por eso produjo `4,760` clashes con bastante ruido.

`analysis_03` fue una corrida de **control de calidad previo al clash**. Ya no intento forzar un conteo; primero audito coordenadas y elegibilidad. El resultado fue `0` incidencias primarias porque detecto que la arquitectura seleccionada no esta alineada con la estructura y bloqueo todos los pares `ARQ/EST`.

## Diferencias principales

| Tema | `analysis_02` | `analysis_03` |
| --- | --- | --- |
| Objetivo | Encontrar muchas zonas conflictivas rapidamente | Validar si la comparacion `ARQ/EST` es tecnicamente confiable |
| Alcance | `core_mixed` multi-entrega | Cohorte manual `ARQ/EST` |
| Fuentes | `31` fuentes (`21 DWG`, `10 PDF`) | `18 DWG` |
| Elementos 2.5D | `2,806` | `3,240` |
| Resultado principal | `4,760` conflictos HARD | `0` incidencias primarias |
| Filosofia | Screening amplio, con ruido | Gating duro antes del clash |
| PDFs | Si | No |
| MEP | Si, mezclado | No |
| Cohortes | Mezcladas | Cohorte manual unica |
| Scheduler previo | No | Si |
| Audit de coordenadas | No | Si |
| Salida de pares bloqueados | No | Si (`pair_schedule.json`) |

## Que encontro cada uno

### `analysis_02`

- Detecto una señal fuerte en `ARQUITECTURA vs ESTRUCTURA`, sobre todo contra:
  - `E04`
  - `E05`
  - `E06`
  - `E10`
  - `E11`
  - `E12`
  - `E14-E19`
- Produjo `4,760` clashes, pero gran parte vino de:
  - `bbox/bbox`
  - `bbox/polyline`
  - mezcla de sistemas de coordenadas
  - mezcla de entregas distintas
  - saturacion a `150` por par
- En la practica fue un **radar preliminar**, no un conteo final confiable.

### `analysis_03`

- Audito `18` DWG de una cohorte manual `ARQ/EST`.
- Marco `15` archivos como `eligible`.
- Marco `3` archivos como `needs_alignment`.
- Programo `45` pares potenciales.
- Bloqueo `45/45` pares.
- No genero incidencias primarias ni debug porque **no habia una base arquitectonica elegible para comparar con la estructura**.

## Mejores tecnicas de `analysis_03`

Si hubo mejoras claras:

1. `coordinate_audit`
- Ahora cada archivo queda perfilado con:
  - banda de coordenadas
  - nivel inferido
  - conteo de entidades
  - conteo de geometria primaria
  - estado de elegibilidad

2. `pair_schedule`
- Ya no se corre `todo contra todo`.
- El sistema decide antes si un par debe entrar o no entrar al clash.

3. Gating por coordenadas
- Si un archivo cae fuera de la banda dominante, queda como `needs_alignment`.
- Eso evita falsos positivos enormes.

4. Gating por geometria
- `bbox` y contenedores ya no dominan el reporte primario como antes.

5. Salidas mas auditables
- `analysis_03` deja:
  - `coordinate_audit.json/md`
  - `pair_schedule.json`
  - `primary_incidents.json/md`
  - `debug_candidates.json`

## Por que `analysis_03` dio cero

No dio cero porque “no haya problemas”.

Dio cero porque encontro que los DWG arquitectonicos base seleccionados no comparten la misma banda de coordenadas que la estructura:

- `2208-Serena18-ID-Base-UpperFloor.dwg` -> `X~-135.25M, Y~-1102.42M`
- `2208-Serena18-ID-Base.dwg` -> `X~-141.69M, Y~-1131.41M`
- Estructura `E03-E19` -> alrededor de `X~168.8M, Y~624.6M`

Eso significa que `analysis_03` no fracaso: **detecto una condicion invalida de entrada y paro antes de inventar clashes**.

## Interpretacion correcta

- `analysis_02` dice: “hay zonas sospechosas y pares que vale la pena revisar”.
- `analysis_03` dice: “todavia no puedes hacer una comparacion formal `ARQ/EST` con esta base arquitectonica porque esta desalineada”.

Los dos analisis no se contradicen. Se complementan:

- `analysis_02` da señal
- `analysis_03` da control

## Veredicto

`analysis_03` es **mejor metodologicamente** que `analysis_02`, aunque haya devuelto `0`.

La mejora principal no fue “detectar mas clashes”, sino **evitar clashes falsos**.

Hoy la conclusion mas honesta es esta:

- `analysis_02` sirve para priorizar revision manual.
- `analysis_03` sirve para demostrar que la comparacion `ARQ/EST` aun necesita alineacion geometrica antes de producir un reporte defendible.

## Siguiente paso recomendado

Antes de `analysis_04`, hay que hacer una de estas dos:

1. Alinear la arquitectura base al sistema de coordenadas estructural.
2. Encontrar otra base arquitectonica de `SERENA 18` que ya este en la misma banda que `E03-E19`.

Solo despues de eso tiene sentido correr un `analysis_04` fino `ARQ/EST`.
