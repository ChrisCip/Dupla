import tempfile
import os
import json
from pathlib import Path
from aps_integration.aps_auth import get_aps_token
from aps_integration.oss_manager import create_bucket, upload_file_to_bucket, APS_BUCKET_NAME
from aps_integration.model_derivative import extract_dwg_data
from agents.vision_agent import run_full_vision_analysis
from processors.json_processor import process_autodesk_json
from knowledge.bc3_embeddings import load_or_build_embeddings
from knowledge.methodology_generator import generate_methodology_context
from knowledge.training_data import extract_training_pairs
from processors.bc3_parser import parse_bc3
from core.pipeline import build_budget_from_sources
from core.schemas import ProjectContext
from disciplines import get_engine
import logging

logger = logging.getLogger(__name__)

def render_pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list[Path]:
    import fitz
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    image_paths = []
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image_path = output_dir / f"page_{page_index + 1:04d}.png"
        pix.save(str(image_path))
        image_paths.append(image_path)
    return image_paths

def run_dupla_pipeline(dwg_content: bytes, dwg_filename: str, pdf_content: bytes = None, pdf_filename: str = None) -> dict:
    """Runs the core budget processing pipeline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        outputs_dir = base_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)

        dwg_path = base_dir / (dwg_filename or "upload.dwg")
        dwg_path.write_bytes(dwg_content)

        # 1. APS Extraction
        bucket_name = os.getenv("APS_BUCKET_NAME", "dupla_processing_bucket")
        token = get_aps_token()
        create_bucket(token, bucket_name)
        object_name = upload_file_to_bucket(
            token, bucket_name, str(dwg_path), unique_suffix="api_job"
        )
        if not object_name:
            raise RuntimeError("DWG upload to Autodesk failed")

        raw_data = extract_dwg_data(
            token, bucket_name, object_name,
            views=("2d",),
            translation_timeout_seconds=3600,
            poll_interval_seconds=10,
            max_property_wait_seconds=3600,
            failed_manifest_grace_polls=3,
            failed_manifest_grace_sleep_seconds=20,
        )
        
        raw_json_path = outputs_dir / "raw.json"
        raw_json_path.write_text(json.dumps(raw_data))
        normalized = process_autodesk_json(str(raw_json_path))
        normalized_json_path = outputs_dir / "normalized.json"
        normalized_json_path.write_text(json.dumps(normalized))

        # 2. Vision Pages
        pages_dir = base_dir / "rendered_pages"
        pages_dir.mkdir(exist_ok=True)
        if pdf_content:
            pdf_path = base_dir / (pdf_filename or "upload.pdf")
            pdf_path.write_bytes(pdf_content)
            page_paths = render_pdf_to_images(pdf_path, pages_dir)
        else:
            page_paths = []

        # 3. Knowledge
        bc3_path = Path("/app/data/TGIU.bc3")
        bc3_catalog = parse_bc3(str(bc3_path)) if bc3_path.exists() else {}
        embedding_index = load_or_build_embeddings(bc3_catalog) if bc3_catalog.get("items") else None
        
        # 4. Vision Analysis
        vision_results = []
        if page_paths:
            vision_results = run_full_vision_analysis(
                str(pages_dir),
                normalized,
                office_methodology=None,
                upload_discipline_id=None
            )

        # 5. Build Budget
        context = ProjectContext(
            project_id="api_job",
            project_name="Dupla API Job",
            source_json_path=str(raw_json_path),
            plan_image_paths=[str(p) for p in page_paths],
            bc3_path=str(bc3_path) if bc3_path.exists() else None,
            metadata={}
        )

        import asyncio
        budget = asyncio.run(build_budget_from_sources(
            context=context,
            cad_facts=normalized,
            vision_payloads=vision_results,
            bc3_catalog=bc3_catalog,
            embedding_index=embedding_index,
            training_pairs=[]
        ))

        return budget
