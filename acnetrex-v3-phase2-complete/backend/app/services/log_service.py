"""
Same-day daily log service.

This is the literal implementation of the spec's most-repeated rule: if a
user logs the same type again on the same calendar day, the existing record
is updated, never duplicated. It's enforced two ways at once - defense in
depth, not redundancy for its own sake:

1. A UNIQUE constraint on (user_id, log_date, log_type) at the database
   level (see db/models/logs.py), so it holds even under concurrent or
   retried requests.
2. Application logic here that looks up the existing row first and merges
   into it, so a normal single-request save behaves predictably without
   relying on catching a constraint violation.

The derived risk/score fields below (sleep debt, food overall risk, activity
breakout risk) are reproduced from the actual formulas in the recovered v2
bundle (functions inlined in deployed-bundle.pretty.js around the sleep/
food/activity log submit handlers), not reinvented, so historical trend
lines stay meaningful across the v2 -> v3 upgrade.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DailyLogType
from app.db.models.logs import DailyLog
from app.schemas.logs import ActivityLogIn, FoodLogIn, SleepLogIn


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_sleep_fields(payload: SleepLogIn) -> dict:
    bh, bm = (int(x) for x in payload.bedtime.split(":"))
    wh, wm = (int(x) for x in payload.wake_time.split(":"))
    bed_minutes = bh * 60 + bm
    wake_minutes = wh * 60 + wm
    if wake_minutes <= bed_minutes:
        wake_minutes += 1440  # crossed midnight
    net_sleep_hours = round(((wake_minutes - bed_minutes) / 60) * 10) / 10
    sleep_debt = max(0.0, 7.5 - net_sleep_hours)
    return {
        "bedtime": payload.bedtime,
        "wakeTime": payload.wake_time,
        "netSleepHours": net_sleep_hours,
        "quality": payload.quality,
        "fragmented": payload.fragmented,
        "lateNightShift": payload.late_night_shift,
        "sleepDebt": round(sleep_debt, 2),
    }


def compute_food_fields(payload: FoodLogIn) -> dict:
    overall_risk = round(
        payload.glycemic_load * 0.4
        + (20 if payload.dairy_intake else 0)
        + (15 if payload.whey_protein else 0)
        + (20 if payload.sugar_load == "high" else 10 if payload.sugar_load == "moderate" else 0)
        + (15 if payload.processed_food_level == "high" else 7 if payload.processed_food_level == "moderate" else 0)
    )
    return {
        "meals": [{"id": str(uuid.uuid4()), "name": m.name, "category": "meal", "riskScore": 30} for m in payload.meals],
        "hydrationLiters": payload.hydration_liters,
        "glycemicLoad": payload.glycemic_load,
        "dairyIntake": payload.dairy_intake,
        "wheyProtein": payload.whey_protein,
        "sugarLoad": payload.sugar_load,
        "processedFoodLevel": payload.processed_food_level,
        "overallRisk": min(overall_risk, 100),
    }


def compute_activity_fields(payload: ActivityLogIn) -> dict:
    breakout_risk = round(
        (30 if payload.sweat_level == "heavy" else 10 if payload.sweat_level == "light" else 0)
        + (30 if payload.post_workout_cleanse_delay_minutes > 60 else 15 if payload.post_workout_cleanse_delay_minutes > 30 else 0)
        + (15 if payload.intensity == "vigorous" else 5 if payload.intensity == "moderate" else 0)
        + len(payload.friction_factors) * 8
    )
    return {
        "activityType": payload.activity_type,
        "intensity": payload.intensity,
        "durationMinutes": payload.duration_minutes,
        "sweatLevel": payload.sweat_level,
        "postWorkoutCleansDelay": payload.post_workout_cleanse_delay_minutes,
        "frictionFactors": payload.friction_factors,
        "breakoutRisk": min(breakout_risk, 100),
    }


def compute_passthrough_fields(payload) -> dict:
    """Stress/contact/hydration/cycle logs had no derived-score formula in
    the recovered bundle - they're stored as the user reported them and feed
    directly into CHI/trigger-correlation calculations downstream."""
    data = payload.model_dump(exclude={"log_date"})
    if "target_liters" in data:
        data["metTarget"] = data["water_intake_liters"] >= data["target_liters"]
    return {_to_camel(k): v for k, v in data.items()}


def _to_camel(snake: str) -> str:
    head, *tail = snake.split("_")
    return head + "".join(w.capitalize() for w in tail)


DERIVED_FIELD_BUILDERS = {
    DailyLogType.SLEEP.value: compute_sleep_fields,
    DailyLogType.FOOD.value: compute_food_fields,
    DailyLogType.ACTIVITY.value: compute_activity_fields,
}


def build_log_data(log_type: str, payload) -> dict:
    builder = DERIVED_FIELD_BUILDERS.get(log_type)
    if builder:
        return builder(payload)
    return compute_passthrough_fields(payload)


async def write_or_merge_daily_log(db: AsyncSession, user_id: uuid.UUID, log_type: str, payload) -> tuple[DailyLog, bool]:
    """Returns (row, was_merged). was_merged=True means an existing same-day
    record was updated rather than a new one created."""
    target_date: date = payload.log_date or datetime.now(timezone.utc).date()
    computed = build_log_data(log_type, payload)

    stmt = select(DailyLog).where(
        DailyLog.user_id == user_id,
        DailyLog.log_date == target_date,
        DailyLog.log_type == log_type,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing is not None:
        existing.data = {**existing.data, **computed}
        existing.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return existing, True

    new_log = DailyLog(user_id=user_id, log_date=target_date, log_type=log_type, data=computed)
    db.add(new_log)
    try:
        await db.flush()
        return new_log, False
    except IntegrityError:
        # A concurrent request won the race and inserted first (the unique
        # constraint caught it). Roll back this attempt and merge into the
        # row that now exists instead of surfacing a duplicate-key error.
        await db.rollback()
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing is None:
            raise
        existing.data = {**existing.data, **computed}
        existing.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return existing, True


async def get_today_logs(db: AsyncSession, user_id: uuid.UUID, target_date: date | None = None) -> list[DailyLog]:
    target_date = target_date or datetime.now(timezone.utc).date()
    stmt = select(DailyLog).where(DailyLog.user_id == user_id, DailyLog.log_date == target_date)
    return list((await db.execute(stmt)).scalars().all())
