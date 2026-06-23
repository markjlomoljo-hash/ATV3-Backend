"""
Intelligence Core status service.

Every number this returns comes from a real query - no field here is a
decorative animation value. Until Phase 2 services start writing
ModelRun/IntelligenceEvent rows (face analysis, forecasting, evidence
retrieval, the assistant), the honest state is "no AI/ML activity yet for
this account," and that is exactly what this returns: zero counts and a
'bootstrap' tier, not a fabricated number to make the UI look alive.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ModelTier
from app.db.models.intelligence import IntelligenceEvent, ModelRun, ModelVersion


async def get_status(db: AsyncSession, user_id: uuid.UUID) -> dict:
    total_runs = (await db.execute(
        select(func.count()).select_from(ModelRun).where(ModelRun.user_id == user_id)
    )).scalar_one()

    last_run_at = (await db.execute(
        select(func.max(ModelRun.created_at)).where(ModelRun.user_id == user_id)
    )).scalar_one()

    active_models = (await db.execute(
        select(func.count()).select_from(ModelVersion).where(ModelVersion.is_active.is_(True))
    )).scalar_one()

    recent_window = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_events = (await db.execute(
        select(func.count()).select_from(IntelligenceEvent).where(
            IntelligenceEvent.user_id == user_id, IntelligenceEvent.occurred_at >= recent_window,
        )
    )).scalar_one()

    if total_runs == 0:
        tier = ModelTier.BOOTSTRAP.value
    elif total_runs < 10:
        tier = ModelTier.DEVELOPING.value
    elif total_runs < 50:
        tier = ModelTier.CALIBRATED.value
    else:
        tier = ModelTier.ADVANCED.value

    return {
        "tier": tier,
        "total_inferences": total_runs,
        "active_models": active_models,
        "events_last_24h": recent_events,
        "last_activity_at": last_run_at.isoformat() if last_run_at else None,
        "is_idle": last_run_at is None or (datetime.now(timezone.utc) - last_run_at) > timedelta(hours=1),
    }


async def list_events(db: AsyncSession, user_id: uuid.UUID, limit: int = 50) -> list[IntelligenceEvent]:
    stmt = select(IntelligenceEvent).where(IntelligenceEvent.user_id == user_id).order_by(IntelligenceEvent.occurred_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def list_model_versions(db: AsyncSession) -> list[ModelVersion]:
    stmt = select(ModelVersion).where(ModelVersion.is_active.is_(True)).order_by(ModelVersion.service)
    return list((await db.execute(stmt)).scalars().all())


async def emit_event(db: AsyncSession, user_id: uuid.UUID, event_type: str, detail: dict | None = None) -> IntelligenceEvent:
    """Called by every Phase-2 ML service after a real inference/retrieval
    action. This is the only way an IntelligenceEvent row gets created -
    there is no path that writes one without a real backing action."""
    event = IntelligenceEvent(user_id=user_id, event_type=event_type, event_detail=detail or {}, occurred_at=datetime.now(timezone.utc))
    db.add(event)
    await db.flush()
    return event
