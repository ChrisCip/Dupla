from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import User, UserRole


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT bearer token")
    token_type: str = Field(default="bearer", description="Always bearer for OAuth2 password flow")


class UserResponse(BaseModel):
    uuid: UUID = Field(..., description="Public user identifier")
    email: EmailStr
    role: UserRole

    @classmethod
    def from_user(cls, user: User) -> UserResponse:
        return cls(uuid=user.id, email=user.email, role=user.role)
