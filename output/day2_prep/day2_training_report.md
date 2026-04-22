# Day 2 training dataset report

- PRES source: `C:\Users\jimif\Documents\Code\Dupla\data\PRES.xlsx`
- Validation limit: 40
- Total pairs extracted: 1565
- Train records: 1462
- Validation records: 40
- Methodology context chars: 8449

## Top item types

- generic_construction_item: 655
- beam: 174
- column: 174
- fixture_count: 144
- floor_finish: 89
- wall: 86
- door_count: 68
- wall_finish_paint: 49
- wet_area_fixture_count: 35
- slab: 33

## Top disciplines

- HORMIGON ARMADO: 305
- INSTALACION ELECTRICA: 187
- SISTEMA DE AGUA POTABLE FRIA Y CALIENTE: 180
- SISTEMA DE DRENAJE DE AGUAS NEGRAS: 174
- TERMINACIÓN DE SUPERFICIES: 124
- General: 116
- APARATOS SANITARIOS: 80
- PUERTAS: 63
- PINTURA: 60
- SISTEMA CONTRA INCENDIOS: 45

## Validation examples

| record_id | item_type | context | target_code | target_unit |
| --- | --- | --- | --- | --- |
| validation_0001 | beam | NIVEL 2 (PARQUEOS) N3.05 \| HORMIGON ARMADO | P030301Y | m3 |
| validation_0002 | column | MISCELANEOS \| SISTEMA DE DRENAJE DE AGUAS NEGRAS | A.0043BD3 | ud |
| validation_0003 | door_count | NIVEL 1 (LOBBY-PARQUEOS) N0.00 \| PUERTAS | P1201300 | m2 |
| validation_0004 | fixture_count | MISCELANEOS \| INSTALACION ELECTRICA | A.0103 | ud |
| validation_0005 | floor_finish | MISCELANEOS \| SISTEMA DE DRENAJE DE AGUAS NEGRAS | A.0055DP2 | ud |
| validation_0006 | footing | Sin Nivel \| PRELIMINARES | P0112200 | m2 |
| validation_0007 | generic_construction_item | EQUIPOS ELECTRICOS \| EQUIPOS DE POTENCIA | %MOELEC | PA |
| validation_0008 | slab | MISCELANEOS \| HORMIGON ARMADO | LOSTCI | m3 |
| validation_0009 | wall | MISCELANEOS \| General | DENSG | m2 |
| validation_0010 | wall_finish_paint | NIVEL 1 (LOBBY-PARQUEOS) N0.00 \| PINTURA | P1801100 | m² |
| validation_0011 | wall_finish_plaster | NIVEL 1 (LOBBY-PARQUEOS) N0.00 \| TERMINACIÓN DE SUPERFICIES | P0501101 | m² |
| validation_0012 | wet_area_fixture_count | MISCELANEOS \| APARATOS SANITARIOS | A.0072 | ud |

## Dataset bundle

- Train JSONL: `C:\Users\jimif\Documents\Code\Dupla\output\day2_prep\day2_train.jsonl`
- Validation JSONL: `C:\Users\jimif\Documents\Code\Dupla\output\day2_prep\day2_validation.jsonl`
- Manifest: `C:\Users\jimif\Documents\Code\Dupla\output\day2_prep\day2_training_manifest.json`
