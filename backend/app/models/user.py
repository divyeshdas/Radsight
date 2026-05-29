from enum import Enum
from typing import Optional
from pydantic import EmailStr, Field
from app.models.base import MongoBaseModel


class UserRole(str, Enum):
    admin = "admin"
    radiologist = "radiologist"
    clinician = "clinician"


class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class User(MongoBaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    role: UserRole = UserRole.clinician
    status: UserStatus = UserStatus.active
    hashed_password: str
    department: Optional[str] = None
    last_login: Optional[str] = None
    reports_processed: int = 0


class UserCreate(MongoBaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8)
    role: UserRole = UserRole.clinician
    department: Optional[str] = None


class UserResponse(MongoBaseModel):
    email: EmailStr
    full_name: str
    role: UserRole
    status: UserStatus
    department: Optional[str] = None
    reports_processed: int = 0
