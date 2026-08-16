"""API endpoints del mòdul d'autenticació (routers prims, sense lògica).

Tota la lògica viu al servei; aquí només es valida l'entrada, s'aplica
el rate limiting i es mapeja la resposta.
"""

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import (
    check_login_rate_limit,
    get_auth_service,
    get_current_user,
    get_google_verifier,
)
from app.auth.google import GoogleIdTokenVerifier
from app.auth.models import User
from app.auth.schemas import (
    ChangePasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenPair,
    UserResponse,
    VerifyEmailRequest,
)
from app.auth.service import AuthService, is_dev
from app.core.config import settings

router = APIRouter()


def _request_meta(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    return user_agent, ip_address


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
    summary="Register a new user",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    user_agent, ip_address = _request_meta(request)
    return await service.register(payload, user_agent=user_agent, ip_address=ip_address)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Login with email and password",
)
async def login(
    payload: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    await check_login_rate_limit(request, payload.email)
    user_agent, ip_address = _request_meta(request)
    return await service.login(payload, user_agent=user_agent, ip_address=ip_address)


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotate a refresh token and get a new token pair",
)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    user_agent, ip_address = _request_meta(request)
    return await service.refresh(payload, user_agent=user_agent, ip_address=ip_address)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke a refresh token (or all user sessions)",
)
async def logout(
    payload: LogoutRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.logout(payload)
    return MessageResponse(message="Logged out.")


@router.post(
    "/google",
    response_model=TokenPair,
    summary="Login/register with a Google ID token",
)
async def google_login(
    payload: GoogleLoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
    verifier: GoogleIdTokenVerifier = Depends(get_google_verifier),
) -> TokenPair:
    user_agent, ip_address = _request_meta(request)
    return await service.google_login(
        payload, verifier, user_agent=user_agent, ip_address=ip_address
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current authenticated user",
)
async def me(
    user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    return await service.get_user_response(user.id)


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify an email with a one-time token",
)
async def verify_email(
    payload: VerifyEmailRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.verify_email(payload.token)
    return MessageResponse(message="Email verified.")


@router.post(
    "/reset-password/request",
    response_model=PasswordResetRequestResponse,
    summary="Request a password reset link",
)
async def reset_password_request(
    payload: PasswordResetRequest,
    service: AuthService = Depends(get_auth_service),
) -> PasswordResetRequestResponse:
    raw_token = await service.request_password_reset(payload.email)
    dev_reset_url = None
    if raw_token is not None and not settings.email_send_enabled and is_dev():
        dev_reset_url = (
            f"{settings.frontend_url}/auth/reset-password?token={raw_token}"
        )
    return PasswordResetRequestResponse(
        message="If the email exists, a reset link will be sent.",
        dev_reset_url=dev_reset_url,
    )


@router.post(
    "/reset-password/confirm",
    response_model=MessageResponse,
    summary="Set a new password using a reset token",
)
async def reset_password_confirm(
    payload: PasswordResetConfirmRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.reset_password(payload.token, payload.new_password)
    return MessageResponse(message="Password updated.")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change the password of the current user",
)
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.change_password(user, payload.current_password, payload.new_password)
    return MessageResponse(message="Password changed.")
