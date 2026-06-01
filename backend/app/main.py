from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.exceptions import (
    RadSightException,
    radsight_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.db.mongodb import connect_db, close_db
from app.db.redis_client import connect_redis, close_redis
from app.api.routes import auth, reports, users, search, analytics, admin

settings = get_settings()
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


async def _backfill_severity():
    import asyncio
    import time
    from app.db.mongodb import get_database
    from app.services.scan_processor import analyze_text
    await asyncio.sleep(2)  # let DB connection settle
    try:
        db = get_database()
        collection = db["reports"]
        total = await collection.count_documents({"severity": None})
        if total == 0:
            return
        logger.info("Backfilling severity for reports", count=total)
        updated = 0
        async for doc in collection.find({"severity": None}, {"_id": 1, "raw_text": 1, "patient_id": 1}):
            try:
                raw = doc.get("raw_text") or ""
                start = time.monotonic()
                result = analyze_text(raw, doc.get("patient_id", ""))
                ms = round((time.monotonic() - start) * 1000 + 50, 1)
                await collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {
                        "severity": result["severity"],
                        "risk_score": result["risk_score"],
                        "classification_confidence": result["classification_confidence"],
                        "findings_count": result["findings_count"],
                        "has_critical_findings": result["has_critical_findings"],
                        "flagged_for_review": result["flagged_for_review"],
                        "tags": result["tags"],
                        "ai_summary": result["ai_summary"],
                        "processing_time_ms": ms,
                        "status": "completed",
                    }}
                )
                updated += 1
            except Exception as e:
                logger.warning("backfill row failed", error=str(e))
        logger.info("Severity backfill complete", updated=updated)
    except Exception as e:
        logger.error("Severity backfill failed", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    configure_logging(debug=settings.debug)
    logger.info("RadSight starting", env=settings.app_env, version=settings.app_version)
    await connect_db()
    await connect_redis()
    asyncio.create_task(_backfill_severity())
    yield
    await close_db()
    await close_redis()
    logger.info("RadSight shutdown complete")


app = FastAPI(
    title="RadSight API",
    description="AI-powered radiology report analysis and healthcare intelligence platform",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.state.limiter = limiter

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(RadSightException, radsight_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check():
    from app.db.mongodb import get_database
    try:
        db = get_database()
        report_count = await db["reports"].count_documents({})
        db_status = "ok"
    except Exception as e:
        report_count = -1
        db_status = str(e)
    return {
        "status": "healthy",
        "version": settings.app_version,
        "env": settings.app_env,
        "db": db_status,
        "reports_in_db": report_count,
    }


@app.get("/", tags=["system"])
async def root():
    return {"service": "RadSight API", "version": settings.app_version}
