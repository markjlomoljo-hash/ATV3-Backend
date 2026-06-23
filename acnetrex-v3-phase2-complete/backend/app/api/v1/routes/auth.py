"""Auth routes. Every response shape matches schemas/auth.py exactly - no
route hand-builds a dict that could drift from the documented contract."""
import uuid as uuid_lib

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, DbSession
from app.core import security
from app.core.errors import MigrationError, ValidationFailedError
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserOut,
)
from app.schemas.migration import LegacyMigrationRequest, LegacyMigrationResult
from app.services import auth_service, migration_service, onboarding_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, request: Request, db: DbSession) -> AuthResponse:
    user = await auth_service.signup(db, payload, ip_address=_client_ip(request))
    _, _, token, expires_at = await auth_service.login(
        db, LoginRequest(email=payload.email, password=payload.password, remember_me=False),
        ip_address=_client_ip(request), user_agent=request.headers.get("user-agent"),
    )
    return AuthResponse(user=UserOut.model_validate(user), access_token=token, expires_at=expires_at, onboarding_completed=False)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, db: DbSession) -> AuthResponse:
    user, _session, token, expires_at = await auth_service.login(
        db, payload, ip_address=_client_ip(request), user_agent=request.headers.get("user-agent"),
    )
    onboarding = await onboarding_service.get_or_create_onboarding(db, user.id)
    return AuthResponse(user=UserOut.model_validate(user), access_token=token, expires_at=expires_at, onboarding_completed=onboarding.completed)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, db: DbSession, current_user: CurrentUser) -> None:
    auth_header = request.headers.get("authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    payload = security.decode_access_token(token)
    await auth_service.logout(db, session_id=uuid_lib.UUID(payload["sid"]), user_id=current_user.id)


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(payload: ForgotPasswordRequest, db: DbSession) -> None:
    # Always 204 regardless of whether the account exists - no enumeration.
    # In production, wire token delivery to a real transactional email
    # provider here (SES/Postmark/etc.) using the token this returns;
    # nothing about the email-sending step is a backend logic concern, it's
    # an infrastructure credential the deploying team provides.
    await auth_service.forgot_password(db, payload.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(payload: ResetPasswordRequest, db: DbSession) -> None:
    await auth_service.reset_password(db, payload.token, payload.new_password)


@router.post("/migrate", response_model=LegacyMigrationResult)
async def migrate_legacy_data(payload: LegacyMigrationRequest, db: DbSession, current_user: CurrentUser) -> LegacyMigrationResult:
    """One-time import of acnetrex_credentials / acnetrex_auth_v2 /
    acnetrex_data_v2 / acnetrex_ai_v2. Requires a real v3 session (the user
    must sign up or log in first) and explicit consent - the old data is
    never trusted as auth, only as an import source."""
    if not payload.consent_to_import:
        raise ValidationFailedError("consent_to_import must be true to run a legacy data import.")
    try:
        result = await migration_service.run_full_migration(
            db, current_user.id, payload.legacy_auth_v2, payload.legacy_data_v2, payload.legacy_ai_v2,
        )
    except MigrationError:
        raise
    return LegacyMigrationResult(**result)
