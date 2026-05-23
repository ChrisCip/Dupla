from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth2 password login",
    description=(
        "Exchange username (email) and password for a JWT. "
        "Use the returned `access_token` with Authorization: Bearer <token>. "
        "In Swagger UI, click **Authorize** and paste the token, or use the form here."
    ),
    responses={
        401: {"description": "Invalid credentials"},
    },
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    **username**: user email address.

    **password**: user password.

    Returns a JWT **access_token** valid for the configured expiry time.
    """
    auth = AuthService(session)
    token = await auth.authenticate(form_data.username, form_data.password)
    return TokenResponse(access_token=token, token_type="bearer")
