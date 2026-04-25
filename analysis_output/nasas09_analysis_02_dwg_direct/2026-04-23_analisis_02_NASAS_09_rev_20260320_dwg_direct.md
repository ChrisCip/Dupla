# NASAS 09 - Analisis 02

- Fecha: 2026-04-23
- Analisis: 02
- Proyecto: NASAS 09
- Revision base: 20.03.2026
- Modalidad: DWG nativo por Civil 3D COM, sin conversion a DXF

## Resumen Ejecutivo

- Corrida DWG directa: 744 elementos y 193 clashes HARD.
- Corrida provisional sin DWG (PDF-only): 235 elementos y 87 clashes HARD.
- Diferencia principal: la corrida DWG ya detecta choques CAD reales, pero la cobertura de archivos sigue parcial por rechazos COM de Civil 3D en algunos estructurales y por filtros agresivos en arquitectura.

## Cobertura Real de Esta Corrida

- Arquitectura: `PLANOS ARQ.-LAS NASAS 09-20260320.dwg` quedo con 1 elemento util tras el filtrado actual.
- Electrico: `20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg` cargo 350 elementos.
- Estructura: `ES-05@11- PLANTAS ENTREPISO...dwg` cargo 350 elementos y `ES-12-DETALLES DE ENCOFRADO.dwg` cargo 43 elementos.
- Estructura no cargada en esta pasada: `ES-01-DETALLES GENERALES.dwg`, `ES-02@04-CIMIENTOS...dwg` y `REF. COLUMNAS-LAS NASAS.dwg`.
- Confianza global: `medium` en todos los clashes del JSON porque la geometria proviene de bounding boxes COM de DWG, no de vertices exactos.

## Pares con Clashes

- `20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg` vs `20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg`: 190 clashes.
- `20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg` vs `PLANOS ARQ.-LAS NASAS 09-20260320.dwg`: 2 clashes.
- `20.03.2026 LAS NASAS 09 ES-12-DETALLES DE ENCOFRADO.dwg` vs `PLANOS ARQ.-LAS NASAS 09-20260320.dwg`: 1 clash.

## Top 10 Clashes

- 20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg [E Tuberia Emp Piso] vs 20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg [Columnas] | area ~ 11.09 m2 | centro aprox. (54189.8, -138392.4) mm | confianza medium
- 20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg [E Tuberia Emp Piso] vs 20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg [Columnas] | area ~ 9.55 m2 | centro aprox. (54191.4, -140740.7) mm | confianza medium
- 20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg [E Tuberia Emp Piso] vs 20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg [Columnas] | area ~ 8.57 m2 | centro aprox. (38051.6, -138241.6) mm | confianza medium
- 20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg [E Linea MT 3F Soterrada Prop] vs 20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg [VIGA-LOSA] | area ~ 2.68 m2 | centro aprox. (19079.4, -228819.9) mm | confianza medium
- 20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg [E Tuberia Emp Piso] vs 20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg [Columnas] | area ~ 1.33 m2 | centro aprox. (56202.8, -153483.1) mm | confianza medium
- 20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg [E Tuberia Emp Piso] vs 20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg [Columnas] | area ~ 1.31 m2 | centro aprox. (48778.4, -155771.7) mm | confianza medium
- 20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg [E Tuberia Emp Piso] vs 20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg [Columnas] | area ~ 1.11 m2 | centro aprox. (54176.4, -155829.3) mm | confianza medium
- 20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg [E Tuberia Emp Piso] vs 20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg [Columnas] | area ~ 0.97 m2 | centro aprox. (54043.2, -151113.3) mm | confianza medium
- 20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg [E Tuberia Telefonica] vs 20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg [Columnas] | area ~ 0.9 m2 | centro aprox. (29402.4, -208606.6) mm | confianza medium
- 20.03.2026 LAS NASAS 09-PLANOS ELECTRICOS .dwg [E Tuberia Emp Piso] vs 20.03.2026 LAS NASAS 09 ES-05@11- PLANTAS ENTREPISO-LAS NASAS-DESSANGLES.dwg [Columnas] | area ~ 0.9 m2 | centro aprox. (53726.7, -142942.1) mm | confianza medium

## Lectura Tecnica

- El grupo dominante ya no es arquitectura contra leyendas electricas; ahora la mayor concentracion de choques esta entre capas electricas como `E Tuberia Emp Piso`, `E Tuberia Telefonica` y elementos estructurales como `Columnas` y `VIGA-LOSA`.
- Eso sugiere que la revision 20.03.2026 si tiene material CAD util para revisar coordinacion entre tecnicos, especialmente electrico vs estructura.
- La parte arquitectonica necesita una iteracion adicional de filtrado/apertura porque quedo subrepresentada en esta pasada final.

## Archivos

- JSON DWG directo: `analysis_output/nasas09_analysis_02_dwg_direct/clash_project_report.analysis_02_dwg_direct.json`
- Informe DWG directo: `analysis_output/nasas09_analysis_02_dwg_direct/2026-04-23_analisis_02_NASAS_09_rev_20260320_dwg_direct.md`
- Informe sin DWG para comparar: `analysis_output/nasas09_analysis_01_provisional_pdf/2026-04-23_analisis_01_NASAS_09_provisional_pdf_rev_20260320.md`
