# SERENA 18 - Meeting Pack de Resultados

- Fecha: `2026-04-25`
- Proyecto: `SERENA 18`
- Estado del pipeline: `screening 2.5D usable por nivel, no cierre BIM total`

## Que si mostrar en la reunion

### Resultado defendible actual

Hoy el resultado defendible no es `analysis_02`.
Lo correcto es mostrar `analysis_05`, porque ahi ya se hizo:

- separacion por nivel
- alineacion manual ARQ/EST
- programacion de pares comparables
- reporte de incidencias primarias en vez de ruido masivo

### Corridas que si valen la pena mostrar

- `analysis_05_NPT_P1`
  - [resultado](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P1/2026-04-25_analysis_05_NPT_P1_resultado.md:1)
  - `53` incidencias primarias
  - `179` debug
  - pares principales:
    - `ARQ P1` vs `E03`
    - `ARQ P1` vs `E09`

- `analysis_05_NPT_P2`
  - [resultado](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P2/2026-04-25_analysis_05_NPT_P2_resultado.md:1)
  - `66` incidencias primarias
  - `769` debug
  - pares principales:
    - `UpperFloor` vs `E12`
    - `UpperFloor` vs `E11`
    - `UpperFloor` vs `E10`

- `analysis_05_TECHO`
  - [resultado](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_TECHO/2026-04-25_analysis_05_TECHO_resultado.md:1)
  - `108` incidencias primarias
  - `842` debug
  - pares principales:
    - `UpperFloor` vs `E14`
    - `UpperFloor` vs `E19`
    - `UpperFloor` vs `E16`
    - `UpperFloor` vs `E15`

### Corridas complementarias ya ejecutadas

- `analysis_05_CIMENTACION`
  - [resultado](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_CIMENTACION/2026-04-25_analysis_05_CIMENTACION_resultado.md:1)
  - `1` incidencia primaria
  - `706` debug
  - lectura:
    - comparable, pero todavia debil

- `analysis_05_SOTANO`
  - [resultado](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_SOTANO/2026-04-25_analysis_05_SOTANO_resultado.md:1)
  - `0` incidencias primarias
  - `429` debug
  - lectura:
    - comparable, pero aun no presentable como clash final

### Mensaje recomendado

"Pasamos de un radar ruidoso a incidencias comparables por nivel.
Hoy tenemos tres corridas presentables: `NPT_P1`, `NPT_P2` y `TECHO`.
`CIMENTACION` y `SOTANO` ya se corrieron tambien, pero siguen siendo corridas de ajuste, no cierre final."

## Cobertura actual real

### Ya comparado

#### Arquitectura vs Estructura

- `NPT_P1`
  - `Serena 18 -PLANTA PISOS 10-10-2022.dwg`
  - contra:
    - `E03 - PLANO DE ENCOFRADO`
    - `E09 - LOSAS DE PISO SOBRE TERRENO`

- `NPT_P2`
  - `2208-Serena18-ID-Base-UpperFloor.dwg`
  - contra:
    - `E10 - ENTREPISO CASA`
    - `E11 - ENTREPISO CASA (MOD.I)`
    - `E12 - ENTREPISO CASA (MOD. II)`

- `CIMENTACION`
  - `2208-Serena18-ID-Base.dwg`
  - contra:
    - `E04 - PLANTA GENERAL DE CIMIENTOS`
    - `E06 - PLANTA EST. CIMIENTOS Y DETALLES CASA`

- `SOTANO`
  - `2208-Serena18-ID-Base.dwg`
  - contra:
    - `E05 - PLANTA EST. CIMIENTOS Y DETALLES SOTANO`
    - `E08 - LOSAS DE TECHO SOTANO`

- `TECHO`
  - `2208-Serena18-ID-Base-UpperFloor.dwg`
  - contra:
    - `E14`
    - `E15`
    - `E16`
    - `E19`

## Si, faltan temas por resolver

La respuesta corta es: **si**, pero ya no faltan corridas base de estructura. Lo que falta ahora es mejorar calidad donde la senal sigue debil.

## Faltantes que si importan para coordinacion

### Estructura ya corrida, pero pendiente de cerrar bien

#### Cimentacion

- `E04 - PLANTA GENERAL DE CIMIENTOS`
- `E06 - PLANTA EST. CIMIENTOS Y DETALLES CASA`
  - estado actual:
    - corrida hecha
    - solo `1` incidencia primaria
    - requiere refinar alineacion o seleccion geometrica

#### Sotano

- `E05 - PLANTA EST. CIMIENTOS Y DETALLES SOTANO`
- `E08 - LOSAS DE TECHO SOTANO`
  - estado actual:
    - corrida hecha
    - `0` incidencias primarias
    - requiere revisar alineacion o cluster dominante

#### Techo

- `E14`
- `E15`
- `E16`
- `E17`
- `E18`
- `E19`
  - estado actual:
    - corrida hecha con buena senal sobre `E14/E15/E16/E19`
    - `E17` y `E18` quedaron fuera por `extract_failed`

### Arquitectura pendiente de resolver

- `2208-Serena18-ID-Base.dwg`
  - ya tiene alineaciones manuales puntuales para `CIMENTACION` y `SOTANO`
  - pero esa alineacion todavia no produce una base tan limpia como `NPT_P1`

## Faltantes que existen, pero no son prioridad para el screening base

### Estructurales de detalle

No son la siguiente prioridad para clash por planta:

- `E00`, `E01`, `E02`
- `E07`, `E07A`, `E07B`
- `E13`
- `E20` a `E25`

Estos son mas de detalle o refuerzo. Pueden entrar despues, pero no son el siguiente paso para una coordinacion rapida y creible por planta.

### Arquitectonicos de interiores y detalle

Hay muchos DWG arquitectonicos adicionales en `11. NOVIEMBRE 2023`:

- schedules
- millwork
- vanities
- media panels
- shutters
- laundry / kitchen details
- reference detail plans

No conviene meterlos ahora al clash base, porque inflarian ruido y no mejoran el baseline `ARQ/EST` principal.

## MEP pendiente

Todavia no esta corrido de forma defendible:

- `ELECTRICOS`
- `HIDROSANITARIOS`
- `MECANICOS`

### Por que no

- varias entregas son de fechas distintas
- varias fuentes caen en bandas de coordenadas diferentes
- primero hay que cerrar baseline `ARQ + ESTRUCTURA`

## Que decir si preguntan "que falta"

Puedes decir esto:

"Si, faltan temas, pero ya no faltan corridas base de estructura.
Lo que falta de verdad es:

1. mejorar `CIMENTACION`
2. mejorar `SOTANO`
3. resolver `E17/E18` en `TECHO`
4. luego `MEP`, una disciplina por vez

No estamos metiendo todos los DWG restantes porque muchos son detalles o entregas no comparables y solo meterian ruido."

## Siguiente secuencia recomendada

1. refinar alineacion o seleccion ARQ de `CIMENTACION`
2. relanzar `E04/E06`
3. refinar alineacion o seleccion ARQ de `SOTANO`
4. relanzar `E05/E08`
5. resolver `extract_failed` de `E17/E18`
6. relanzar `TECHO` completo
7. despues entrar a `HIDROSANITARIO`
8. luego `MECANICO`
9. luego `ELECTRICO`

## Archivos de apoyo para la reunion

- indice general: [2026-04-25_analysis_05_SERENA_18_runs_index.md](C:/Users/Enrique Casanova/Dupla/analysis_output/2026-04-25_analysis_05_SERENA_18_runs_index.md:1)
- carpeta consolidada: [serena18_analysis_05_runs](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs:1)
- tiempos: [2026-04-25_comparacion_tiempos_todos_los_analysis.md](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/2026-04-25_comparacion_tiempos_todos_los_analysis.md:1)
