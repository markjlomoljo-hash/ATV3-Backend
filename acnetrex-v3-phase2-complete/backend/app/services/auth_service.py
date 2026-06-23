"""
Real server-side authentication service.

This is what replaces v2's `acnetrex_credentials` localStorage object
(SHA-256 + static salt, no server, no real sessions). Every function here
talks to the database: signup creates a User row with an Argon2 hash and a
mandatory privacy Consent row; login verifies against that hash and creates
a real AuthSession row; logout revokes the session server-side so a stolen
token stops working immediately instead of just being deleted client-side.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.constants import ConsentType
from app.core.errors import AccountExistsError, AuthError, InvalidCredentialsError, NotFoundError, SessionExpiredError
from app.db.models.user import AuditLog, AuthSession, Consent, User
from app.schemas.auth import LoginRequest, SignupRequest


async def signup(db: AsyncSession, payload: SignupRequest, ip_address: str | None = None) -> User:
    email = payload.email.lower().strip()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        raise AccountExistsError("An account with this email already exists.")

    user = User(
        email=email,
        password_hash=security.hash_password(payload.password),
        display_name=payload.display_name.strip(),
    )
    db.add(user)
    await db.flush()

    # Privacy consent is required to use the app at all and is granted at
    # signup as part of account creation (matches v2's consentPrivacy: true
    # default). Research/federated consent are NOT granted here - those stay
    # opt-in and are set explicitly via /network/consent.
    db.add(Consent(user_id=user.id, consent_type=ConsentType.PRIVACY.value, granted=True, granted_at=datetime.now(timezone.utc)))
    db.add(AuditLog(user_id=user.id, event_type="account_created", payload={"email": email}, ip_address=ip_address))

    await db.flush()
    return user


async def login(db: AsyncSession, payload: LoginRequest, ip_address: str | None = None, user_agent: str | None = None) -> tuple[User, AuthSession, str, datetime]:
    email = payload.email.lower().strip()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    if user is None or not user.is_active:
        # Constant-shape response regardless of whether the email exists, to
        # avoid leaking which emails are registered.
        raise InvalidCredentialsError("Incorrect email or password.")

    if not security.verify_password(payload.password, user.password_hash):
        raise InvalidCredentialsError("Incorrect email or password.")

    if security.needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(payload.password)

    user.last_login_at = datetime.now(timezone.utc)

    session = AuthSession(
        user_id=user.id,
        expires_at=datetime.now(timezone.utc),  # placeholder, set correctly below after token creation
        remember_me=payload.remember_me,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(session)
    await db.flush()  # need session.id for the JWT 'sid' claim

    token, expires_at = security.create_access_token(user.id, session.id, payload.remember_me)
    session.expires_at = expires_at

    db.add(AuditLog(user_id=user.id, event_type="login", payload={"remember_me": payload.remember_me}, ip_address=ip_address))
    await db.flush()
    return user, session, token, expires_at


async def logout(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> None:
    session = (
        await db.execute(select(AuthSession).where(AuthSession.id == session_id, AuthSession.user_id == user_id))
    ).scalar_one_or_none()
    if session is None:
        raise NotFoundError("Session not found.")
    session.revoked_at = datetime.now(timezone.utc)
    db.add(AuditLog(user_id=user_id, event_type="logout", payload={}))
    await db.flush()


async def get_user_from_token(db: AsyncSession, token: str) -> User:
    """Validates the JWT cryptographically AND checks the referenced
    AuthSession is still valid server-side. A token alone is never
    sufficient - this is what makes logout/revocation real."""
    try:
        payload = security.decode_access_token(token)
    except Exception as exc:  # jwt.ExpiredSignatureError, jwt.InvalidTokenError, etc.
        raise SessionExpiredError("Session expired or invalid. Please sign in again.") from exc

    try:
        user_id = uuid.UUID(payload["sub"])
        session_id = uuid.UUID(payload["sid"])
    except (KeyError, ValueError) as exc:
        raise AuthError("Malformed session token.") from exc

    session = (await db.execute(select(AuthSession).where(AuthSession.id == session_id))).scalar_one_or_none()
    if session is None or not session.is_valid or session.user_id != user_id:
        raise SessionExpiredError("Session expired or invalid. Please sign in again.")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise AuthError("Account not found or deactivated.")

    return user


async def forgot_password(db: AsyncSession, email: str) -> str | None:
    """Returns a reset token if the account exists, else None. The route
    layer must respond identically either way (no enumeration), and is
    responsible for actually emailing the token - this service only issues
    it and records the audit event."""
    user = (await db.execute(select(User).where(User.email == email.lower().strip()))).scalar_one_or_none()
    if user is None:
        return None
    token, _ = security.create_password_reset_token(user.id)
    db.add(AuditLog(user_id=user.id, event_type="password_reset_requested", payload={}))
    await db.flush()
    return token


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    try:
        user_id = security.decode_password_reset_token(token)
    except Exception as exc:
        raise AuthError("Reset link is invalid or expired.") from exc

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise NotFoundError("Account not found.")

    user.password_hash = security.hash_password(new_password)

    # Revoke every existing session - a password reset should not leave old
    # sessions (e.g. on a device that triggered the reset because it was
    # compromised) still valid.
    existing_sessions = (await db.execute(select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)))).scalars().all()
    now = datetime.now(timezone.utc)
    for s in existing_sessions:
        s.revoked_at = now

    db.add(AuditLog(user_id=user.id, event_type="password_reset_completed", payload={}))
    await db.flush()
