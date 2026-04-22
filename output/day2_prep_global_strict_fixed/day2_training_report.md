# Day 2 training dataset report

- PRES sources: 2
- Primary source: `C:\Users\jimif\Documents\Code\Dupla\data\PRES.xlsx`
- Validation limit: 60
- Min source quality: 0.75
- Total pairs extracted: 3397
- Train records: 3320
- Validation records: 60
- Methodology context chars: 10040

## Top item types

- generic_construction_item: 1703
- wall: 322
- column: 302
- beam: 278
- fixture_count: 148
- floor_finish: 129
- wall_finish_plaster: 109
- footing: 91
- door_count: 84
- slab: 81

## Top disciplines

- Hormigón armado: 544
- HORMIGON ARMADO: 305
- INSTALACION ELECTRICA: 187
- SISTEMA DE AGUA POTABLE FRIA Y CALIENTE: 180
- SISTEMA DE DRENAJE DE AGUAS NEGRAS: 174
- General: 144
- TERMINACIÓN DE SUPERFICIES: 124
- Techos: 88
- Terminaciones de superficies de muros, columnas y vigas: 84
- APARATOS SANITARIOS: 80

## Source pair counts

- C:\Users\jimif\Documents\Code\Dupla\data\PRES.xlsx: 1565
- C:\Users\jimif\Documents\Code\Dupla\data\Prelimary Budget NASAS 9-2, 17-02-2026.xlsx: 1832

## Source quality scores

- C:\Users\jimif\Documents\Code\Dupla\data\PRES.xlsx: 100
- C:\Users\jimif\Documents\Code\Dupla\data\Prelimary Budget NASAS 9-2, 17-02-2026.xlsx: 100

## Validation examples

| record_id | item_type | context | target_code | target_unit |
| --- | --- | --- | --- | --- |
| validation_0001 | beam | Misceláneos \| Hormigón armado | 11.31 | M3 |
| validation_0002 | column | Misceláneos \| Hormigón armado | 11.01 | M3 |
| validation_0003 | door_count | Miscelaneos \| Suministro e instalción de PTR refuerzo de puertas pockets y mamparas | 18.04 | PA |
| validation_0004 | fixture_count | Miscelaneos \| Obras civiles complementarias | 25.01 | UD |
| validation_0005 | floor_finish | Misceláneos \| Equipos de baños | 10.06 | UD |
| validation_0006 | footing | Miscelaneos \| Hormigón armado de piscina | 18.05 | M3 |
| validation_0007 | generic_construction_item | EQUIPOS ELECTRICOS \| EQUIPOS DE POTENCIA | %MOELEC | PA |
| validation_0008 | slab | Misceláneos \| Hormigón armado | 11.37 | M3 |
| validation_0009 | wall | Misceláneos \| Muros de bloques | 10.01 | M2 |
| validation_0010 | wall_finish_paint | Misceláneos \| Techos | 13.07 | M2 |
| validation_0011 | wall_finish_plaster | Misceláneos \| Terminaciones de superficies de muros, columnas y vigas | 13.02 | M2 |
| validation_0012 | wet_area_fixture_count | Misceláneos \| Equipos de baños | 10.01 | UD |

## Dataset bundle

- Train JSONL: `C:\Users\jimif\Documents\Code\Dupla\output\day2_prep_global_strict_fixed\day2_train.jsonl`
- Validation JSONL: `C:\Users\jimif\Documents\Code\Dupla\output\day2_prep_global_strict_fixed\day2_validation.jsonl`
- Manifest: `C:\Users\jimif\Documents\Code\Dupla\output\day2_prep_global_strict_fixed\day2_training_manifest.json`
