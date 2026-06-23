"""Onboarding schemas. PATCH accepts partial updates (every field optional)
since the multi-step flow saves progress after each step rather than all at
once."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OnboardingPatchRequest(BaseModel):
    age: int | None = Field(default=None, ge=10, le=110)
    sex: str | None = None
    height_cm: float | None = Field(default=None, gt=0, lt=300)
    weight_kg: float | None = Field(default=None, gt=0, lt=400)
    life_status: str | None = None

    skin_type: str | None = None
    acne_type: str | None = None
    acne_severity: str | None = None
    skin_goals: list[str] | None = None
    family_acne_history: bool | None = None

    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    bedtime: str | None = None
    stress_level: int | None = Field(default=None, ge=1, le=10)
    exercise_frequency: str | None = None
    diet_type: str | None = None
    shower_frequency: str | None = None

    current_products: list[str] | None = None
    sunscreen_habit: str | None = None
    exfoliation_frequency: str | None = None

    health_conditions: list[str] | None = None
    maintenance_medications: list[str] | None = None
    track_cycle: bool | None = None

    current_step: int | None = Field(default=None, ge=0, le=8)


class OnboardingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    age: int | None
    sex: str | None
    height_cm: float | None
    weight_kg: float | None
    life_status: str | None
    skin_type: str | None
    acne_type: str | None
    acne_severity: str | None
    skin_goals: list[str]
    family_acne_history: bool | None
    sleep_hours: float | None
    bedtime: str | None
    stress_level: int | None
    exercise_frequency: str | None
    diet_type: str | None
    shower_frequency: str | None
    current_products: list[str]
    sunscreen_habit: str | None
    exfoliation_frequency: str | None
    health_conditions: list[str]
    maintenance_medications: list[str]
    track_cycle: bool
    baseline_scan_completed: bool
    baseline_scan_id: uuid.UUID | None
    completed: bool
    current_step: int
    completed_at: datetime | None
