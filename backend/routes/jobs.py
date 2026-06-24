"""
Job status endpoints
"""
from fastapi import APIRouter, HTTPException
from rq import Queue
from rq.job import Job
from redis import Redis
try:
    from ..config import settings
except ImportError:
    from config import settings

router = APIRouter()

# RQ expects binary-safe Redis connections for job payloads.
redis_conn = Redis.from_url(settings.redis_url, decode_responses=False)
q = Queue('ad_jobs', connection=redis_conn)


@router.get("/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Get current RQ job status (queued, started, finished, failed)
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        return {
            "job_id": job_id,
            "status": job.get_status(),
            "result": job.result if job.is_finished else None,
            "exc_info": job.exc_info if job.is_failed else None
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job not found: {str(e)}")


@router.get("/")
async def list_jobs(queue: str = "ad_jobs", limit: int = 20):
    """
    List recent jobs in a queue
    """
    q = Queue(queue, connection=redis_conn)
    jobs = q.get_job_ids()[:limit]
    
    results = []
    for job_id in jobs:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
            results.append({
                "job_id": job_id,
                "status": job.get_status(),
                "created_at": job.created_at.isoformat() if job.created_at else None
            })
        except Exception:
            pass
    
    return results
