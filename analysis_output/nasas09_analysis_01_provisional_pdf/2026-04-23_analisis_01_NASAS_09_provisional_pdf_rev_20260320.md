# Informe Provisional de Clashes

- Fecha: 2026-04-23
- Analisis: 01
- Proyecto: NASAS 09
- Tipo de corrida: provisional PDF-only
- Revision base: entrega 20.03.2026
- Disciplinas incluidas: Arquitectonicos REV. 4 y Tecnicos/Estructural REV. 3

## Alcance y criterio

Esta corrida se hizo como alternativa temporal mientras los `DWG` siguen bloqueados:

- Localmente, los DWG binarios `AC1027/AC1032` no se pueden abrir con `ezdxf`.
- En APS, la traduccion sigue devolviendo `403 ProductAccessRequiresCapacity`.

Por eso esta pasada usa solo:

- `PLANOS ARQ.-LAS NASAS 09-20260320.pdf`
- `PLANOS ESTRUCTURALES-LAS NASAS 09.pdf`

Nota importante:

- Se uso `--mix-issues` solo para esta corrida provisional, porque el PDF estructural no trae la fecha `20.03.2026` en el nombre del archivo.
- Los conflictos de este informe son utiles para orientar revision humana, pero no deben tratarse como clash BIM fino.
- La confianza reportada es `low` en todos los casos.

## Resultado general

- PDFs analizados: 2
- Elementos 2.5D generados: 235
- Conflictos detectados: 87
- JSON base: `analysis_output/nasas09_analysis_01_provisional_pdf/clash_project_report.provisional_pdf.json`

## DWG con clashes entre si

En esta corrida no hay clashes `DWG vs DWG`, porque fue una corrida provisional basada en `PDF`.

Lo que si hay es una lista de conflictos `ARQ PDF vs EST PDF` que sirven para localizar zonas de posible interferencia y preparar la corrida definitiva con `DWG`.

## Principales conflictos detectados

Las ubicaciones se reportan en mm del sistema 2D provisional del runner:

1. `ARQ page 1 cluster 0` vs `EST page 4 cluster 0`
   - IDs: `pdf_PLANOS ARQ.-LAS NASAS 09-20260320_p0_c0` vs `pdf_PLANOS ESTRUCTURALES-LAS NASAS 09_p3_c0`
   - Area de interseccion: `115754.1 mm²`
   - Centro aproximado del clash: `(429.3, 306.8) mm`
   - Bounds aproximados: `(308.4, 67.6, 550.3, 546.0) mm`
   - Niveles: `NPT_P1` vs `NASAS_ARQ_P2_NPT`
   - Confianza: `low`

2. `ARQ page 11 cluster 0` vs `EST page 11 cluster 0`
   - IDs: `pdf_PLANOS ARQ.-LAS NASAS 09-20260320_p10_c0` vs `pdf_PLANOS ESTRUCTURALES-LAS NASAS 09_p10_c0`
   - Area de interseccion: `54426.5 mm²`
   - Centro aproximado del clash: `(210.1, 385.0) mm`
   - Bounds aproximados: `(147.6, 167.2, 272.5, 602.8) mm`
   - Niveles: `NPT_P1` vs `NPT_P1`
   - Confianza: `low`

3. `ARQ page 6 cluster 0` vs `EST page 6 cluster 0`
   - IDs: `pdf_PLANOS ARQ.-LAS NASAS 09-20260320_p5_c0` vs `pdf_PLANOS ESTRUCTURALES-LAS NASAS 09_p5_c0`
   - Area de interseccion: `46136.4 mm²`
   - Centro aproximado del clash: `(394.4, 249.8) mm`
   - Bounds aproximados: `(316.8, 101.1, 472.0, 398.4) mm`
   - Niveles: `NPT_P1` vs `NPT_P1`
   - Confianza: `low`

4. `ARQ page 1 cluster 1` vs `EST page 4 cluster 0`
   - IDs: `pdf_PLANOS ARQ.-LAS NASAS 09-20260320_p0_c1` vs `pdf_PLANOS ESTRUCTURALES-LAS NASAS 09_p3_c0`
   - Area de interseccion: `36700.9 mm²`
   - Centro aproximado del clash: `(231.4, 228.6) mm`
   - Bounds aproximados: `(174.4, 67.6, 288.4, 389.6) mm`
   - Niveles: `NPT_P1` vs `NASAS_ARQ_P2_NPT`
   - Confianza: `low`

5. `ARQ page 11 cluster 0` vs `EST page 11 cluster 1`
   - IDs: `pdf_PLANOS ARQ.-LAS NASAS 09-20260320_p10_c0` vs `pdf_PLANOS ESTRUCTURALES-LAS NASAS 09_p10_c1`
   - Area de interseccion: `34878.3 mm²`
   - Centro aproximado del clash: `(394.4, 411.4) mm`
   - Bounds aproximados: `(348.8, 220.0, 439.9, 602.8) mm`
   - Niveles: `NPT_P1` vs `NPT_P1`
   - Confianza: `low`

6. `ARQ page 10 cluster 0` vs `EST page 10 cluster 0`
   - IDs: `pdf_PLANOS ARQ.-LAS NASAS 09-20260320_p9_c0` vs `pdf_PLANOS ESTRUCTURALES-LAS NASAS 09_p9_c0`
   - Area de interseccion: `31960.1 mm²`
   - Centro aproximado del clash: `(277.2, 223.3) mm`
   - Bounds aproximados: `(220.4, 82.6, 333.9, 364.1) mm`
   - Niveles: `NPT_P1` vs `NPT_P1`
   - Confianza: `low`

7. `ARQ page 10 cluster 0` vs `EST page 10 cluster 2`
   - IDs: `pdf_PLANOS ARQ.-LAS NASAS 09-20260320_p9_c0` vs `pdf_PLANOS ESTRUCTURALES-LAS NASAS 09_p9_c2`
   - Area de interseccion: `27874.5 mm²`
   - Centro aproximado del clash: `(286.3, 497.1) mm`
   - Bounds aproximados: `(220.4, 391.5, 352.3, 602.8) mm`
   - Niveles: `NPT_P1` vs `NPT_P1`
   - Confianza: `low`

8. `ARQ page 3 cluster 0` vs `EST page 3 cluster 0`
   - IDs: `pdf_PLANOS ARQ.-LAS NASAS 09-20260320_p2_c0` vs `pdf_PLANOS ESTRUCTURALES-LAS NASAS 09_p2_c0`
   - Area de interseccion: `24693.1 mm²`
   - Centro aproximado del clash: `(249.2, 427.3) mm`
   - Bounds aproximados: `(147.1, 366.9, 351.3, 487.8) mm`
   - Niveles: `NPT_P1` vs `NPT_P1`
   - Confianza: `low`

9. `ARQ page 1 cluster 1` vs `EST page 4 cluster 1`
   - IDs: `pdf_PLANOS ARQ.-LAS NASAS 09-20260320_p0_c1` vs `pdf_PLANOS ESTRUCTURALES-LAS NASAS 09_p3_c1`
   - Area de interseccion: `21309.9 mm²`
   - Centro aproximado del clash: `(125.7, 134.8) mm`
   - Bounds aproximados: `(49.4, 65.0, 202.0, 204.6) mm`
   - Niveles: `NPT_P1` vs `NASAS_ARQ_P2_NPT`
   - Confianza: `low`

10. `ARQ page 6 cluster 0` vs `EST page 6 cluster 1`
   - IDs: `pdf_PLANOS ARQ.-LAS NASAS 09-20260320_p5_c0` vs `pdf_PLANOS ESTRUCTURALES-LAS NASAS 09_p5_c1`
   - Area de interseccion: `18450.1 mm²`
   - Centro aproximado del clash: `(223.4, 208.9) mm`
   - Bounds aproximados: `(180.6, 101.1, 266.2, 316.6) mm`
   - Niveles: `NPT_P1` vs `NPT_P1`
   - Confianza: `low`

## Lectura tecnica del resultado

Lo bueno:

- Ya no estamos en `0 elementos / 0 clashes`.
- El pipeline esta generando geometria util a nivel de clusters PDF.
- La salida ya localiza zonas de choque y las paginas involucradas.

La limitacion principal:

- Como esto sale de `PDF` y no de `DWG`, muchos choques pueden ser solapes de marcos, detalles o regiones amplias de pagina.
- La presencia de `page_index_fallback` en parte de los niveles baja la confianza.
- Por eso este informe debe verse como una guia de inspeccion, no como veredicto final de coordinacion.

## Siguiente paso recomendado

1. Mantener esta misma revision `20.03.2026` como base del Analisis 01.
2. Resolver la ingestión de `DWG` por una de estas dos vias:
   - habilitar APS Model Derivative sin el `403 ProductAccessRequiresCapacity`
   - exportar la misma cohorte a `DXF`
3. Repetir el analisis definitivo con `DWG`, y entonces si reportar:
   - `DWG vs DWG`
   - ubicacion mas confiable del clash
   - hojas, vistas y niveles con mejor trazabilidad
