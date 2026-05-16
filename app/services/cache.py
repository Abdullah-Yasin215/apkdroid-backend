import redis
from app.config import get_settings
import json
import time

settings = get_settings()

# Primary: Redis
try:
    cache_client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
    cache_client.ping()  # verify connection
except Exception as e:
    print(f"Redis connection failed: {e}. Using in-memory fallback cache.")
    cache_client = None

# Phase 3/5 fallback: in-process LRU-like dict {key: {"val": ..., "exp": timestamp}}
_mem_cache: dict = {}
_MEM_CACHE_MAX = 500  # limit to avoid unbounded growth


def cache_get(key: str):
    """Get value from Redis, falling back to in-memory cache."""
    if cache_client:
        try:
            value = cache_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            pass  # fall through to mem cache

    # In-memory fallback
    entry = _mem_cache.get(key)
    if entry and entry["exp"] > time.time():
        return entry["val"]
    _mem_cache.pop(key, None)
    return None


def cache_set(key: str, value: dict, ttl: int = 3600):
    """Set value in Redis or in-memory fallback."""
    if cache_client:
        try:
            cache_client.setex(key, ttl, json.dumps(value, default=str))
            return
        except Exception:
            pass  # fall through to mem cache

    # In-memory fallback — evict oldest if too large
    if len(_mem_cache) >= _MEM_CACHE_MAX:
        oldest = min(_mem_cache, key=lambda k: _mem_cache[k]["exp"])
        _mem_cache.pop(oldest, None)
    _mem_cache[key] = {"val": value, "exp": time.time() + ttl}


def cache_delete(key: str):
    """Delete value from Redis and in-memory fallback."""
    if cache_client:
        try:
            cache_client.delete(key)
        except Exception:
            pass
    _mem_cache.pop(key, None)
