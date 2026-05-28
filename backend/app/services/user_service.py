from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from app.db.mongodb import get_collection
from app.db.redis_client import cache_set, cache_get, cache_delete
from app.models.user import User, UserCreate, UserRole, UserStatus
from app.core.security import hash_password, verify_password
from app.core.exceptions import NotFoundError, ConflictError, UnauthorizedError


async def create_user(data: UserCreate) -> User:
    collection = get_collection("users")

    existing = await collection.find_one({"email": data.email})
    if existing:
        raise ConflictError(f"Email {data.email} is already registered")

    doc = {
        "email": data.email,
        "full_name": data.full_name,
        "role": data.role,
        "status": UserStatus.active,
        "hashed_password": hash_password(data.password),
        "department": data.department,
        "last_login": None,
        "reports_processed": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    result = await collection.insert_one(doc)
    return User(**{**doc, "_id": str(result.inserted_id)})


async def authenticate_user(email: str, password: str) -> User:
    collection = get_collection("users")
    doc = await collection.find_one({"email": email})

    if not doc or not verify_password(password, doc["hashed_password"]):
        raise UnauthorizedError("Invalid email or password")

    if doc.get("status") != UserStatus.active:
        raise UnauthorizedError("Account is suspended or inactive")

    await collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}},
    )

    return User(**{**doc, "_id": str(doc["_id"])})


async def get_user_by_id(user_id: str) -> User:
    cache_key = f"user:{user_id}"
    cached = await cache_get(cache_key)
    if cached:
        return User(**cached)

    collection = get_collection("users")
    doc = await collection.find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise NotFoundError("User", user_id)

    user = User(**{**doc, "_id": str(doc["_id"])})
    await cache_set(cache_key, user.model_dump(), ttl=300)
    return user


async def list_users(role: Optional[UserRole] = None, skip: int = 0, limit: int = 50) -> list[User]:
    collection = get_collection("users")
    query = {}
    if role:
        query["role"] = role

    cursor = collection.find(query, {"hashed_password": 0}).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [User(**{**d, "_id": str(d["_id"])}) for d in docs]


async def update_user_status(user_id: str, status: UserStatus) -> None:
    collection = get_collection("users")
    result = await collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise NotFoundError("User", user_id)
    await cache_delete(f"user:{user_id}")
