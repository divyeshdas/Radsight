from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.mongodb import connect_db, close_db
from app.db.redis_client import connect_redis, close_redis

settings = get_settings()
logger = get_logger(__name__)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "healthy", "version": settings.app_version, "env": settings.app_env}


@app.get("/", tags=["system"])
async def root():
    return {"service": "RadSight API", "version": settings.app_version}
