"""
Genera Excel (y PDF vía Excel instalado en Windows) para presentación.

Uso desde la raíz del repo:
    python scripts/export_presentacion.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from budget.export_excel import export_budget_workbook
from core.pipeline import build_budget_from_inventory
from core.schemas import ProjectContext, level_inventory_from_dict
from processors.bc3_parser import parse_bc3


def _excel_to_pdf(xlsx: Path, pdf: Path) -> None:
    xlsx_s = str(xlsx.resolve()).replace("'", "''")
    pdf_s = str(pdf.resolve()).replace("'", "''")
    script = f"""$ErrorActionPreference = 'Stop'
$xlsx = '{xlsx_s}'
$pdf = '{pdf_s}'
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
$wb = $xl.Workbooks.Open($xlsx)
$wb.ExportAsFixedFormat(0, $pdf)
$wb.Close($false)
$xl.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($wb) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($xl) | Out-Null
[GC]::Collect()
[GC]::WaitForPendingFinalizers()
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ps1", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(script)
        tmp_path = tmp.name
    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                tmp_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def main() -> int:
    inv_path = REPO_ROOT / "examples" / "sample_level_inventory.json"
    bc3_path = REPO_ROOT / "data" / "TGIU.bc3"
    out_dir = REPO_ROOT / "output" / "presentacion"
    out_dir.mkdir(parents=True, exist_ok=True)
    xlsx_path = out_dir / "presupuesto_dupla_presentacion.xlsx"
    pdf_path = out_dir / "presupuesto_dupla_presentacion.pdf"

    with open(inv_path, encoding="utf-8") as handle:
        level = level_inventory_from_dict(json.load(handle))
    bc3 = parse_bc3(str(bc3_path))
    ctx = ProjectContext(
        project_id="demo_presentacion",
        project_name="Demostracion Dupla - Presupuesto",
        source_json_path=None,
        plan_image_paths=[],
        bc3_path=str(bc3_path),
    )
    budget = build_budget_from_inventory(
        ctx, [level], bc3, embedding_index=None, training_pairs=[]
    )
    saved_xlsx = export_budget_workbook(ctx, budget["rows"], xlsx_path)
    print(f"Excel: {saved_xlsx}")
    print(f"Filas exportadas: {len(budget.get('rows', []))}")

    try:
        _excel_to_pdf(Path(saved_xlsx), pdf_path)
        print(f"PDF: {pdf_path.resolve()}")
    except subprocess.CalledProcessError as exc:
        print("No se pudo generar PDF automáticamente (revisa que Excel este instalado).", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        print(f"Exporta a PDF manualmente desde: {saved_xlsx}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
