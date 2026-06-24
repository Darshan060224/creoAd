import time
import uuid
from backend.jobs import generate_ad
from backend.db import SessionLocal
from backend.models import Campaign

db = SessionLocal()
camp_id = str(uuid.uuid4())
camp = Campaign(
    id=camp_id,
    business_url="https://claude.ai/",
    user_id="test",
    status="queued"
)
db.add(camp)
db.commit()

start = time.time()
generate_ad(campaign_id=camp_id, url="https://claude.ai/", job_id="test_parallel_job")
print(f"Total time: {time.time() - start}")
