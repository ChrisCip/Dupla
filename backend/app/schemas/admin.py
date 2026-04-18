from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    module_ids: list[int] = Field(default_factory=lambda: [1])

    @field_validator("module_ids")
    @classmethod
    def non_empty_modules(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("Al menos un módulo debe asignarse")
        return v


class AdminUpdateUserRequest(BaseModel):
    email: EmailStr
    role: UserRole
    module_ids: list[int] = Field(default_factory=lambda: [1])
    password: str | None = Field(None, min_length=8, max_length=128)

    @field_validator("module_ids")
    @classmethod
    def non_empty_modules(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("Al menos un módulo debe asignarse")
        return v
