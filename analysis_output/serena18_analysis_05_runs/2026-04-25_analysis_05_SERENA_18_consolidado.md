# SERENA 18 - Analysis 05 Consolidado

- Fecha: `2026-04-25`
- Proyecto: `SERENA 18`
- Familia de corridas: `analysis_05_*`
- Fuente principal: `DWG vs DWG`
- Perfil: `fast_compare`
- Nota clave: este consolidado resume los cinco runs por nivel. Los conteos aqui no deben leerse como un total unico del proyecto sin deduplicacion adicional entre niveles.

## Parte Resumida Para Arquitectos

### Que ya se logro

El proyecto ya no esta en la etapa de "radar bruto" de `analysis_02`.
En `analysis_05` ya se hicieron corridas por nivel con alineacion manual `ARQ/EST`, comparando solo pares `DWG vs DWG` que el scheduler considero tecnicamente comparables.

Hoy hay tres resultados que si se pueden mostrar como base de coordinacion:

- `NPT_P1`
  - `53` incidencias primarias
  - pares principales:
    - `ARQ P1` vs `E03`
    - `ARQ P1` vs `E09`

- `NPT_P2`
  - `66` incidencias primarias
  - pares principales:
    - `UpperFloor` vs `E12`
    - `UpperFloor` vs `E11`
    - `UpperFloor` vs `E10`

- `TECHO`
  - `108` incidencias primarias
  - pares principales:
    - `UpperFloor` vs `E14`
    - `UpperFloor` vs `E19`
    - `UpperFloor` vs `E16`
    - `UpperFloor` vs `E15`

### Que ya se corrio pero todavia no sirve como resultado final

- `CIMENTACION`
  - si fue comparable
  - pero solo dio `1` incidencia primaria
  - sigue siendo una corrida de ajuste, no un cierre confiable

- `SOTANO`
  - si fue comparable
  - pero dio `0` incidencias primarias y `429` debug
  - hoy no debe presentarse como clash final

### Que decir en una reunion

Puedes decir esto:

"Ya tenemos coordinacion comparable por nivel en `P1`, `P2` y `TECHO`.
`CIMENTACION` y `SOTANO` ya se probaron tambien, pero todavia necesitan refinamiento antes de presentarse como resultado final.
La base estructural ya esta corrida. Lo que sigue es limpiar semantica de capas y cerrar los casos pendientes."

### Lo que todavia falta

- refinar `CIMENTACION`
- refinar `SOTANO`
- resolver `E17` y `E18` en `TECHO`, que quedaron fuera por `extract_failed`
- despues entrar a `HIDROSANITARIO`, `MECANICO` y `ELECTRICO`

## Parte Tecnica Larga

### 1. Alcance real de `analysis_05`

Runs incluidos:

- [analysis_05_NPT_P1](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P1:1)
- [analysis_05_NPT_P2](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P2:1)
- [analysis_05_CIMENTACION](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_CIMENTACION:1)
- [analysis_05_SOTANO](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_SOTANO:1)
- [analysis_05_TECHO](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_TECHO:1)

Resultado agregado de la familia `analysis_05`:

- `228` incidencias primarias agrupadas
- `1314` conflictos miembros dentro de esas incidencias
- `2925` debug conflicts
- `3732` elementos suprimidos por baja fidelidad o `bbox`

Importante:

- estos numeros no son un conteo unico y deduplicado del proyecto
- son la suma de cinco corridas por nivel
- un mismo archivo ARQ participa en varios runs con alineaciones distintas

### 2. Metodologia aplicada

En `analysis_05` ya no se hizo mezcla global.
Cada run tuvo:

- `cohort_manifest.json`
- `alignment_manifest.json`
- `fast_compare`
- gating por disciplina, nivel y comparabilidad
- conflicto primario separado de `debug`

Todas las comparaciones de esta familia fueron `DWG vs DWG`.
No se usaron PDFs como fuente primaria aqui.

### 3. Alineaciones manuales aplicadas

Las transformaciones manuales usadas por run fueron estas:

| Run | Archivo ARQ | Traslacion mm |
| --- | --- | --- |
| `NPT_P1` | `Serena 18 -PLANTA PISOS 10-10-2022.dwg` | `dx = -4,871,358.9623`, `dy = +500,416.0999` |
| `NPT_P2` | `2208-Serena18-ID-Base-UpperFloor.dwg` | `dx = +168,737,102.0343`, `dy = +624,500,058.7463` |
| `CIMENTACION` | `2208-Serena18-ID-Base.dwg` | `dx = +168,772,836.1209`, `dy = +624,585,112.5822` |
| `SOTANO` | `2208-Serena18-ID-Base.dwg` | `dx = +168,782,587.1251`, `dy = +624,594,592.8669` |
| `TECHO` | `2208-Serena18-ID-Base-UpperFloor.dwg` | `dx = +168,745,822.0042`, `dy = +624,607,707.0682` |

Ademas:

- `CIMENTACION` uso override manual `level_id = CIMENTACION`
- `SOTANO` uso override manual `level_id = SOTANO`
- `TECHO` uso override manual `level_id = TECHO`

### 4. Unidades y normalizacion

Los `coordinate_audit.json` muestran mezcla de unidades entre archivos:

- algunos ARQ quedaron con `units_to_mm_factor = 1.0`
- varios estructurales quedaron con `units_to_mm_factor = 304.8`
- `NPT_P1` incluso corre con ARQ y EST ambos en `304.8`

La buena noticia es que el pipeline si logro normalizar esos sistemas a `mm` antes del clash.

### 5. Bandas de coordenadas utiles por nivel

Despues de la alineacion manual, las bandas comparables quedaron asi:

| Run | Banda util dominante |
| --- | --- |
| `NPT_P1` | `X~168.81M a 168.82M`, `Y~624.64M a 624.65M` |
| `NPT_P2` | `X~168.82M`, `Y~624.56M` |
| `CIMENTACION` | `X~168.80M a 168.81M`, `Y~624.62M a 624.64M` |
| `SOTANO` | `X~168.81M a 168.82M`, `Y~624.63M a 624.65M` |
| `TECHO` | `X~168.83M`, `Y~624.67M` |

Esto significa que `analysis_05` si resolvio el problema grueso de comparabilidad espacial que antes habia bloqueado `analysis_03` y `analysis_04`.

### 6. Donde estan las inconsistencias `DWG vs DWG` por coordenadas

#### `NPT_P1`

Pares programados:

- `Serena 18 -PLANTA PISOS 10-10-2022.dwg` vs `E03`
- `Serena 18 -PLANTA PISOS 10-10-2022.dwg` vs `E09`

Resumen por par:

| Par | Incidencias | Miembros agrupados | Rango X mm | Rango Y mm | Confianza dominante |
| --- | ---: | ---: | --- | --- | --- |
| `ARQ P1 vs E03` | `36` | `253` | `168,795,586 - 168,833,404` | `624,644,422 - 624,652,502` | `medium` |
| `ARQ P1 vs E09` | `17` | `70` | `168,801,703 - 168,828,518` | `624,644,583 - 624,647,196` | `medium` |

Hotspots representativos:

- `ARQ P1 vs E03`
  - centro principal: `(168,817,815, 624,648,464) mm`
  - bounds: `[168,816,581, 624,646,757, 168,819,049, 624,650,171]`
  - capas/entidades: `MARCO|Polyline` vs `EST_PROYECCION|Polyline`
  - area representativa: `8,428,160.81 mm2`

- `ARQ P1 vs E09`
  - hotspot alto: `(168,828,518, 624,644,613) mm`
  - bounds: `[168,828,493, 624,644,315, 168,828,543, 624,644,911]`
  - capas/entidades: mezcla `Polyline / Line`

Lectura tecnica:

- el nivel si esta alineado
- pero las incidencias primarias siguen muy cargadas por `MARCO` del ARQ
- eso sugiere que parte de la senal todavia es perimetral o de contorno, no puramente constructiva

#### `NPT_P2`

Pares programados:

- `UpperFloor vs E10`
- `UpperFloor vs E11`
- `UpperFloor vs E12`

Resumen por par:

| Par | Incidencias | Miembros agrupados | Rango X mm | Rango Y mm | Confianza dominante |
| --- | ---: | ---: | --- | --- | --- |
| `UpperFloor vs E12` | `31` | `115` | `168,824,639 - 168,845,428` | `624,549,776 - 624,569,513` | `high` |
| `UpperFloor vs E11` | `27` | `102` | `168,824,639 - 168,845,428` | `624,549,776 - 624,569,513` | `high` |
| `UpperFloor vs E10` | `8` | `23` | `168,816,979 - 168,845,201` | `624,549,143 - 624,569,189` | `high` |

Hotspots representativos:

- `UpperFloor vs E11`
  - `(168,835,479, 624,569,513) mm`
  - capas/entidades: `I-WALL|Polyline` vs `Solares|Polyline`
  - area representativa: `1,574,999.82 mm2`

- `UpperFloor vs E11`
  - `(168,827,059, 624,562,963) mm`
  - capas/entidades: `I-FURN|Polyline` vs `Solares|Polyline`
  - area representativa: `1,183,110.06 mm2`

- `UpperFloor vs E12`
  - `(168,824,639, 624,568,338) mm`
  - capas/entidades: `I-EQUIPMENT|Polyline` vs `Solares|Polyline`
  - area representativa: `439,200.00 mm2`

Lectura tecnica:

- geometria primaria mucho mejor que en `NPT_P1`
- confianza `high` en las `66` incidencias
- pero semanticamente sigue habiendo ruido porque las capas ARQ dominantes son `I-FURN`, `I-WALL`, `I-EQUIPMENT` y del lado estructural aparecen `Solares`, `PARCELS`, `TITULOS`

#### `CIMENTACION`

Pares programados:

- `Base vs E04`
- `Base vs E06`

Resultado:

- `1` sola incidencia primaria
- `706` debug

Ubicacion de la unica incidencia primaria:

- `Base vs E06`
- centro: `(168,816,577, 624,649,583) mm`
- bounds: `[168,816,359, 624,649,096, 168,816,873, 624,650,070]`
- geometria: `dwg_accore_polyline / dwg_accore_circle`
- confianza: `high`
- capas/entidades: `I-FURN|Polyline` vs `Planos|Circle`

Lectura tecnica:

- el scheduler ya deja correr `CIMENTACION`
- pero la senal util todavia es muy pobre
- la unica incidencia primaria viene de `I-FURN` contra `Circle` en `Planos`, lo cual no es una base robusta para cerrar este nivel

#### `SOTANO`

Pares programados:

- `Base vs E05`
- `Base vs E08`

Resultado:

- `0` incidencias primarias
- `429` debug

Lectura tecnica:

- `SOTANO` ya es comparable espacialmente
- pero no produjo ninguna incidencia primaria defendible
- hoy es una corrida valida como prueba de comparabilidad, no como reporte final

#### `TECHO`

Pares programados:

- `UpperFloor vs E14`
- `UpperFloor vs E15`
- `UpperFloor vs E16`
- `UpperFloor vs E19`

Pares no programados:

- `UpperFloor vs E17`
  - `extract_failed`
- `UpperFloor vs E18`
  - `extract_failed`

Resumen por par:

| Par | Incidencias | Miembros agrupados | Rango X mm | Rango Y mm | Confianza dominante |
| --- | ---: | ---: | --- | --- | --- |
| `UpperFloor vs E15` | `29` | `208` | `168,812,070 - 168,853,574` | `624,655,994 - 624,676,169` | `high` |
| `UpperFloor vs E16` | `28` | `196` | `168,812,070 - 168,853,574` | `624,655,994 - 624,675,787` | `high` |
| `UpperFloor vs E14` | `29` | `190` | `168,812,070 - 168,853,574` | `624,655,994 - 624,676,171` | `high` |
| `UpperFloor vs E19` | `22` | `156` | `168,835,779 - 168,853,574` | `624,663,429 - 624,676,249` | `high` |

Hotspots representativos:

- `UpperFloor vs E14`
  - centro: `(168,841,863, 624,668,410) mm`
  - bounds: `[168,841,838, 624,667,083, 168,841,888, 624,669,736]`
  - capas/entidades: `I-FURN|Polyline` vs `EST_PROEECCION|Line`

- `UpperFloor vs E19`
  - centro: `(168,841,839, 624,668,487) mm`
  - bounds: `[168,841,814, 624,667,237, 168,841,864, 624,669,736]`
  - capas/entidades: `I-FURN|Polyline` vs `EST_PROEECCION|Line`

- `UpperFloor vs E16`
  - centro: `(168,841,135, 624,666,914) mm`
  - bounds: `[168,838,599, 624,663,536, 168,844,837, 624,669,736]`
  - capas/entidades: `I-FURN|Polyline` vs `PARCELS|Polyline`

- `UpperFloor vs E15`
  - centro: `(168,841,940, 624,668,408) mm`
  - bounds: `[168,841,915, 624,667,079, 168,841,965, 624,669,736]`
  - capas/entidades: `I-FURN|Polyline` vs `EST_PROEECCION|Line`

Lectura tecnica:

- `TECHO` es el run nuevo con mejor senal util despues de `P1` y `P2`
- la confianza es `high` en las `108` incidencias
- pero semanticamente todavia domina `I-FURN` del lado ARQ y `Solares`, `PARCELS`, `EST_PROEECCION` del lado estructural
- o sea: la alineacion ya funciona, pero el filtro de capas aun necesita endurecerse

### 7. Inconsistencias residuales por coordenadas

Hay un patron muy claro de ruido residual en `debug`:

- cluster repetido cerca de `X ~ 172,788,421 mm`, `Y ~ 624,240,745 mm`
- aparece sobre todo en `NPT_P2`, `CIMENTACION` y `TECHO`
- viene con areas gigantes del orden de `649,031,598.72 mm2`
- la geometria es casi siempre `dwg_accore_bbox / dwg_accore_bbox`

Interpretacion:

- eso no parece una interferencia fisica puntual
- parece un outlier de `bbox` global, contenedor o referencia no constructiva
- por eso esos casos quedaron en `debug` y no en el reporte primario

En `SOTANO`, el ruido se concentra mas cerca de la banda correcta:

- ejemplo: `(168,837,047, 624,634,869) mm`
- pero sigue viniendo como `bbox / bbox`
- por eso el nivel no genero incidencias primarias

### 8. Calidad geometrica y ruido remanente

Distribucion de confianza en incidencias primarias:

| Run | `high` | `medium` |
| --- | ---: | ---: |
| `NPT_P1` | `0` | `53` |
| `NPT_P2` | `66` | `0` |
| `CIMENTACION` | `1` | `0` |
| `SOTANO` | `0` | `0` |
| `TECHO` | `108` | `0` |

Distribucion de geometria primaria:

| Run | Geometria dominante |
| --- | --- |
| `NPT_P1` | `polyline / line` |
| `NPT_P2` | `polyline / polyline` |
| `CIMENTACION` | `polyline / circle` |
| `SOTANO` | sin primarios |
| `TECHO` | `polyline / polyline` y `polyline / line` |

Elementos suprimidos por baja fidelidad:

| Run | Suprimidos | `bounds_fallback` | `container_bbox` |
| --- | ---: | ---: | ---: |
| `NPT_P1` | `596` | `430` | `166` |
| `NPT_P2` | `823` | `713` | `110` |
| `CIMENTACION` | `635` | `467` | `168` |
| `SOTANO` | `748` | `577` | `171` |
| `TECHO` | `930` | `831` | `99` |

Lectura tecnica:

- el pipeline ya separa bien `primario` y `debug`
- pero la base de entrada sigue teniendo muchos `bbox`
- el siguiente salto de calidad no depende de mas scheduler
- depende de filtrar mejor capas/entidades no constructivas

### 9. Hallazgo tecnico importante al revisar los `source_refs`

Aunque la alineacion espacial ya funciona, varias incidencias primarias siguen apoyandose en capas semanticamente dudosas.

Capas ARQ mas frecuentes en las incidencias primarias:

- `NPT_P1`: `MARCO`
- `NPT_P2`: `I-FURN`, `I-WALL`, `I-EQUIPMENT`, `I-MILLWORK`
- `CIMENTACION`: `I-FURN`
- `TECHO`: `I-FURN`, `I-FLOR-FIN`, `I-WALL`

Capas EST mas frecuentes en las incidencias primarias:

- `NPT_P1`: `EST_PROYECCION`, `EST - EJE DE VIGA`, `piso`
- `NPT_P2`: `Solares`, `PARCELS`, `TITULOS`
- `CIMENTACION`: `Planos`
- `TECHO`: `Solares`, `PARCELS`, `MURO`, `EST_PROEECCION`

Esto implica:

- geometria `high` no equivale automaticamente a semantica correcta
- varios choques todavia parecen perimetros, mobiliario, capas de apoyo o referencias de dibujo
- el filtro por tipo geometrico ya mejoro mucho el pipeline
- el filtro por capa/semantic role sigue siendo la mejora mas rentable

### 10. Conclusiones tecnicas

Conclusiones firmes:

- `analysis_05` resolvio la comparabilidad espacial por nivel
- `P1`, `P2` y `TECHO` ya tienen senal util para revision manual
- `CIMENTACION` y `SOTANO` ya dejaron de fallar por scheduler, pero aun no estan cerrados
- `TECHO` es el nivel nuevo mas fuerte, aunque todavia con ruido semantico

Conclusiones de cautela:

- no conviene presentar `228` como "cantidad final del proyecto"
- no conviene interpretar cada incidencia primaria como clash constructivo definitivo
- el principal problema remanente ya no es coordenada sino semantica de capas

### 11. Recomendacion inmediata

Antes de entrar a MEP:

- endurecer filtro de capas ARQ:
  - `I-FURN`
  - `I-FURN-RUGS`
  - `I-EQUIPMENT`
  - `MARCO`

- endurecer filtro de capas EST:
  - `Solares`
  - `PARCELS`
  - `TITULOS`
  - `EST_PROYECCION`
  - `Planos`

- resolver `extract_failed` de `E17` y `E18`
- relanzar `TECHO`
- luego refinar `CIMENTACION`
- luego refinar `SOTANO`

Despues de eso, si, ya tiene sentido abrir `HIDROSANITARIO`, `MECANICO` y `ELECTRICO` una disciplina por vez.

## Referencias

### Indices y resumenes

- [README.md del grupo](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/README.md:1)
- [Index general](C:/Users/Enrique Casanova/Dupla/analysis_output/2026-04-25_analysis_05_SERENA_18_runs_index.md:1)
- [Meeting pack](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/2026-04-25_meeting_pack_SERENA_18.md:1)

### JSONs auditados por run

- `NPT_P1`
  - [summary.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P1/summary.json:1)
  - [coordinate_audit.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P1/coordinate_audit.json:1)
  - [pair_schedule.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P1/pair_schedule.json:1)
  - [primary_incidents.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P1/primary_incidents.json:1)
  - [debug_candidates.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P1/debug_candidates.json:1)

- `NPT_P2`
  - [summary.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P2/summary.json:1)
  - [coordinate_audit.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P2/coordinate_audit.json:1)
  - [pair_schedule.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P2/pair_schedule.json:1)
  - [primary_incidents.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P2/primary_incidents.json:1)
  - [debug_candidates.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_NPT_P2/debug_candidates.json:1)

- `CIMENTACION`
  - [summary.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_CIMENTACION/summary.json:1)
  - [coordinate_audit.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_CIMENTACION/coordinate_audit.json:1)
  - [pair_schedule.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_CIMENTACION/pair_schedule.json:1)
  - [primary_incidents.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_CIMENTACION/primary_incidents.json:1)
  - [debug_candidates.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_CIMENTACION/debug_candidates.json:1)

- `SOTANO`
  - [summary.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_SOTANO/summary.json:1)
  - [coordinate_audit.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_SOTANO/coordinate_audit.json:1)
  - [pair_schedule.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_SOTANO/pair_schedule.json:1)
  - [primary_incidents.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_SOTANO/primary_incidents.json:1)
  - [debug_candidates.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_SOTANO/debug_candidates.json:1)

- `TECHO`
  - [summary.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_TECHO/summary.json:1)
  - [coordinate_audit.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_TECHO/coordinate_audit.json:1)
  - [pair_schedule.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_TECHO/pair_schedule.json:1)
  - [primary_incidents.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_TECHO/primary_incidents.json:1)
  - [debug_candidates.json](C:/Users/Enrique Casanova/Dupla/analysis_output/serena18_analysis_05_runs/analysis_05_TECHO/debug_candidates.json:1)
