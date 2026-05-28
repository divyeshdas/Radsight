from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.db.mongodb import get_collection
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> User:
    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError()

    collection = get_collection("users")
    from bson import ObjectId
    user_doc = await collection.find_one({"_id": ObjectId(user_id)})

    if not user_doc:
        raise UnauthorizedError("User not found")

    if user_doc.get("status") != "active":
        raise ForbiddenError("Account is not active")

    return User(**{**user_doc, "_id": str(user_doc["_id"])})


def require_roles(*roles: UserRole):
    async def _check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise ForbiddenError(f"Role '{user.role}' is not authorized for this action")
        return user
    return _check


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_roles(UserRole.admin))]
RadiologistOrAdmin = Annotated[User, Depends(require_roles(UserRole.admin, UserRole.radiologist))]
