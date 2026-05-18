from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.responses import JSONResponse
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
    x_correlation_id: Optional[str] = Header(None)
):
    """
    Accept one or more uploaded files (DWG / PDF).
    The first .dwg file found is used as the primary CAD input;
    the first .pdf file found is used for vision analysis.
    """
    try:
        correlation_id = x_correlation_id or "unknown"
        logger.info(f"Received job processing request with correlation ID: {correlation_id}")
        dwg_content: Optional[bytes] = None
        dwg_filename: Optional[str] = None
        pdf_content: Optional[bytes] = None
        pdf_filename: Optional[str] = None

        for uf in files:
            name_lower = (uf.filename or "").lower()
            content = await uf.read()
            if dwg_content is None and name_lower.endswith(".dwg"):
                dwg_content = content
                dwg_filename = uf.filename
            elif pdf_content is None and name_lower.endswith(".pdf"):
                pdf_content = content
                pdf_filename = uf.filename

        if not dwg_content:
            raise HTTPException(status_code=422, detail="No .dwg file found in uploaded files")

        from tasks import run_dupla_pipeline
        job = q.enqueue(
            run_dupla_pipeline,
            dwg_content=dwg_content,
            dwg_filename=dwg_filename,
            pdf_content=pdf_content,
            pdf_filename=pdf_filename,
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
