"""JWT revocation list backed by Redis.

JWTs are stateless, so `/api/auth/logout` cannot "delete" a token — instead the
token's unique id (`jti`) is stored in Redis until its natural expiry, and every
protected request checks that list.

Keys expire on their own, so the blocklist never grows without bound.

Note: if Redis is unreachable, `is_revoked()` returns False (fail-open) so that
a Redis outage does not lock every user out of the portal. The trade-off is that
already-logged-out tokens would work again until they expire.
"""

import logging

import redis

from backend.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

_PREFIX = "ppa:revoked_jwt:"


def revoke(jti: str, ttl_seconds: int) -> bool:
    """Mark a token id as revoked for the remainder of its lifetime."""
    try:
        get_redis().setex(f"{_PREFIX}{jti}", max(int(ttl_seconds), 1), "revoked")
        return True
    except redis.RedisError:
        logger.warning("Redis unavailable — could not revoke token %s", jti)
        return False


def is_revoked(jti: str) -> bool:
    """Return True if this token id was revoked by a logout."""
    try:
        return get_redis().exists(f"{_PREFIX}{jti}") == 1
    except redis.RedisError:
        logger.warning("Redis unavailable — skipping revocation check for %s", jti)
        return False
