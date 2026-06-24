"""
Phase 5 - Redis Caching Layer
"""
import redis
import json
from config import settings

try:
    cache = redis.Redis.from_url(settings.redis_url, decode_responses=True)
except Exception:
    cache = None

def get_cached_response(key: str):
    if cache:
        val = cache.get(key)
        if val:
            return json.loads(val)
    return None

def set_cached_response(key: str, data: dict, ttl_seconds: int = 3600):
    if cache:
        cache.setex(key, ttl_seconds, json.dumps(data))
