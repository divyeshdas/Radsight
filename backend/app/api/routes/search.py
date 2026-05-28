from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
import httpx
from app.api.dependencies.auth import CurrentUser
from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter(prefix="/search", tags=["search"])
settings = get_settings()
logger = get_logger(__name__)

AI_SERVICES_URL = "http://ai_services:8001"


class SearchRequest(BaseModel):
    query: str
    k: int = 10
    severity_filter: Optional[str] = None
    min_score: float = 0.30


class SearchResult(BaseModel):
    report_id: str
    patient_id: Optional[str]
    report_type: Optional[str]
    severity: Optional[str]
    risk_score: Optional[float]
    summary: Optional[str]
    findings_count: int
    has_critical_findings: bool
    created_at: Optional[str]
    institution: Optional[str]
    similarity_score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query: str
    inference_ms: float
    index_ready: bool
    index_size: Optional[int] = None
    cache_hit_rate_pct: Optional[float] = None


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(request: SearchRequest, current_user: CurrentUser):
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{AI_SERVICES_URL}/search/semantic",
            json={
                "query": request.query,
                "k": request.k,
                "severity_filter": request.severity_filter,
                "min_score": request.min_score,
            },
        )
        resp.raise_for_status()
        return resp.json()


@router.post("/index/rebuild", status_code=202)
async def trigger_index_rebuild(current_user: CurrentUser):
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(f"{AI_SERVICES_URL}/search/index/rebuild")
        return resp.json()


@router.get("/stats")
async def search_stats(current_user: CurrentUser):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{AI_SERVICES_URL}/search/stats")
        return resp.json()
