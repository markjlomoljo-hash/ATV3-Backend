from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.core.constants import ConsentType
from app.core.errors import ValidationFailedError
from app.services import network_service

router = APIRouter(prefix="/network", tags=["network"])


class ConsentRequest(BaseModel):
    consent_type: str
    granted: bool


@router.get("/status")
async def network_status(db: DbSession, current_user: CurrentUser) -> dict:
    return await network_service.get_network_status(db, current_user.id)


@router.get("/participants")
async def network_participants(db: DbSession, current_user: CurrentUser) -> dict:
    status = await network_service.get_network_status(db, current_user.id)
    return {"active_research_participants": status["active_research_participants"], "total_accounts": status["total_accounts"]}


@router.post("/consent")
async def post_consent(payload: ConsentRequest, db: DbSession, current_user: CurrentUser) -> dict:
    valid_types = {ConsentType.RESEARCH_PARTICIPATION.value, ConsentType.FEDERATED_LEARNING.value, ConsentType.IMAGE_STORAGE.value}
    if payload.consent_type not in valid_types:
        raise ValidationFailedError(f"consent_type must be one of {sorted(valid_types)}")
    row = await network_service.set_consent(db, current_user.id, payload.consent_type, payload.granted)
    return {"consent_type": row.consent_type, "granted": row.granted, "updated_at": row.updated_at.isoformat()}
