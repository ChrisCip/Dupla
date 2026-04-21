# Comparaciones presupuesto (Dupla vs PRES)

Cada corrida genera una carpeta bajo `comparisons/budget/<proyecto>/<YYYY-MM-DD_HHMMSS>/` con:

- `dupla_presupuesto_generado.xlsx` — salida del pipeline Dupla.
- `PRES_referencia.xlsx` — copia del PRES usado como baseline (la que comparaste).
- `diferencias_YYYY-MM-DD.md` — análisis en Markdown (métricas, tablas, códigos solo en uno u otro).
- `comparison_report.txt` — mismo análisis en texto plano (legado).
- `README_CORRIDA.txt` — rutas y etiqueta de corrida.
- `run.log` — log de la ejecución.

## Cómo lanzar una nueva corrida

Desde la raíz del repositorio:

```bash
# Programa completo (APS + PDF render + GPT-4o visión + presupuesto). Requiere PDF.
python scripts/run_dw_pres_compare.py --pipeline full --pdf ruta\al\plano.pdf

# Si el PDF está junto al DWG y tiene el mismo nombre base, se detecta solo.
python scripts/run_dw_pres_compare.py --pipeline full

# Solo CAD (sin visión)
python scripts/run_dw_pres_compare.py --pipeline cad-only
```

Opcional: `--dwg`, `--pres`, `--bc3`.

### Baseline de comparación

Por defecto **`--compare-baseline structural`**: se genera `PRES_estructural_filtrado.xlsx` (heurística en `budget/pres_structural_filter.py`: tierra, hormigón armado, acero; se excluyen acabados e instalaciones típicas). La comparación en `diferencias_*.md` usa ese archivo frente al Excel generado por Dupla — adecuado cuando el DWG es principalmente estructural.

Para comparar contra el PRES completo: `--compare-baseline full`.

### Otras flags

- `--pres-template-takeoffs`: inyecta líneas tipo PRES como takeoffs sintéticos (más cobertura; revisar cantidades).
- `--no-open-excel`: no lanzar Excel al terminar.

La carpeta `YYYY-MM-DD_HHMMSS` distingue corridas del mismo día con distintos cambios de código o de insumos.

## Dependencias del modo `full`

Hace falta **PyMuPDF** (`pip install pymupdf`) para rasterizar el PDF y **OpenAI** para la visión.
