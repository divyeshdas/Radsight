from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_client: Optional[AsyncIOMotorClient] = None


async def connect_db() -> None:
    global _client
    _client = AsyncIOMotorClient(
        settings.mongodb_uri,
        maxPoolSize=settings.mongodb_max_pool_size,
        minPoolSize=settings.mongodb_min_pool_size,
        serverSelectionTimeoutMS=5000,
    )
    await _client.admin.command("ping")
    logger.info("MongoDB connected", db=settings.mongodb_db_name)


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _client[settings.mongodb_db_name]


def get_collection(name: str):
    return get_database()[name]
