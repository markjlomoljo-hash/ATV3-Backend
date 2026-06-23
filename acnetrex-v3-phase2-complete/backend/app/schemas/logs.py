"""
Daily log input schemas, one per log type.

These accept only the raw facts a user actually reports (bedtime, meals
eaten, activity duration, etc.). Derived risk/score fields (sleepDebt,
food overallRisk, activity breakoutRisk) are NOT accepted from the client -
they're computed server-side in log_service.py using the same formulas the
recovered v2 bundle used (extracted directly from the deployed JS, not
reinvented), so a client can't simply submit a fabricated risk number.
"""
from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.core.constants import DailyLogType


class MealItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class SleepLogIn(BaseModel):
    log_date: date | None = None
    bedtime: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    wake_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    quality: int = Field(ge=1, le=10)
    fragmented: bool = False
    late_night_shift: bool = False


class FoodLogIn(BaseModel):
    log_date: date | None = None
    meals: list[MealItemIn] = Field(default_factory=list)
    hydration_liters: float = Field(ge=0, le=15)
    glycemic_load: float = Field(ge=0, le=100)
    dairy_intake: bool = False
    whey_protein: bool = False
    sugar_load: str = Field(default="low")
    processed_food_level: str = Field(default="minimal")

    @field_validator("sugar_load")
    @classmethod
    def valid_sugar_load(cls, v: str) -> str:
        if v not in {"low", "moderate", "high"}:
            raise ValueError("sugar_load must be low|moderate|high")
        return v

    @field_validator("processed_food_level")
    @classmethod
    def valid_processed_level(cls, v: str) -> str:
        if v not in {"minimal", "moderate", "high"}:
            raise ValueError("processed_food_level must be minimal|moderate|high")
        return v


class StressLogIn(BaseModel):
    log_date: date | None = None
    stress_level: int = Field(ge=1, le=10)
    mood: str
    anxiety_level: int = Field(ge=1, le=10)
    workload: str
    major_event: str | None = None


class ActivityLogIn(BaseModel):
    log_date: date | None = None
    activity_type: str
    intensity: str
    duration_minutes: int = Field(ge=0, le=720)
    sweat_level: str
    post_workout_cleanse_delay_minutes: int = Field(ge=0, le=1440)
    friction_factors: list[str] = Field(default_factory=list)

    @field_validator("intensity")
    @classmethod
    def valid_intensity(cls, v: str) -> str:
        if v not in {"light", "moderate", "vigorous"}:
            raise ValueError("intensity must be light|moderate|vigorous")
        return v

    @field_validator("sweat_level")
    @classmethod
    def valid_sweat(cls, v: str) -> str:
        if v not in {"none", "light", "heavy"}:
            raise ValueError("sweat_level must be none|light|heavy")
        return v


class ContactLogIn(BaseModel):
    log_date: date | None = None
    pillowcase_changed: bool = False
    phone_screen_cleaned: bool = False
    mask_worn: bool = False
    helmet_worn: bool = False
    touched_face: bool = False
    hair_product_contact: bool = False
    makeup_worn: bool = False
    makeup_removed: bool = False


class HydrationLogIn(BaseModel):
    log_date: date | None = None
    water_intake_liters: float = Field(ge=0, le=15)
    target_liters: float = Field(default=2.5, ge=0.5, le=10)


class CycleLogIn(BaseModel):
    log_date: date | None = None
    cycle_day: int | None = Field(default=None, ge=1, le=60)
    phase: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    flow_level: str = Field(default="none")

    @field_validator("flow_level")
    @classmethod
    def valid_flow(cls, v: str) -> str:
        if v not in {"none", "light", "moderate", "heavy"}:
            raise ValueError("flow_level must be none|light|moderate|heavy")
        return v


LOG_TYPE_SCHEMAS: dict[str, type[BaseModel]] = {
    DailyLogType.SLEEP.value: SleepLogIn,
    DailyLogType.FOOD.value: FoodLogIn,
    DailyLogType.STRESS.value: StressLogIn,
    DailyLogType.ACTIVITY.value: ActivityLogIn,
    DailyLogType.CONTACT.value: ContactLogIn,
    DailyLogType.HYDRATION.value: HydrationLogIn,
    DailyLogType.CYCLE.value: CycleLogIn,
}


class DailyLogOut(BaseModel):
    id: str
    user_id: str
    log_date: date
    log_type: str
    data: dict
    created_at: str
    updated_at: str
    was_merged: bool   # true if this call updated an existing same-day record rather than creating a new one
