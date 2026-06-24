#!/usr/bin/env python3
import time
import uuid
from datetime import datetime

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from db import SessionLocal
from models import User, Campaign
from main import q
from jobs import generate_ad
from jobs import redis_conn


def ensure_user(email: str) -> User:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return user
        user = User(id=str(uuid.uuid4()), email=email, hashed_password=str(uuid.uuid4()))
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def create_campaign(user_id: str, url: str) -> str:
    db = SessionLocal()
    try:
        campaign_id = str(uuid.uuid4())
        campaign = Campaign(id=campaign_id, user_id=user_id, business_url=url, status="queued")
        db.add(campaign)
        db.commit()
        return campaign_id
    finally:
        db.close()


def enqueue_and_monitor(campaign_id: str, url: str):
    # Enqueue job to run via existing RQ worker
    job = q.enqueue(generate_ad, campaign_id=campaign_id, url=url, job_timeout=3600)
    print(f"Enqueued job {job.id} for campaign {campaign_id}")

    # Poll redis hash for status
    job_hash = f"job:{job.id}"
    start = time.time()
    while True:
        data = redis_conn.hgetall(job_hash)
        print(datetime.utcnow().isoformat(), data)
        if data.get("status") in ("complete", "error"):
            print("Final status:", data.get("status"))
            break
        if time.time() - start > 3600:
            print("Timeout waiting for job to finish")
            break
        time.sleep(5)


if __name__ == "__main__":
    TARGET_URL = "https://www.claude.com"
    user = ensure_user("e2e@local.test")
    campaign_id = create_campaign(user.id, TARGET_URL)
    enqueue_and_monitor(campaign_id, TARGET_URL)
