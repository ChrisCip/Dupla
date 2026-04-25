# Analysis 04 - SERENA 18

- Perfil: `fast_compare`
- Cohorte: `analysis_03_serena18_arq_est_manual`
- Fecha: `2026-04-25`

## Resultado

- `18` archivos auditados
- `45` pares evaluados por scheduler
- `0` pares programados
- `0` elementos extraidos para clash
- `0` incidencias primarias
- `0` conflictos debug

## Que cambio respecto a analysis_03

- El `coordinate_audit` ya no usa el bbox global contaminado del DWG.
- Ahora usa el **cluster primario dominante** por archivo para asignar banda de coordenadas.
- Eso hizo el audit mas creible: ya no estamos viendo centroides absurdos por outliers globales.

## Hallazgo principal

El resultado sigue siendo `0`, pero ahora por una razon mas confiable:

- `2208-Serena18-ID-Base.dwg` y `2208-Serena18-ID-Base-UpperFloor.dwg` quedaron en banda `X~0.03M/0.09M, Y~0.04M/0.06M`
- `Serena 18 -PLANTA PISOS 10-10-2022.dwg` quedo en banda `X~173.69M, Y~624.14M`
- La estructura `E03-E19` quedo estable alrededor de `X~168.80M-168.82M, Y~624.62M-624.65M`

Eso significa:

- los `Base*.dwg` siguen claramente fuera de sistema
- el archivo arquitectonico mas prometedor (`PLANTA PISOS`) **tampoco** coincide con la estructura

## Diferencia relevante ARQ vs EST

Tomando como referencia:

- ARQ: `Serena 18 -PLANTA PISOS 10-10-2022.dwg`
- EST: `EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg`

La separacion aproximada entre centroides dominantes es:

- `dX ~= +4,875,269 mm`
- `dY ~= -501,979 mm`

Esto ya no parece ruido de outliers; parece una **desalineacion real de insercion / sistema de coordenadas**.

## Conclusión

`analysis_04` confirma que el problema ya no es el conteo de clashes, sino la comparabilidad espacial entre arquitectura y estructura.

El siguiente paso correcto ya no es relajar filtros.
El siguiente paso correcto es:

1. definir una alineacion manual confiable para `ARQ`
2. aplicar esa transformacion al audit / scheduler
3. correr una nueva pasada `ARQ vs EST`
