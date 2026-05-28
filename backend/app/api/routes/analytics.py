from typing import Optional
from fastapi import APIRouter, Query
import httpx
from app.api.dependencies.auth import CurrentUser

router = APIRouter(prefix="/analytics", tags=["analytics"])

ANALYTICS_URL = "http://analytics:8002"


async def _proxy(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{ANALYTICS_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


@router.get("/kpis")
async def kpis(current_user: CurrentUser):
    return await _proxy("/analytics/kpis")


@router.get("/severity")
async def severity(current_user: CurrentUser, days: int = Query(30)):
    return await _proxy("/analytics/severity", {"days": days})


@router.get("/diseases")
async def diseases(current_user: CurrentUser, days: int = Query(30), limit: int = Query(10)):
    return await _proxy("/analytics/diseases", {"days": days, "limit": limit})


@router.get("/daily")
async def daily(current_user: CurrentUser, days: int = Query(90)):
    return await _proxy("/analytics/daily", {"days": days})


@router.get("/trends")
async def trends(current_user: CurrentUser, days: int = Query(90), window: int = Query(7)):
    return await _proxy("/analytics/trends", {"days": days, "window": window})


@router.get("/heatmap")
async def heatmap(current_user: CurrentUser, days: int = Query(60)):
    return await _proxy("/analytics/heatmap", {"days": days})


@router.get("/forecast")
async def forecast(
    current_user: CurrentUser,
    days_history: int = Query(90),
    periods: int = Query(30),
    disease: Optional[str] = Query(None),
):
    return await _proxy("/analytics/forecast", {"days_history": days_history, "periods": periods, "disease": disease})


@router.get("/anomalies")
async def anomalies(current_user: CurrentUser, days: int = Query(90)):
    return await _proxy("/analytics/anomalies", {"days": days})


@router.get("/processing")
async def processing(current_user: CurrentUser, hours: int = Query(24)):
    return await _proxy("/analytics/processing", {"hours": hours})


@router.get("/confidence")
async def confidence(current_user: CurrentUser, days: int = Query(30)):
    return await _proxy("/analytics/confidence", {"days": days})
