import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
import motor.motor_asyncio
from pydantic_settings import BaseSettings, SettingsConfigDict

from analytics.forecasting.prophet_forecaster import forecast_disease_trend, forecast_severity_distribution
from analytics.anomaly.isolation_forest import detect_anomalies, detect_disease_surge
from analytics.trends.trend_engine import compute_daily_trends, compute_disease_prevalence_trends, compute_rolling_risk_heatmap
from analytics.aggregation.aggregator import (
    get_kpi_summary,
    get_severity_distribution,
    get_disease_prevalence,
    get_daily_report_counts,
    get_processing_metrics,
    get_confidence_distribution,
)
from analytics.websocket.manager import manager, start_broadcast_loop
import structlog

logger = structlog.get_logger(__name__)


class AnalyticsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "radsight"
    ws_broadcast_interval: int = 5


settings = AnalyticsSettings()
_db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None


def get_db():
    global _db
    if _db is None:
        client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
        )
        _db = client[settings.mongodb_db_name]
    return _db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_db()
    loop = asyncio.get_event_loop()
    broadcast_task = loop.create_task(
        start_broadcast_loop(db, interval_seconds=settings.ws_broadcast_interval)
    )
    logger.info("Analytics service started")
    yield
    broadcast_task.cancel()
    logger.info("Analytics service stopped")


app = FastAPI(title="RadSight Analytics", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "analytics", "ws_connections": manager.connection_count}


@app.get("/analytics/kpis")
async def kpis():
    return await get_kpi_summary(get_db())


@app.get("/analytics/severity")
async def severity_distribution(days: int = Query(30, ge=1, le=365)):
    return await get_severity_distribution(get_db(), days=days)


@app.get("/analytics/diseases")
async def disease_prevalence(days: int = Query(30, ge=1, le=365), limit: int = Query(10, ge=1, le=20)):
    return await get_disease_prevalence(get_db(), days=days, limit=limit)


@app.get("/analytics/daily")
async def daily_counts(days: int = Query(90, ge=7, le=365)):
    return await get_daily_report_counts(get_db(), days=days)


@app.get("/analytics/processing")
async def processing_metrics(hours: int = Query(24, ge=1, le=168)):
    return await get_processing_metrics(get_db(), hours=hours)


@app.get("/analytics/confidence")
async def confidence_distribution(days: int = Query(30, ge=1, le=365)):
    return await get_confidence_distribution(get_db(), days=days)


@app.get("/analytics/trends")
async def trends(days: int = Query(90, ge=7, le=365), window: int = Query(7, ge=3, le=30)):
    daily = await get_daily_report_counts(get_db(), days=days)
    return compute_daily_trends(daily, window=window)


@app.get("/analytics/heatmap")
async def risk_heatmap(days: int = Query(60, ge=7, le=365)):
    daily = await get_daily_report_counts(get_db(), days=days)
    return compute_rolling_risk_heatmap(daily)


@app.get("/analytics/forecast")
async def forecast(
    days_history: int = Query(90, ge=14, le=365),
    periods: int = Query(30, ge=7, le=90),
    disease: Optional[str] = Query(None),
):
    daily = await get_daily_report_counts(get_db(), days=days_history)
    series = [{"date": d["date"], "count": d["total_reports"]} for d in daily]
    return forecast_disease_trend(series, periods=periods, disease=disease)


@app.get("/analytics/forecast/severity")
async def forecast_severity(
    days_history: int = Query(90, ge=14, le=365),
    periods: int = Query(14, ge=7, le=60),
):
    daily = await get_daily_report_counts(get_db(), days=days_history)
    series = [
        {
            "date": d["date"],
            "critical": d.get("critical_count", 0),
            "high": d.get("severity_distribution", {}).get("high", d.get("severity_distribution", {}).get("severe", 0)),
            "total": max(d["total_reports"], 1),
        }
        for d in daily
    ]
    return forecast_severity_distribution(series, periods=periods)


@app.get("/analytics/anomalies")
async def anomalies(days: int = Query(90, ge=14, le=365), contamination: float = Query(0.05, ge=0.01, le=0.2)):
    daily = await get_daily_report_counts(get_db(), days=days)
    return detect_anomalies(daily, contamination=contamination)


@app.get("/analytics/surge/{disease}")
async def disease_surge(
    disease: str,
    days: int = Query(90, ge=14, le=365),
    window: int = Query(7, ge=3, le=14),
    threshold: float = Query(2.5, ge=1.5, le=5.0),
):
    daily = await get_daily_report_counts(get_db(), days=days)
    series = [
        {"date": d["date"], "count": d.get("disease_counts", {}).get(disease, 0)}
        for d in daily
    ]
    return detect_disease_surge(series, disease=disease, window=window, threshold_sigma=threshold)


@app.websocket("/ws/analytics")
async def analytics_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    db = get_db()

    try:
        kpis = await get_kpi_summary(db)
        await manager.send_to(websocket, {"type": "initial_state", "data": {"kpis": kpis}})

        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await manager.send_to(websocket, {"type": "ping"})

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
