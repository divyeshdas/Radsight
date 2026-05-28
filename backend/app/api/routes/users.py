from typing import Optional
from fastapi import APIRouter, Query
from app.models.user import UserResponse, UserRole, UserStatus
from app.services.user_service import list_users, get_user_by_id, update_user_status
from app.api.dependencies.auth import AdminUser, CurrentUser

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
async def list_users_endpoint(
    current_user: AdminUser,
    role: Optional[UserRole] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    users = await list_users(role=role, skip=skip, limit=limit)
    return [UserResponse(**u.model_dump()) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_endpoint(user_id: str, current_user: AdminUser):
    user = await get_user_by_id(user_id)
    return UserResponse(**user.model_dump())


@router.patch("/{user_id}/status", status_code=204)
async def update_status(user_id: str, status: UserStatus, current_user: AdminUser):
    await update_user_status(user_id, status)
