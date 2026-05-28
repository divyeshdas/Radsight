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
from app.api.routes import auth, reports, users

settings = get_settings()
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(debug=settings.debug)
    logger.info("RadSight starting", env=settings.app_env, version=settings.app_version)
    await connect_db()
    await connect_redis()
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


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "healthy", "version": settings.app_version, "env": settings.app_env}


@app.get("/", tags=["system"])
async def root():
    return {"service": "RadSight API", "version": settings.app_version}
