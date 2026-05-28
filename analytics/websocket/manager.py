import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set
from fastapi import WebSocket
import structlog

logger = structlog.get_logger(__name__)

_KPI_BROADCAST_TTL = 30.0
_PROC_BROADCAST_TTL = 15.0


class ConnectionManager:
    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        logger.info("WebSocket client connected", total=len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)
        logger.info("WebSocket client disconnected", total=len(self._connections))

    async def broadcast(self, payload: Dict) -> None:
        if not self._connections:
            return

        message = json.dumps({
            **payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        dead: Set[WebSocket] = set()
        async with self._lock:
            connections = set(self._connections)

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        if dead:
            async with self._lock:
                self._connections -= dead

    async def send_to(self, ws: WebSocket, payload: Dict) -> None:
        try:
            await ws.send_text(json.dumps({
                **payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))
        except Exception as e:
            logger.warning("Failed to send to WebSocket client", error=str(e))
            await self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


class _BroadcastState:
    """Holds in-memory cached results for the broadcast loop."""
    kpis: Optional[Dict] = None
    kpis_ts: float = 0.0
    processing: Optional[Dict] = None
    processing_ts: float = 0.0


_state = _BroadcastState()


async def _get_kpis_cached(db, redis) -> Dict:
    """Return cached KPIs if fresh, otherwise recompute and update cache."""
    from analytics.aggregation.aggregator import get_kpi_summary
    from analytics.core.response_cache import cache_or_compute

    now = time.monotonic()
    if _state.kpis is not None and (now - _state.kpis_ts) < _KPI_BROADCAST_TTL:
        return _state.kpis

    result = await cache_or_compute(redis, "analytics:kpi:summary", ttl=30, compute=get_kpi_summary(db))
    _state.kpis = result
    _state.kpis_ts = now
    return result


async def _get_processing_cached(db, redis) -> Dict:
    from analytics.aggregation.aggregator import get_processing_metrics
    from analytics.core.response_cache import cache_or_compute

    now = time.monotonic()
    if _state.processing is not None and (now - _state.processing_ts) < _PROC_BROADCAST_TTL:
        return _state.processing

    result = await cache_or_compute(redis, "analytics:processing:1", ttl=15, compute=get_processing_metrics(db, hours=1))
    _state.processing = result
    _state.processing_ts = now
    return result


async def start_broadcast_loop(
    db: Any,
    redis: Any,
    interval_seconds: int = 5,
) -> None:
    logger.info("WebSocket broadcast loop started", interval=interval_seconds)
    consecutive_errors = 0

    while True:
        await asyncio.sleep(interval_seconds)

        if manager.connection_count == 0:
            continue

        try:
            kpis = await _get_kpis_cached(db, redis)
            processing = await _get_processing_cached(db, redis)

            await manager.broadcast({
                "type": "kpi_update",
                "data": {
                    "kpis": kpis,
                    "processing": processing,
                },
            })
            consecutive_errors = 0

        except Exception as e:
            consecutive_errors += 1
            logger.error("Broadcast loop error", error=str(e), consecutive=consecutive_errors)
            if consecutive_errors > 10:
                await asyncio.sleep(30)
                consecutive_errors = 0
