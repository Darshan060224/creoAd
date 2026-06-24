#!/usr/bin/env python3
import time
from backend.jobs import redis_conn
from backend.db import SessionLocal
from backend.models import JobLog

def print_job_progress(job_id):
    data = redis_conn.hgetall(f"job:{job_id}")
    print(job_id, data)
    db = SessionLocal()
    try:
        logs = db.query(JobLog).filter(JobLog.job_id == job_id).order_by(JobLog.created_at.asc()).all()
        for l in logs:
            print(f"[{l.created_at}] {l.stage} {l.status} - {l.message}")
    finally:
        db.close()

if __name__ == '__main__':
    # Monitor the long-running job and the queued job
    job_ids = ["a0840a0d-1acc-42a6-acec-0252cfe5f52e", "c6373927-5e01-4944-a0a0-a75a7bf01786"]
    while True:
        for j in job_ids:
            print_job_progress(j)
        print('---')
        time.sleep(10)
