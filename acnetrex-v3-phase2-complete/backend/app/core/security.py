"""
Password hashing and session token issuance.

Passwords are hashed with Argon2id (memory-hard, current OWASP recommendation),
never with the legacy SHA-256 + static-salt scheme the v2 client app used.
Session tokens are short-lived JWTs; "remember me" extends the lifetime
instead of inventing a separate auth mechanism, and every token carries a
`sid` (session id) that maps to a row in `auth_sessions` so logout actually
revokes the session server-side instead of just deleting a client token.
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from app.core.config import settings

_ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True if a stored hash was created with weaker params than current policy."""
    return _ph.check_needs_rehash(hashed)


def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID, remember_me: bool = False) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    duration = timedelta(days=settings.REMEMBER_ME_EXPIRE_DAYS) if remember_me else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = now + duration
    token = jwt.encode(
        {
            "sub": str(user_id),
            "sid": str(session_id),
            "iat": now,
            "exp": expires_at,
            "typ": "access",
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return token, expires_at


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError subclasses on invalid/expired tokens. Caller handles."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def create_password_reset_token(user_id: uuid.UUID) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": expires_at, "typ": "reset"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return token, expires_at


def decode_password_reset_token(token: str) -> uuid.UUID:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("typ") != "reset":
        raise jwt.InvalidTokenError("Not a reset token")
    return uuid.UUID(payload["sub"])


def generate_opaque_token(nbytes: int = 32) -> str:
    """For things like email-verification links that shouldn't be JWTs."""
    return secrets.token_urlsafe(nbytes)
