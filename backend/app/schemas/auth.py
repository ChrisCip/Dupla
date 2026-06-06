from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.inspection import inspect

from app.models.user import User, UserRole


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT bearer token")
    token_type: str = Field(default="bearer", description="Always bearer for OAuth2 password flow")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=512)
    password: str = Field(min_length=8, max_length=128)


class ResetPasswordResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    uuid: UUID = Field(..., description="Public user identifier")
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    module_ids: list[int] = Field(default_factory=list, description="Módulos asignados")

    @classmethod
    def from_user(cls, user: User) -> UserResponse:
        st = inspect(user)
        if "modules" in st.unloaded:
            mids: list[int] = []
        else:
            mids = [m.module_id for m in user.modules]
        return cls(
            uuid=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            module_ids=mids,
        )
