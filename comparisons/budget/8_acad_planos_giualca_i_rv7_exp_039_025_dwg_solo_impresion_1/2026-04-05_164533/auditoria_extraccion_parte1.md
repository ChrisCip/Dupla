# Auditoría extracción — Parte 1 (trazabilidad)

## 1. Contexto de corrida

- **project_id:** `8_acad_planos_giualca_i_rv7_exp_039_025_dwg_solo_impresion_1`
- **plan_image_paths:** 1 imagen(es)
- **pipeline (inferido):** `visión + CAD`
- **vision_pages_dir:** `C:\Users\Enrique Casanova\Dupla\comparisons\budget\8_acad_planos_giualca_i_rv7_exp_039_025_dwg_solo_impresion_1\2026-04-05_164533\rendered_pages\p_74be01ecffa7aafd`
- **dwg_path:** `C:\Users\Enrique Casanova\Dupla\8- ACAD-PLANOS GIUALCA I - RV7 - EXP.039-025.dwg SOLO IMPRESION (1).dwg`

## 2. Inventario híbrido (origen por entidad)

### Nivel `page_0001` — page_0001 — source nivel: `hybrid`
| Entidades por source | Cantidad |
| --- | ---: |
| json | 3 |


## 3. Takeoffs — de dónde sale la cantidad

Reglas (`rules_engine`) expanden takeoffs base; las cantidades vienen de fórmulas sobre inventario (determinístico salvo supuestos listados).

- **Takeoffs base (pre-reglas):** 5
- **Takeoffs finales (post-reglas):** 11

| item_key | item_type | qty | ud | trace sources | #asunciones |
| --- | --- | ---: | --- | --- | ---: |
| `json-wall-a-wall:length` | wall_length | 4088.205999999992 | m | json | 0 |
| `json-wall-a-wall:length:wall_length_finish_standard:finish_plaster` | wall_finish_plaster | 22893.953599999953 | m2 | json | 1 |
| `json-wall-a-wall:length:wall_length_finish_standard:finish_paint` | wall_finish_paint | 22893.953599999953 | m2 | json | 1 |
| `json-wall-a-wall-patt:length` | wall_length | 1925.1720000001642 | m | json | 0 |
| `json-wall-a-wall-patt:length:wall_length_finish_standard:finish_plaster` | wall_finish_plaster | 10780.963200000919 | m2 | json | 1 |
| `json-wall-a-wall-patt:length:wall_length_finish_standard:finish_paint` | wall_finish_paint | 10780.963200000919 | m2 | json | 1 |
| `json-beam-s-beam:count` | structural_count | 1.0 | unit | json | 0 |
| `json-beam-s-beam:length` | structural_length | 57.66000000000004 | m | json | 0 |
| `json-beam-s-beam:beam_length` | beam_length | 57.66000000000004 | m | json | 0 |
| `json-beam-s-beam:beam_length:beam_length_concrete_standard:concrete_volume` | beam_concrete_volume | 8.649000000000006 | m3 | json | 1 |
| `json-beam-s-beam:beam_length:beam_length_concrete_standard:formwork` | beam_formwork_area_hint | 74.95800000000006 | m2 | json | 1 |

## 4. Compositor de presupuesto (qué entra y qué no)

| Métrica | Valor |
| --- | ---: |
| budget_inclusive | True |
| takeoffs_budgetable | 6 |
| takeoffs_excluded | 5 |
| takeoffs_total | 11 |

**Excluidos por razón:**
- `derived_child`: 3
- `type_excluded`: 2

**Tipos excluidos (top):**
- `wall_length`: 2
- `structural_count`: 1
- `structural_length`: 1
- `beam_length`: 1

## 5. Clasificador BC3 (IA vs determinístico)

- **gpt4o:** clasificación por capítulo con GPT-4o sobre subconjunto BC3 (requiere `OPENAI_API_KEY`).
- **keyword_match:** ranking por solapamiento de tokens con el catálogo (fallback si no hay GPT o falla).

| takeoff_key | Candidato top | source | rationale (recorte) |
| --- | --- | --- | --- |
| `json-wall-a-wall:length` | `—` | `—` | — |
| `json-wall-a-wall:length:wall_length_finish_standard:finish_plaster` | `P0501101` | `gpt4o` | {"unit_price": 544.9, "match_type": "aproximado"} |
| `json-wall-a-wall:length:wall_length_finish_standard:finish_paint` | `P1801102` | `gpt4o` | {"unit_price": 548.7, "match_type": "aproximado"} |
| `json-wall-a-wall-patt:length` | `—` | `—` | — |
| `json-wall-a-wall-patt:length:wall_length_finish_standard:finish_plaster` | `P0501101` | `gpt4o` | {"unit_price": 544.9, "match_type": "aproximado"} |
| `json-wall-a-wall-patt:length:wall_length_finish_standard:finish_paint` | `P1801102` | `gpt4o` | {"unit_price": 548.7, "match_type": "aproximado"} |
| `json-beam-s-beam:count` | `—` | `—` | — |
| `json-beam-s-beam:length` | `—` | `—` | — |
| `json-beam-s-beam:beam_length` | `—` | `—` | — |
| `json-beam-s-beam:beam_length:beam_length_concrete_standard:concrete_volume` | `M040108` | `gpt4o` | {"unit_price": 9400.0, "match_type": "aproximado"} |
| `json-beam-s-beam:beam_length:beam_length_concrete_standard:formwork` | `H0502195` | `gpt4o` | {"unit_price": 1400.0, "match_type": "aproximado"} |

## 6. Cómo saber si la extracción es “la mejor posible” (Parte 1)

1. **CAD:** revisá que `normalized.json` y el inventario `json`/`hybrid` reflejen capas y geometría esperables.
2. **Visión:** si hay `plan_image_paths`, revisá que `conflict_notes` tengan sentido (no silenciar diferencias).
3. **Reglas:** si muchos takeoffs quedan excluidos por `derived_child` o `type_excluded`, es el diseño del compositor, no un bug de APS.
4. **IA:** si `source` es `keyword_match` en casi todo, el GPT no está actuando o falló (ver logs).

