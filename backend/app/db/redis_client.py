from typing import Optional, Any
import json
import redis.asyncio as aioredis
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_redis: Optional[aioredis.Redis] = None


async def connect_redis() -> None:
    global _redis
    _redis = aioredis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        db=settings.redis_db,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    await _redis.ping()
    logger.info("Redis connected", host=settings.redis_host)


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        logger.info("Redis connection closed")


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call connect_redis() first.")
    return _redis


async def cache_set(key: str, value: Any, ttl: int = settings.redis_cache_ttl) -> None:
    r = get_redis()
    await r.set(key, json.dumps(value), ex=ttl)


async def cache_get(key: str) -> Optional[Any]:
    r = get_redis()
    data = await r.get(key)
    return json.loads(data) if data else None


async def cache_delete(key: str) -> None:
    await get_redis().delete(key)


async def cache_exists(key: str) -> bool:
    return bool(await get_redis().exists(key))
