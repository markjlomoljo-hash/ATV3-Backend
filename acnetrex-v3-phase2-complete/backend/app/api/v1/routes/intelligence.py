from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.services import intelligence_service

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/status")
async def status(db: DbSession, current_user: CurrentUser) -> dict:
    return await intelligence_service.get_status(db, current_user.id)


@router.get("/events")
async def events(db: DbSession, current_user: CurrentUser) -> list[dict]:
    rows = await intelligence_service.list_events(db, current_user.id)
    return [
        {"id": str(r.id), "event_type": r.event_type, "detail": r.event_detail, "occurred_at": r.occurred_at.isoformat()}
        for r in rows
    ]


@router.get("/model-versions")
async def model_versions(db: DbSession, current_user: CurrentUser) -> list[dict]:
    rows = await intelligence_service.list_model_versions(db)
    return [
        {"id": str(r.id), "service": r.service, "version": r.version, "description": r.description}
        for r in rows
    ]
