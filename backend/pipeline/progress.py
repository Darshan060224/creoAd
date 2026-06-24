import json
import time
from redis import Redis

try:
    from ..config import settings
except ImportError:
    from config import settings

redis_conn = Redis.from_url(settings.redis_url, decode_responses=True)

def pub_log(job_id: str, stage: str, message: str, pct: int = 50):
    payload = {
        "job_id": job_id,
        "stage": stage,
        "status": "running",
        "pct": pct,
        "log": message,
        "event": "log",
        "data": {}
    }
    try:
        msg = json.dumps(payload)
        redis_conn.publish(f"job:{job_id}", msg)
        redis_conn.rpush(f"job_logs:{job_id}", msg)
        redis_conn.expire(f"job_logs:{job_id}", 3600)
    except Exception:
        pass

def pub_start(job_id: str, stage: str, message: str):
    pub_log(job_id, stage, message, 5)

def pub_done(job_id: str, stage: str, elapsed: float):
    payload = {
        "job_id": job_id,
        "stage": stage,
        "status": "done",
        "pct": 100,
        "log": f"Done in {elapsed:.1f}s",
        "event": "log",
        "data": {}
    }
    try:
        msg = json.dumps(payload)
        redis_conn.publish(f"job:{job_id}", msg)
        redis_conn.rpush(f"job_logs:{job_id}", msg)
        redis_conn.expire(f"job_logs:{job_id}", 3600)
    except Exception:
        pass

def pub_error(job_id: str, stage: str, message: str):
    payload = {
        "job_id": job_id,
        "stage": stage,
        "status": "error",
        "pct": 0,
        "log": f"Error: {message}",
        "event": "error",
        "data": {}
    }
    try:
        msg = json.dumps(payload)
        redis_conn.publish(f"job:{job_id}", msg)
        redis_conn.rpush(f"job_logs:{job_id}", msg)
        redis_conn.expire(f"job_logs:{job_id}", 3600)
    except Exception:
        pass
