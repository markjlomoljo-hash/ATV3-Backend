"""
Onboarding profile - preserves every field the recovered v2 bundle's 8-step
onboarding flow collected (see handoff doc section 8), so the migration
service has a 1:1 target and no answer a user already gave is lost on
upgrade.
"""
import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class OnboardingProfile(Base, RecordMixin):
    __tablename__ = "onboarding_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # --- Personal profile ---
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(32), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    life_status: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # --- Skin profile ---
    skin_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    acne_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    acne_severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    skin_goals: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    family_acne_history: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # --- Lifestyle ---
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    bedtime: Mapped[str | None] = mapped_column(String(16), nullable=True)
    stress_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exercise_frequency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    diet_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    shower_frequency: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # --- Skincare routine ---
    current_products: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    sunscreen_habit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    exfoliation_frequency: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # --- Health context ---
    health_conditions: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    maintenance_medications: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    track_cycle: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Baseline scan (live-camera onboarding scan, distinct from daily
    # FaceAtlas multi-photo flow) ---
    baseline_scan_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    baseline_scan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("face_scans.id", ondelete="SET NULL"), nullable=True)

    # --- Flow metadata ---
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
