"""
Declarative Base + shared mixins.

Every user-owned table gets RecordMixin: a stable UUID id, created_at /
updated_at, and app_version / schema_version stamped at write time. This is
the "every record must carry stable id, user_id, created_at, updated_at,
app_version, schema_version, source metadata" requirement applied once
instead of re-typed into every model.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


def utcnow() -> datetime:
    return datetime.utcnow()


class Base(DeclarativeBase):
    pass


class RecordMixin:
    """id + audit/version columns shared by every durable record."""

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    app_version: Mapped[str] = mapped_column(String(32), default=lambda: settings.APP_VERSION, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=lambda: settings.SCHEMA_VERSION, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="app_v3", nullable=False)
