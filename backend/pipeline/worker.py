"""RQ worker entrypoint for CreoAd jobs."""

from __future__ import annotations

from rq import Connection, Worker
from redis import Redis

try:
    from ..config import settings
except ImportError:
    from config import settings


def run_worker() -> None:
    redis_conn = Redis.from_url(settings.redis_url, decode_responses=True)
    with Connection(redis_conn):
        worker = Worker(["ad_jobs"])
        worker.work(with_scheduler=True)


if __name__ == "__main__":
    run_worker()
