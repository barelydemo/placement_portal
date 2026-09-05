"""Redis connection helper.

The client is created lazily so that importing this module never opens a socket;
nothing in Phase 0 should fail merely because Redis is not running yet. Actual
caching (with expiry) is layered on top of `get_redis()` in later phases.
"""

import redis

from backend.config import Config

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return the process-wide Redis client, creating it on first use."""
    global _client
    if _client is None:
        _client = redis.from_url(Config.REDIS_URL, decode_responses=True)
    return _client


def ping() -> bool:
    """Return True if Redis answers a PING, False if it is unreachable."""
    try:
        return bool(get_redis().ping())
    except redis.RedisError:
        return False


if __name__ == "__main__":  # pragma: no cover - manual connection test
    print(f"Redis URL: {Config.REDIS_URL}")
    print("Redis PING ->", "PONG (OK)" if ping() else "FAILED (is Redis running?)")
