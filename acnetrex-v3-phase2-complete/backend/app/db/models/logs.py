"""
Unified daily log model.

Sleep, food, stress, activity, contact, hydration, and cycle logs all share
one table keyed on (user_id, log_date, log_type) with a UNIQUE index. This is
deliberate, not a shortcut: it makes the "same-day log merge" rule a database
constraint instead of just application logic, so it holds even under
concurrent requests, retried submissions, or a future code path someone adds
without reading log_service.py. The `data` JSONB column holds the type-
specific fields (validated against per-type Pydantic schemas in
schemas/logs.py before they ever reach this table), preserving every field
the v2 app tracked per log type.
"""
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class DailyLog(Base, RecordMixin):
    __tablename__ = "daily_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    log_type: Mapped[str] = mapped_column(String(32), nullable=False)  # sleep|food|stress|activity|contact|hydration|cycle
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("user_id", "log_date", "log_type", name="ux_user_date_logtype"),
        Index("ix_daily_logs_user_type_date", "user_id", "log_type", "log_date"),
    )
