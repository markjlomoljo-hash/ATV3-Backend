"""Daily log routes. Each endpoint accepts only that log type's validated
shape (schemas/logs.py) and always goes through
log_service.write_or_merge_daily_log, so the same-day merge guarantee is
structurally impossible to bypass from a route handler."""
from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.core.constants import DailyLogType
from app.db.models.logs import DailyLog
from app.schemas.logs import (
    ActivityLogIn,
    ContactLogIn,
    CycleLogIn,
    DailyLogOut,
    FoodLogIn,
    HydrationLogIn,
    SleepLogIn,
    StressLogIn,
)
from app.services import log_service

router = APIRouter(prefix="/logs", tags=["logs"])


def _to_out(row: DailyLog, was_merged: bool) -> DailyLogOut:
    return DailyLogOut(
        id=str(row.id), user_id=str(row.user_id), log_date=row.log_date, log_type=row.log_type,
        data=row.data, created_at=row.created_at.isoformat(), updated_at=row.updated_at.isoformat(),
        was_merged=was_merged,
    )


@router.get("/today", response_model=list[DailyLogOut])
async def get_today_logs(db: DbSession, current_user: CurrentUser, for_date: date | None = Query(default=None)) -> list[DailyLogOut]:
    rows = await log_service.get_today_logs(db, current_user.id, for_date)
    return [_to_out(r, was_merged=False) for r in rows]


@router.post("/sleep", response_model=DailyLogOut)
async def log_sleep(payload: SleepLogIn, db: DbSession, current_user: CurrentUser) -> DailyLogOut:
    row, merged = await log_service.write_or_merge_daily_log(db, current_user.id, DailyLogType.SLEEP.value, payload)
    return _to_out(row, merged)


@router.post("/food", response_model=DailyLogOut)
async def log_food(payload: FoodLogIn, db: DbSession, current_user: CurrentUser) -> DailyLogOut:
    row, merged = await log_service.write_or_merge_daily_log(db, current_user.id, DailyLogType.FOOD.value, payload)
    return _to_out(row, merged)


@router.post("/stress", response_model=DailyLogOut)
async def log_stress(payload: StressLogIn, db: DbSession, current_user: CurrentUser) -> DailyLogOut:
    row, merged = await log_service.write_or_merge_daily_log(db, current_user.id, DailyLogType.STRESS.value, payload)
    return _to_out(row, merged)


@router.post("/activity", response_model=DailyLogOut)
async def log_activity(payload: ActivityLogIn, db: DbSession, current_user: CurrentUser) -> DailyLogOut:
    row, merged = await log_service.write_or_merge_daily_log(db, current_user.id, DailyLogType.ACTIVITY.value, payload)
    return _to_out(row, merged)


@router.post("/contact", response_model=DailyLogOut)
async def log_contact(payload: ContactLogIn, db: DbSession, current_user: CurrentUser) -> DailyLogOut:
    row, merged = await log_service.write_or_merge_daily_log(db, current_user.id, DailyLogType.CONTACT.value, payload)
    return _to_out(row, merged)


@router.post("/hydration", response_model=DailyLogOut)
async def log_hydration(payload: HydrationLogIn, db: DbSession, current_user: CurrentUser) -> DailyLogOut:
    row, merged = await log_service.write_or_merge_daily_log(db, current_user.id, DailyLogType.HYDRATION.value, payload)
    return _to_out(row, merged)


@router.post("/cycle", response_model=DailyLogOut)
async def log_cycle(payload: CycleLogIn, db: DbSession, current_user: CurrentUser) -> DailyLogOut:
    row, merged = await log_service.write_or_merge_daily_log(db, current_user.id, DailyLogType.CYCLE.value, payload)
    return _to_out(row, merged)
