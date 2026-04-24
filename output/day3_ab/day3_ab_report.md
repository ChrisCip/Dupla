# Day 3 A/B Calibration Report

## Scope

- Disciplines: arquitectura, estructura
- Comparison: baseline vs enhanced flow with threshold sweep
- Go/No-Go threshold: +10.0% in both coverage and quantity accuracy

## Column definitions

- `coverage`: percentage of PRES real codes that are present in generated output.
- `qty_accuracy`: average quantity precision over matching codes.
- `price_accuracy`: average unit-price precision over matching codes.
- `delta_cov`: enhanced coverage minus baseline coverage.
- `delta_qty`: enhanced quantity accuracy minus baseline quantity accuracy.

## Winning threshold: 0.75

| Discipline | Baseline coverage | Enhanced coverage | delta_cov | Baseline qty_accuracy | Enhanced qty_accuracy | delta_qty | Baseline price_accuracy | Enhanced price_accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arquitectura | 0.00% | 0.00% | +0.00% | 0.00% | 0.00% | +0.00% | 0.00% | 0.00% |

## Threshold sweep summary

| Threshold | Avg delta_cov | Avg delta_qty | Avg delta_price |
| --- | ---: | ---: | ---: |
| 0.75 | +0.00% | +0.00% | +0.00% |

## Decision

- Result: NO-GO

## Notes

- arquitectura: delta_cov=+0.00%, delta_qty=+0.00% -> NO
