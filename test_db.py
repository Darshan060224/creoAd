import uuid
from backend.models import Campaign
from backend.db import SessionLocal
from backend.jobs import generate_ad
from redis import Redis
from rq import Queue
from backend.config import settings

db = SessionLocal()
campaign_id = str(uuid.uuid4())
job_id = str(uuid.uuid4())

campaign = Campaign(
    id=campaign_id,
    user_id="test-user",
    job_id=job_id,
    business_url="http://test.com",
    status="queued"
)
db.add(campaign)
db.commit()
print("DB COMMIT OK")

redis_conn = Redis.from_url(settings.redis_url, decode_responses=True)
q = Queue('ad_jobs', connection=redis_conn)
rq_job = q.enqueue(
    generate_ad,
    campaign_id=campaign_id,
    url="http://test.com",
    voice_backend="chatterbox",
    voice_model=None,
    job_timeout=3600,
    result_ttl=86400
)
print("ENQUEUE OK:", rq_job.id)
