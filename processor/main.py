from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from redis import Redis
from rq import Queue
from rq.job import Job
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="Dupla Processor Service")
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_conn = Redis.from_url(redis_url)
q = Queue("dupla_processing", connection=redis_conn)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/jobs/process")
async def process_project(
    dwg_file: UploadFile = File(...),
    pdf_file: Optional[UploadFile] = File(None)
):
    try:
        dwg_content = await dwg_file.read()
        pdf_content = await pdf_file.read() if pdf_file else None
        
        from tasks import run_dupla_pipeline
        job = q.enqueue(
            run_dupla_pipeline,
            dwg_content=dwg_content,
            dwg_filename=dwg_file.filename,
            pdf_content=pdf_content,
            pdf_filename=pdf_file.filename if pdf_file else None,
            job_timeout=3600 # 1 hour timeout for APS processing
        )
        return {"job_id": job.id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
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
