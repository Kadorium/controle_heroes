from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class HealthResponse(BaseModel):
    status: str
    app: str
    database: str
    timestamp: datetime


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    permissions: list[str]
    last_login: datetime | None
    is_active: bool = True
    created_at: datetime | None = None
    cancelled_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6)
    role_name: str = Field(default="operador")


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role_name: str | None = None
    password: str | None = Field(default=None, min_length=6)


class RoleResponse(BaseModel):
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class UserCancelRequest(BaseModel):
    reason: str = Field(min_length=3)
    reason_code: str | None = None


class ReasonCodeResponse(BaseModel):
    id: int
    code: str
    category: str
    label: str
    requires_comment: bool

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
