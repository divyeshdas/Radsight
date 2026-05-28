import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Set
from fastapi import WebSocket
import structlog

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections and broadcasts analytics updates.
    Clients connect once and receive real-time metric pushes without polling.
    """

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

        dead = set()
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


async def start_broadcast_loop(
    db,
    interval_seconds: int = 5,
) -> None:
    from analytics.aggregation.aggregator import get_kpi_summary, get_processing_metrics
    from analytics.anomaly.isolation_forest import detect_anomalies

    logger.info("WebSocket broadcast loop started", interval=interval_seconds)
    consecutive_errors = 0

    while True:
        await asyncio.sleep(interval_seconds)

        if manager.connection_count == 0:
            continue

        try:
            kpis = await get_kpi_summary(db)
            processing = await get_processing_metrics(db, hours=1)

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
