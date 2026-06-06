from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
)
from app.services.auth_service import AuthService
from app.services.password_reset_service import PasswordResetService

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


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Solicitar restablecimiento de contraseña",
    description=(
        "Envía un correo con enlace de restablecimiento si el email está registrado. "
        "La respuesta es siempre genérica para evitar enumeración de cuentas."
    ),
)
async def forgot_password(
    body: ForgotPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ForgotPasswordResponse:
    service = PasswordResetService(session)
    message = await service.request_reset(body.email)
    return ForgotPasswordResponse(message=message)


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirmar nueva contraseña",
    responses={400: {"description": "Token inválido o expirado"}},
)
async def reset_password(
    body: ResetPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ResetPasswordResponse:
    service = PasswordResetService(session)
    await service.reset_password(body.token, body.password)
    return ResetPasswordResponse(message="Contraseña actualizada. Ya puedes iniciar sesión.")
