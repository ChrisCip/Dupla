from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/api", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current user profile",
    description="Returns the authenticated user's public data (UUID, email, role). Requires Bearer JWT.",
)
async def read_me(current: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.from_user(current)
