from fastapi import APIRouter, Response
from pydantic import BaseModel, EmailStr
from app.models.user import UserCreate, UserResponse, UserRole
from app.services.user_service import create_user, authenticate_user
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.core.exceptions import UnauthorizedError
from app.api.dependencies.auth import CurrentUser
from app.db.redis_client import cache_set, cache_delete

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserCreate):
    user = await create_user(data)
    return UserResponse(**user.model_dump())


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    user = await authenticate_user(data.email, data.password)
    access = create_access_token(subject=str(user.id), role=user.role)
    refresh = create_refresh_token(subject=str(user.id))
    await cache_set(f"refresh:{user.id}", refresh, ttl=60 * 60 * 24 * 7)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest):
    payload = decode_token(data.refresh_token)

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    user_id = payload.get("sub")
    from app.services.user_service import get_user_by_id
    user = await get_user_by_id(user_id)

    access = create_access_token(subject=user_id, role=user.role)
    new_refresh = create_refresh_token(subject=user_id)
    await cache_set(f"refresh:{user_id}", new_refresh, ttl=60 * 60 * 24 * 7)

    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=204)
async def logout(current_user: CurrentUser):
    await cache_delete(f"refresh:{current_user.id}")


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser):
    return UserResponse(**current_user.model_dump())
