# Day 1 training prep report

- PRES source: `C:\Users\jimif\Documents\Code\Dupla\data\Prelimary Budget NASAS 9-2, 17-02-2026.xlsx`
- Holdout limit: 40
- Training pairs extracted: 458
- Unique item types: 2
- Unique units: 343
- Unique contexts: 46
- Level templates detected: 46

## Top item types

- generic_construction_item: 450
- wall_finish_plaster: 8

## Top disciplines

- Reinforced Concrete: 136
- Classic coraline stone floor 0.30m x 0.60m Sup US$28.33: 25
- Roofs: 22
- Surface finishes of walls, columns, and beams: 21
- Bathroom fixtures: 21
- Roof Finishes:: 20
- Walls: 17
- Surface finishes of walls: 14
- Masonry Walls: 13
- Wooden beams: 11

## Holdout examples

| code | item_type | unit | context | description |
| --- | --- | --- | --- | --- |
| 1.01 | generic_construction_item | Fumigación | Sin Nivel | Preliminary Works | Fumigation (foundations) |
| 13.01 | wall_finish_plaster | Fraguache de columnas, vigas y dinteles | Sin Nivel | Surface finishes of walls, columns, and beams | Fraguache (cement adherence) on concrete columns, beams and lintels |
| 1.02 | generic_construction_item | Limpieza del solar | Sin Nivel | Preliminary Works | Lot cleaning |
| 13.02 | wall_finish_plaster | Fraguache de muro de hormigón | Sin Nivel | Surface finishes of walls, columns, and beams | Fraguache (cement adherence) on concrete walls |
| 10.01 | generic_construction_item | Muros (8") AC. Ø 3/8" SNP | Sin Nivel | Masonry Walls | Block Walls (8") AC. Ø 3/8" AFL |
| 14.01 | wall_finish_plaster | Fraguache de techos | Sin Nivel | Roof Finishes: | Fraguache (cement adherence) on concrete ceilings |
| 10.02 | generic_construction_item | Muros (6") AC. Ø 3/8" SNP | Sin Nivel | Masonry Walls | Block Walls (6") AC. Ø 3/8" AFL |
| 15.01 | wall_finish_plaster | Fraguache de columnas, vigas y dinteles | Sin Nivel | Surface finishes of walls, columns, and beams | Fraguache (cement adherence) on concrete columns, beams and lintels |
| 10.03 | generic_construction_item | Muros (8") AC. Ø 3/8" SNP de enrase | Sin Nivel | Masonry Walls | Block Walls (8") AC. Ø 3/8"  AFL up to roof |
| 15.02 | wall_finish_plaster | Fraguache de muro de hormigón | Sin Nivel | Surface finishes of walls, columns, and beams | Fraguache (cement adherence) on concrete walls |
| 10.04 | generic_construction_item | Muros (6") AC. Ø 3/8" SNP de enrase | Sin Nivel | Masonry Walls | Block Walls (6") AC. Ø 3/8"  AFL up to roof |
| 16.01 | wall_finish_plaster | Fraguache de techos | Sin Nivel | Roof Finishes: | Fraguache (cement adherence) on concrete ceilings |
| 11.01 | generic_construction_item | Columna C1 (0.35m x 0.35m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Column C1(0.35m x 0.35m) with 240 kg/cm² concrete |
| 20.01 | wall_finish_plaster | Fraguache de superficies de hormigón | Sin Nivel | Surface finishes of walls | Fraguache (cement adherence) on concrete walls and slab |
| 11.02 | generic_construction_item | Columna C4 (0.60m x 0.25m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Column C4 (0.60m x 0.25m) with 240 kg/cm² concrete |
| 23.01 | wall_finish_plaster | Fraguache de superficies de hormigón | Sin Nivel | Surface finishes of walls | Fraguache (cement adherence) on concrete walls and slab |
| 11.03 | generic_construction_item | Columna C5 (0.25m x 0.25m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Column C5 (0.25m x 0.25m) with 240 kg/cm² concrete |
| 11.04 | generic_construction_item | Columna C6 (0.50m x 0.30m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Column C6 (0.50m x 0.30m) with 240 kg/cm² concrete |
| 11.05 | generic_construction_item | Columna C7 (0.60m x 0.25m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Column C7 (0.60m x 0.25m) with 240 kg/cm² concrete |
| 11.06 | generic_construction_item | Columna CA (0.20m x 0.20m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Column CA (0.20m x 0.20m)with 240 kg/cm² concrete |
| 11.07 | generic_construction_item | Muro Horm. MH1 (0.80m x 0.30m), con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Concrete wall MH1 (0.80m x 0.30m), with 240 kg/cm² concrete |
| 11.08 | generic_construction_item | Muro Horm. MH2 (1.20m x 0.25m), con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Concrete wall MH2 (1.20m x 0.25m), with 240 kg/cm² concrete |
| 11.09 | generic_construction_item | Muro Horm. MH3 en L (2.60m x 0.25m), con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Concrete wall MH3 L shaped (2.60m x 0.25m), with 240 kg/cm² concrete |
| 11.10 | generic_construction_item | Muro Horm. MH4 (1.80m x 0.30m), con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Concrete wall MH4 (1.80m x 0.30m), with 240 kg/cm² concrete |
| 11.11 | generic_construction_item | Muro Horm. MH5 (1.00m x 0.30m), con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Concrete wall MH5 (1.00m x 0.30m), with 240 kg/cm² concrete |
| 11.12 | generic_construction_item | Cepos en columnas y muros de hormigón bnp | Sin Nivel | Reinforced Concrete | Wooden formwork to stabilize steel |
| 11.13 | generic_construction_item | Pórtico eje AX (0.25m x 0.80m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis AX (0.25m x 0.80m) with 240 kg/cm² concrete |
| 11.14 | generic_construction_item | Pórtico eje AX-1 (0.25m x 0.90m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis AX-1 (0.25m x 0.90m)with 240 kg/cm² concrete |
| 11.15 | generic_construction_item | Pórtico eje CX (0.25m x 0.60m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis CX (0.25m x 0.60m) with 240 kg/cm² concrete |
| 11.16 | generic_construction_item | Pórtico eje CX' (0.25m x 0.60m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis CX' (0.25m x 0.60m)  with 240 kg/cm² concrete |
| 11.17 | generic_construction_item | Pórtico eje CX-1 (0.25m x 0.90m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis CX-1 (0.25m x 0.90m) with 240 kg/cm² concrete |
| 11.18 | generic_construction_item | Pórtico eje EX (0.25m x 0.60m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis EX (0.25m x 0.60m)  with 240 kg/cm² concrete |
| 11.19 | generic_construction_item | Pórtico eje GX (0.25m x 0.60m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis GX (0.25m x 0.60m) with 240 kg/cm² concrete |
| 11.20 | generic_construction_item | Pórtico eje GX' (0.25m x 0.60m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis GX' (0.25m x 0.60m) with 240 kg/cm² concrete |
| 11.21 | generic_construction_item | Pórtico eje GX-1 (0.25m x 0.90m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis GX-1 (0.25m x 0.90m) with 240 kg/cm² concrete |
| 11.22 | generic_construction_item | Pórtico eje HX (0.30m x 0.80m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis HX (0.30m x 0.80m) with 240 kg/cm² concrete |
| 11.23 | generic_construction_item | Pórtico eje HX-1 (0.30m x 0.75m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis HX-1 (0.30m x 0.75m) with 240 kg/cm² concrete |
| 11.24 | generic_construction_item | Pórtico eje 5Y (0.25m x 0.60m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis 5Y (0.25m x 0.60m) with 240 kg/cm² concrete |
| 11.25 | generic_construction_item | Pórtico eje 6Y (0.25m x 0.60m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis 6Y (0.25m x 0.60m) with 240 kg/cm² concrete |
| 11.26 | generic_construction_item | Pórtico eje 7Y (0.25m x 0.60m) con hormigón 240 kg/cm2 | Sin Nivel | Reinforced Concrete | Beam axis 7Y (0.25m x 0.60m) with 240 kg/cm² concrete |

## Baseline comparison

_No generated workbook supplied, so only the dataset prep bundle was written._
