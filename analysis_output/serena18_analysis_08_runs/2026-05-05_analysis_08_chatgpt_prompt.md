# Prompt para ChatGPT - analysis_08 - SERENA 18

Copia y pega este prompt en ChatGPT para obtener un informe portfolio mas humano, ejecutivo y util para revision interdisciplinaria.

```text
Actua como un coordinador tecnico senior de proyectos AEC.
Quiero que redactes un informe consolidado, humano y profesional, en espanol neutro, a partir de varias corridas de coordinacion 2.5D del mismo proyecto.

Objetivo del informe:
- resumir el estado general de coordinacion por alcance o nivel
- separar claramente hallazgos defendibles vs ruido tecnico
- identificar que corridas ya son presentables y cuales siguen en validacion
- proponer un orden de revision interdisciplinaria

Reglas:
- no inventes informacion no presente en los datos
- no conviertas debug o hotspots en hallazgos finales
- cuando una corrida no tenga hallazgos defendibles, dilo claramente
- si una disciplina no tiene cobertura real, dilo
- escribe como un informe tecnico para equipo real, no como log ni como salida automatica

Estructura requerida:
1. Resumen ejecutivo consolidado
2. Corridas ya presentables
3. Corridas que siguen en validacion
4. Hallazgos defendibles prioritarios por alcance
5. Lectura por perfiles de revisor
6. Limites tecnicos y ruido detectado
7. Recomendaciones para la siguiente ronda

Datos portfolio:
- portfolio_label: analysis_08
- generated_at: 2026-05-05
- run_count: 6
- scheduled_pairs_total: 16
- primary_incidents_total: 277
- defendable_incidents_total: 184
- validation_incidents_total: 93
- debug_conflicts_total: 3411
- suppressed_elements_total: 4297

Corridas incluidas:
- analysis_08_NPT_P1 | status=completed | scheduled_pairs=2 | primary_incidents=53 | defendable_incidents=6 | validation_incidents=47 | debug_conflicts=179
  - pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | incidents=36 | members=253 | top_priority=P2 | confidence_mix=low=31, medium=5 | severity_mix=low=23, medium=9, high=4
  - pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg | incidents=17 | members=70 | top_priority=P2 | confidence_mix=low=16, medium=1 | severity_mix=low=13, medium=3, high=1
  - defendable=incident_0026 | priority=P2 | severity=high | confidence=medium | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | location=NPT_P1; (168,817,815, 624,648,464) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - defendable=incident_0021 | priority=P2 | severity=high | confidence=medium | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | location=NPT_P1; (168,812,817, 624,648,464) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - defendable=incident_0034 | priority=P2 | severity=high | confidence=medium | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg | location=NPT_P1; (168,832,736, 624,649,470) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - defendable=incident_0051 | priority=P2 | severity=high | confidence=medium | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E09 - PLANTA EST. LOSAS DE PISO SOBRE TERRENO  Y DETALLES  CASA.dwg | location=NPT_P1; (168,826,979, 624,644,583) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - validation=incident_0029 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg
  - validation=incident_0020 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg
  - validation=incident_0017 | reason=low confidence signal | level=NPT_P1 | pair=Serena 18 -PLANTA PISOS 10-10-2022.dwg vs EST. SERENA 18 - E03 - PLANO DE ENCOFRADO.dwg
- analysis_08_NPT_P2 | status=completed | scheduled_pairs=3 | primary_incidents=66 | defendable_incidents=46 | validation_incidents=20 | debug_conflicts=769
  - pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | incidents=31 | members=115 | top_priority=P1 | confidence_mix=medium=23, high=8 | severity_mix=medium=13, low=9, high=8, critical=1
  - pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | incidents=27 | members=102 | top_priority=P1 | confidence_mix=medium=19, high=8 | severity_mix=medium=10, high=8, low=8, critical=1
  - pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E10 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (1).dwg | incidents=8 | members=23 | top_priority=P2 | confidence_mix=medium=8 | severity_mix=medium=5, low=3
  - defendable=incident_0019 | priority=P1 | severity=critical | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | location=NPT_P2; (168,832,051, 624,560,950) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - defendable=incident_0050 | priority=P1 | severity=critical | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | location=NPT_P2; (168,832,051, 624,560,950) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - defendable=incident_0027 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg | location=NPT_P2; (168,835,479, 624,569,513) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - defendable=incident_0058 | priority=P1 | severity=high | confidence=high | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg | location=NPT_P2; (168,835,479, 624,569,513) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - validation=incident_0023 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg
  - validation=incident_0054 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E12 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD. II).dwg
  - validation=incident_0028 | reason=line-based geometry needs manual confirmation | level=NPT_P2 | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E11 - PLANTA EST. DE ENTREPISO Y  DETALLES  CASA (MOD.I).dwg
- analysis_08_CIMENTACION | status=completed | scheduled_pairs=2 | primary_incidents=1 | defendable_incidents=1 | validation_incidents=0 | debug_conflicts=706
  - pair=2208-Serena18-ID-Base.dwg vs EST. SERENA 18 - E06 - PLANTA EST. CIMIENTOS Y DETALLES  CASA.dwg | incidents=1 | members=1 | top_priority=P2 | confidence_mix=medium=1 | severity_mix=medium=1
  - defendable=incident_0000 | priority=P2 | severity=medium | confidence=medium | level=CIMENTACION | pair=2208-Serena18-ID-Base.dwg vs EST. SERENA 18 - E06 - PLANTA EST. CIMIENTOS Y DETALLES  CASA.dwg | location=CIMENTACION; (168,816,577, 624,649,583) mm | action=Revisar el par directamente y revisar con validacion acotada.
- analysis_08_SOTANO | status=completed | scheduled_pairs=2 | primary_incidents=0 | defendable_incidents=0 | validation_incidents=0 | debug_conflicts=429
- analysis_08_TECHO | status=completed | scheduled_pairs=6 | primary_incidents=157 | defendable_incidents=131 | validation_incidents=26 | debug_conflicts=1262
  - pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E18 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. I).dwg | incidents=30 | members=192 | top_priority=P1 | confidence_mix=medium=19, high=11 | severity_mix=high=10, medium=10, low=7, critical=3
  - pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg | incidents=29 | members=190 | top_priority=P1 | confidence_mix=medium=19, high=10 | severity_mix=medium=11, high=9, low=5, critical=4
  - pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg | incidents=29 | members=208 | top_priority=P1 | confidence_mix=medium=19, high=10 | severity_mix=medium=12, high=9, critical=5, low=3
  - pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg | incidents=28 | members=196 | top_priority=P1 | confidence_mix=medium=17, high=11 | severity_mix=medium=11, high=7, critical=6, low=4
  - defendable=incident_0076 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E16 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. II).dwg | location=TECHO; (168,841,135, 624,666,914) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - defendable=incident_0036 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg | location=TECHO; (168,835,779, 624,670,611) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - defendable=incident_0043 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg | location=TECHO; (168,839,897, 624,668,453) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - defendable=incident_0046 | priority=P1 | severity=critical | confidence=high | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E15 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES (MOD. I).dwg | location=TECHO; (168,841,274, 624,666,898) mm | action=Revisar el par directamente y escalar en la siguiente ronda de coordinacion.
  - validation=incident_0016 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E14 - PLANTA EST. DE TECHOS T1 EN MADERA Y DETALLES.dwg
  - validation=incident_0122 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E18 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. I).dwg
  - validation=incident_0144 | reason=line-based geometry needs manual confirmation | level=TECHO | pair=2208-Serena18-ID-Base-UpperFloor.dwg vs EST. SERENA 18 - E19 - PLANTA EST. DE TECHOS T2 EN MADERA Y DETALLES (MOD. II).dwg
- analysis_08_ARQ_HS_P1 | status=completed | scheduled_pairs=1 | primary_incidents=0 | defendable_incidents=0 | validation_incidents=0 | debug_conflicts=66

Devuelveme solo el informe final en markdown, sin explicar tu proceso.
```
