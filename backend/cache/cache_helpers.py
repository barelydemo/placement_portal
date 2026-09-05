"""Redis caching helpers for read-heavy endpoints.

Design notes:

* **Namespaced keys with a version counter.** Every key embeds the current
  version of its namespace (`ppa:cache:ver:<ns>`). Bumping that counter on a
  write instantly orphans every cached entry in the namespace, so nothing goes
  stale — without ever running KEYS/SCAN against a live Redis.
* **TTL as a backstop.** Orphaned entries expire on their own.
* **Fail open.** If Redis is unreachable the caller still gets correct data,
  just uncached. A cache outage must never take the portal down.
"""

import hashlib
import json
import logging
from typing import Any, Callable

import redis

from backend.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

PREFIX = "ppa:cache"

# Namespaces
NS_STATS = "stats"
NS_DRIVES = "drives"


def _version_key(namespace: str) -> str:
    return f"{PREFIX}:ver:{namespace}"


def namespace_version(namespace: str) -> int:
    """Current version of a cache namespace (0 when Redis is unavailable)."""
    try:
        raw = get_redis().get(_version_key(namespace))
        if raw is None:
            get_redis().set(_version_key(namespace), 1)
            return 1
        return int(raw)
    except (redis.RedisError, ValueError):
        return 0


def bump(namespace: str) -> None:
    """Invalidate every cached entry in a namespace."""
    try:
        get_redis().incr(_version_key(namespace))
    except redis.RedisError:
        logger.warning("Redis unavailable — could not invalidate namespace %s", namespace)


def make_key(namespace: str, parts: Any) -> str:
    """Build a cache key from a namespace and any JSON-serializable descriptor.

    `parts` should capture everything the response depends on — including the
    requesting user when the payload is user-specific.
    """
    raw = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"{PREFIX}:{namespace}:v{namespace_version(namespace)}:{digest}"


def get_or_set(key: str, ttl: int, producer: Callable[[], Any]) -> tuple[Any, bool]:
    """Return (value, was_cache_hit), computing and storing the value on a miss."""
    try:
        cached = get_redis().get(key)
        if cached is not None:
            return json.loads(cached), True
    except (redis.RedisError, ValueError, TypeError):
        logger.warning("Cache read failed for %s — serving uncached", key)
        return producer(), False

    value = producer()
    try:
        get_redis().setex(key, max(int(ttl), 1), json.dumps(value, default=str))
    except (redis.RedisError, TypeError):
        logger.warning("Cache write failed for %s", key)
    return value, False
