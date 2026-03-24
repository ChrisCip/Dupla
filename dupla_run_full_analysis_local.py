
"""
Dupla local full-run wrapper.

Edit the CONFIG section and run:
    python dupla_run_full_analysis_local.py

Recommended location:
- Save this file in the ROOT of your Dupla repo

What it does:
1. Upload DWG to Autodesk APS
2. Extract raw Autodesk JSON
3. Normalize CAD facts
4. Use PDF or image pages for vision
5. Build hybrid inventory
6. Quantify + rules + BC3 candidates
7. Compose budget
8. Export workbook-ready Excel

Notes:
- Requires the Dupla repo dependencies installed
- Requires .env with Autodesk + OpenAI keys
- If USE_PDF = True, it requires PyMuPDF for PDF rendering
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# ========= CONFIG: EDIT THIS SECTION =========
PROJECT_NAME = "Proyecto Demo"
PROJECT_ID = "demo_001"

# Input files
DWG_PATH = r"C:\Users\chris\Downloads\archivos dupla\dwg\TGIU\8- ACAD-PLANOS GIUALCA I - RV7 - EXP.039-025.dwg SOLO IMPRESION.dwg"
PDF_PATH = r"C:\Users\chris\Downloads\archivos dupla\dwg\TGIU\Binder1.pdf"   # Used only if USE_PDF = True
IMAGES_DIR = r"./inputs/rendered_pages"   # Used only if USE_PDF = False
BC3_PATH = r"./data/TGIU.bc3"             # Optional: can be blank ""

# Visual stage selection
USE_PDF = True  # True = render PDF pages; False = use IMAGES_DIR directly

# Autodesk Model Derivative behavior
TRANSLATION_VIEWS = ("2d",)  # Add "3d" only when a workflow explicitly needs it
TRANSLATION_TIMEOUT_SECONDS = 3600
POLL_INTERVAL_SECONDS = 10
MAX_PROPERTY_WAIT_SECONDS = 3600
FAILED_MANIFEST_GRACE_POLLS = 3
FAILED_MANIFEST_GRACE_SLEEP_SECONDS = 20

# Autodesk OSS upload naming
UPLOAD_OBJECT_NAME = None  # Set a string to override the uploaded Autodesk object name
AUTO_UNIQUE_OBJECT_NAME = True

# Outputs
OUTPUTS_DIR = r"C:\Users\chris\Downloads\archivos dupla\dwg"
OUTPUT_NAME = "dupla_budget_ready_full"

# Optional Autodesk bucket override (or leave None to use APS_BUCKET_NAME from .env)
BUCKET_NAME = None
# ============================================

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aps_integration.aps_auth import get_aps_token
from aps_integration.model_derivative import extract_dwg_data
from aps_integration.oss_manager import APS_BUCKET_NAME, create_bucket, upload_file_to_bucket
from agents.vision_agent import run_full_vision_analysis
from budget.export_excel import export_budget_workbook
from core.pipeline import build_budget_from_sources
from core.schemas import ProjectContext
from processors.bc3_parser import parse_bc3
from processors.json_processor import process_autodesk_json


def render_pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list[Path]:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "USE_PDF=True but PyMuPDF is not installed.\n"
            "Install it with:\n"
            "    pip install pymupdf"
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    image_paths: list[Path] = []

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image_path = output_dir / f"{pdf_path.stem}_page_{page_index + 1:03d}.png"
        pix.save(str(image_path))
        image_paths.append(image_path)

    return image_paths


def ensure_normalized_cad_facts(
    dwg_path: Path,
    outputs_dir: Path,
    bucket_name: str,
    *,
    translation_views: tuple[str, ...] = TRANSLATION_VIEWS,
    translation_timeout_seconds: int = TRANSLATION_TIMEOUT_SECONDS,
    poll_interval_seconds: int = POLL_INTERVAL_SECONDS,
    max_property_wait_seconds: int = MAX_PROPERTY_WAIT_SECONDS,
    failed_manifest_grace_polls: int = FAILED_MANIFEST_GRACE_POLLS,
    failed_manifest_grace_sleep_seconds: int = FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
    upload_object_name: str | None = UPLOAD_OBJECT_NAME,
    auto_unique_object_name: bool = AUTO_UNIQUE_OBJECT_NAME,
):
    token = get_aps_token()
    create_bucket(token, bucket_name)
    unique_suffix = None
    if auto_unique_object_name:
        unique_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(
            f"[APS] AUTO_UNIQUE_OBJECT_NAME enabled. Uploading with timestamp suffix: "
            f"{unique_suffix}"
        )

    object_name = upload_file_to_bucket(
        token,
        bucket_name,
        str(dwg_path),
        object_name=upload_object_name,
        unique_suffix=unique_suffix,
    )
    if not object_name:
        raise RuntimeError("DWG upload to Autodesk failed.")

    raw_data = extract_dwg_data(
        token,
        bucket_name,
        object_name,
        views=translation_views,
        translation_timeout_seconds=translation_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        max_property_wait_seconds=max_property_wait_seconds,
        failed_manifest_grace_polls=failed_manifest_grace_polls,
        failed_manifest_grace_sleep_seconds=failed_manifest_grace_sleep_seconds,
    )
    raw_json_path = outputs_dir / f"{dwg_path.stem}.autodesk_raw.json"
    raw_json_path.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")

    normalized = process_autodesk_json(str(raw_json_path))
    normalized_json_path = outputs_dir / f"{dwg_path.stem}.normalized.json"
    normalized_json_path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")

    return normalized, raw_json_path, normalized_json_path, object_name


def resolve_pages_dir(outputs_dir: Path) -> Path:
    if USE_PDF:
        pdf_path = (REPO_ROOT / PDF_PATH).resolve()
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        rendered_dir = outputs_dir / "rendered_pages" / pdf_path.stem
        render_pdf_to_images(pdf_path, rendered_dir)
        return rendered_dir

    images_dir = (REPO_ROOT / IMAGES_DIR).resolve()
    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    return images_dir


def main() -> None:
    outputs_dir = (REPO_ROOT / OUTPUTS_DIR).resolve()
    outputs_dir.mkdir(parents=True, exist_ok=True)

    dwg_path = (REPO_ROOT / DWG_PATH).resolve()
    if not dwg_path.exists():
        raise FileNotFoundError(f"DWG file not found: {dwg_path}")

    bucket_name = BUCKET_NAME or APS_BUCKET_NAME

    print("\n=== 1) APS / Autodesk extraction ===")
    cad_facts, raw_json_path, normalized_json_path, uploaded_object_name = ensure_normalized_cad_facts(
        dwg_path=dwg_path,
        outputs_dir=outputs_dir,
        bucket_name=bucket_name,
        translation_views=TRANSLATION_VIEWS,
        translation_timeout_seconds=TRANSLATION_TIMEOUT_SECONDS,
        poll_interval_seconds=POLL_INTERVAL_SECONDS,
        max_property_wait_seconds=MAX_PROPERTY_WAIT_SECONDS,
        failed_manifest_grace_polls=FAILED_MANIFEST_GRACE_POLLS,
        failed_manifest_grace_sleep_seconds=FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
        upload_object_name=UPLOAD_OBJECT_NAME,
        auto_unique_object_name=AUTO_UNIQUE_OBJECT_NAME,
    )

    print("\n=== 2) Resolve vision pages ===")
    pages_dir = resolve_pages_dir(outputs_dir)

    print("\n=== 3) Vision analysis ===")
    vision_results = run_full_vision_analysis(str(pages_dir), cad_facts)
    vision_json_path = outputs_dir / "vision_inventory_results.json"
    vision_json_path.write_text(json.dumps(vision_results, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== 4) Optional BC3 ===")
    bc3_catalog = {}
    bc3_path_value = None
    if BC3_PATH:
        bc3_path = (REPO_ROOT / BC3_PATH).resolve()
        if not bc3_path.exists():
            raise FileNotFoundError(f"BC3 file not found: {bc3_path}")
        bc3_catalog = parse_bc3(str(bc3_path))
        bc3_path_value = str(bc3_path)

    print("\n=== 5) Build technical budget output ===")
    page_paths = sorted(
        str(path)
        for path in pages_dir.iterdir()
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )

    context = ProjectContext(
        project_id=PROJECT_ID,
        project_name=PROJECT_NAME,
        source_json_path=str(raw_json_path),
        plan_image_paths=page_paths,
        bc3_path=bc3_path_value,
        metadata={
            "dwg_path": str(dwg_path),
            "raw_autodesk_json": str(raw_json_path),
            "normalized_json": str(normalized_json_path),
            "vision_pages_dir": str(pages_dir),
            "uploaded_object_name": uploaded_object_name,
            "upload_object_name_override": UPLOAD_OBJECT_NAME,
            "auto_unique_object_name": AUTO_UNIQUE_OBJECT_NAME,
            "translation_views": list(TRANSLATION_VIEWS),
            "translation_timeout_seconds": TRANSLATION_TIMEOUT_SECONDS,
            "poll_interval_seconds": POLL_INTERVAL_SECONDS,
            "max_property_wait_seconds": MAX_PROPERTY_WAIT_SECONDS,
            "failed_manifest_grace_polls": FAILED_MANIFEST_GRACE_POLLS,
            "failed_manifest_grace_sleep_seconds": FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
        },
    )

    budget = build_budget_from_sources(
        context=context,
        cad_facts=cad_facts,
        vision_payloads=vision_results,
        bc3_catalog=bc3_catalog,
    )

    budget_json_path = outputs_dir / "dupla_full_budget_output.json"
    budget_json_path.write_text(json.dumps(budget, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== 6) Export Excel ===")
    workbook_path = outputs_dir / f"{OUTPUT_NAME}.xlsx"
    export_budget_workbook(
        context=context,
        rows=budget["rows"],
        output_path=workbook_path,
    )

    summary = {
        "dwg": str(dwg_path),
        "raw_autodesk_json": str(raw_json_path),
        "normalized_json": str(normalized_json_path),
        "vision_inventory_json": str(vision_json_path),
        "budget_json": str(budget_json_path),
        "budget_excel": str(workbook_path),
        "pages_dir": str(pages_dir),
        "vision_pages_count": len(page_paths),
        "uploaded_object_name": uploaded_object_name,
        "upload_object_name_override": UPLOAD_OBJECT_NAME,
        "auto_unique_object_name": AUTO_UNIQUE_OBJECT_NAME,
        "translation_views": list(TRANSLATION_VIEWS),
        "translation_timeout_seconds": TRANSLATION_TIMEOUT_SECONDS,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "max_property_wait_seconds": MAX_PROPERTY_WAIT_SECONDS,
        "failed_manifest_grace_polls": FAILED_MANIFEST_GRACE_POLLS,
        "failed_manifest_grace_sleep_seconds": FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
        "hybrid_levels": len(budget.get("hybrid_inventory", [])),
        "base_takeoffs": len(budget.get("base_takeoffs", [])),
        "expanded_takeoffs": len(budget.get("takeoffs", [])),
        "budget_rows": len(budget.get("rows", [])),
        "budget_lines": len(budget.get("lines", [])),
        "chapters": len(budget.get("chapters", [])),
    }

    summary_path = outputs_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== DONE ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
