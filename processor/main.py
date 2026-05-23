from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form
from fastapi.responses import JSONResponse, FileResponse
from redis import Redis
from rq import Queue
from rq.job import Job
from typing import List, Optional
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="Dupla Processor Service")
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_conn = Redis.from_url(redis_url)
q = Queue("dupla_processing", connection=redis_conn)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/jobs/process")
async def process_project(
    files: List[UploadFile] = File(...),
    discipline: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
    x_correlation_id: Optional[str] = Header(None),
):
    """
    Accept one or more uploaded files (DWG / PDF).
    All .dwg files found are extracted via APS and merged into a single
    unified cad_facts; the first .pdf file found is used for vision analysis.

    Optional ``discipline`` form field (arquitectura | estructura | electrico |
    sanitario) overrides discipline detection; when omitted it is inferred
    from the uploaded file names.
    """
    try:
        correlation_id = x_correlation_id or "unknown"
        logger.info(f"Received job processing request with correlation ID: {correlation_id}")
        dwg_files: List[tuple[str, bytes]] = []
        pdf_files: List[tuple[str, bytes]] = []

        for uf in files:
            name_lower = (uf.filename or "").lower()
            content = await uf.read()
            if name_lower.endswith(".dwg"):
                dwg_files.append((uf.filename or "upload.dwg", content))
            elif name_lower.endswith(".pdf"):
                pdf_files.append((uf.filename or "upload.pdf", content))

        if not dwg_files:
            raise HTTPException(status_code=422, detail="No .dwg file found in uploaded files")

        from tasks import run_dupla_pipeline
        job = q.enqueue(
            run_dupla_pipeline,
            dwg_files,
            pdf_files=pdf_files,
            discipline_id=discipline,
            project_name=project_name,
            correlation_id=correlation_id,
            job_timeout=3600,
        )
        return {"job_id": job.id, "status": "queued"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}")
def get_job_status(job_id: str, x_correlation_id: Optional[str] = Header(None)):
    correlation_id = x_correlation_id or "unknown"
    logger.info(f"Received job status request for {job_id} with correlation ID: {correlation_id}")
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.is_finished:
        return {"job_id": job_id, "status": "completed", "result": job.result}
    elif job.is_failed:
        return {"job_id": job_id, "status": "failed", "error": str(job.exc_info)}
    else:
        return {"job_id": job_id, "status": job.get_status()}


@app.get("/jobs/{job_id}/download")
def download_job_artifacts(job_id: str):
    """Stream the zipped deliverables (Excel, BC3, reports) for a finished job.

    Reads the archive path from the job result. The output directory is a
    shared volume (dupla_outputs) so this API container can serve files the
    worker container produced.
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.is_finished:
        raise HTTPException(status_code=409, detail="Job not finished")

    result = job.result if isinstance(job.result, dict) else {}
    output = result.get("output") or {}
    archive = output.get("archive")
    if not archive or not os.path.exists(archive):
        raise HTTPException(status_code=404, detail="No artifact archive available for this job")

    return FileResponse(
        archive,
        media_type="application/zip",
        filename=os.path.basename(archive),
    )
