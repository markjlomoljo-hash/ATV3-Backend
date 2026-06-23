"""
Identity, sessions, consent, and audit models.

This is the real auth foundation that replaces the v2 client app's
localStorage `acnetrex_credentials` (plaintext-keyed SHA-256 hashes). Nothing
here is reachable without a server-side check: passwords are Argon2 hashes,
sessions are server-side rows a JWT merely points to (so logout/revocation is
real), and every consent grant/revoke is its own timestamped row instead of a
single mutable boolean, so consent history survives audits and schema
changes.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import AppRole
from app.db.base import Base, RecordMixin, utcnow


class User(Base, RecordMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default=AppRole.USER.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Carried forward so legacy-imported accounts remain traceable; null for
    # accounts created natively in v3.
    legacy_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    consents: Mapped[list["Consent"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthSession(Base, RecordMixin):
    """A real server-side session. The JWT's `sid` claim points here; if this
    row is revoked or expired, the token is dead even if it hasn't expired
    cryptographically yet (covers logout, password reset, and admin
    revocation)."""

    __tablename__ = "auth_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remember_me: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")

    __table_args__ = (Index("ix_auth_sessions_user_id", "user_id"),)

    @property
    def is_valid(self) -> bool:
        return self.revoked_at is None and self.expires_at > utcnow()


class Consent(Base, RecordMixin):
    """One row per consent grant/revoke event. Current state for a
    consent_type is the row with the latest created_at and revoked_at IS NULL
    -> granted; current_state helper lives in consent_service, not here."""

    __tablename__ = "consents"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), default="1", nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="consents")

    __table_args__ = (Index("ix_consents_user_type", "user_id", "consent_type"),)


class AuditLog(Base, RecordMixin):
    """Append-only event trail for security-relevant and consent-relevant
    actions (login, password reset, consent change, data export, data
    deletion, migration). Never updated, never deleted."""

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)


class MigrationRecord(Base, RecordMixin):
    """One row per legacy localStorage object successfully (or
    unsuccessfully) imported during the one-time v2 -> v3 migration flow.
    Lets /profile show "imported from your old account" and lets support
    diagnose a partial migration without guessing."""

    __tablename__ = "migration_records"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    legacy_key: Mapped[str] = mapped_column(String(64), nullable=False)   # e.g. acnetrex_data_v2
    legacy_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. sleep_log, face_scan
    new_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)        # imported | skipped | failed
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
