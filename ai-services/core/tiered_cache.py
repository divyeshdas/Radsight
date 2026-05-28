import time
from typing import Any, Optional
import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)


class _L1Entry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.expires_at = time.monotonic() + ttl


class TieredCache:
    """
    Two-level cache: in-process dict (L1) backed by Redis (L2).
    L1 avoids the Redis RTT (~1-2ms) for frequently accessed keys.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        l1_maxsize: int = 512,
        l1_ttl: float = 300.0,
    ):
        self._redis = redis_client
        self._l1: dict[str, _L1Entry] = {}
        self._l1_maxsize = l1_maxsize
        self._l1_ttl = l1_ttl

    def _l1_get(self, key: str) -> Optional[Any]:
        entry = self._l1.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._l1[key]
            return None
        return entry.value

    def _l1_set(self, key: str, value: Any) -> None:
        if len(self._l1) >= self._l1_maxsize:
            oldest = min(self._l1, key=lambda k: self._l1[k].expires_at)
            del self._l1[oldest]
        self._l1[key] = _L1Entry(value, self._l1_ttl)

    async def get(self, key: str) -> Optional[bytes]:
        val = self._l1_get(key)
        if val is not None:
            return val

        try:
            data = await self._redis.get(key)
            if data is not None:
                self._l1_set(key, data)
            return data
        except Exception as exc:
            logger.warning("TieredCache L2 get failed", key=key, error=str(exc))
            return None

    async def set(self, key: str, value: bytes, ttl: int) -> None:
        self._l1_set(key, value)
        try:
            await self._redis.set(key, value, ex=ttl)
        except Exception as exc:
            logger.warning("TieredCache L2 set failed", key=key, error=str(exc))

    async def delete(self, key: str) -> None:
        self._l1.pop(key, None)
        try:
            await self._redis.delete(key)
        except Exception:
            pass


_instance: Optional[TieredCache] = None


def get_tiered_cache(redis_client: aioredis.Redis) -> TieredCache:
    global _instance
    if _instance is None:
        from core.config import get_ai_settings
        cfg = get_ai_settings()
        _instance = TieredCache(
            redis_client,
            l1_maxsize=cfg.l1_cache_maxsize,
            l1_ttl=float(cfg.l1_cache_ttl),
        )
    return _instance
