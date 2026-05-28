"""
Redis-backed response cache for analytics endpoints.
Serialises the return value as JSON and stores it with a TTL.
On a cache miss the underlying coroutine is called and its result is stored.

Usage:
    result = await cache_or_compute(redis, "analytics:kpi:v1", ttl=30, compute=get_kpi_summary(db))
"""

import json
import time
from typing import Any, Awaitable, Callable, Optional
import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)


class _DatetimeEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return super().default(obj)


async def cache_or_compute(
    redis: aioredis.Redis,
    key: str,
    ttl: int,
    compute: Awaitable[Any],
) -> Any:
    """
    Try reading `key` from Redis. On hit return the deserialized value.
    On miss, await `compute`, store the result, then return it.
    """
    try:
        raw = await redis.get(key)
        if raw is not None:
            return json.loads(raw)
    except Exception as exc:
        logger.warning("Cache read failed", key=key, error=str(exc))

    result = await compute
    try:
        await redis.set(key, json.dumps(result, cls=_DatetimeEncoder), ex=ttl)
    except Exception as exc:
        logger.warning("Cache write failed", key=key, error=str(exc))

    return result


async def invalidate(redis: aioredis.Redis, *keys: str) -> None:
    try:
        if keys:
            await redis.delete(*keys)
    except Exception:
        pass
