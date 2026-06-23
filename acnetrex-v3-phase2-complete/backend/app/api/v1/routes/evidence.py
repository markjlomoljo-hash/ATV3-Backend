"""DermVault evidence routes - real keyword/vector search via evidence_service."""
import uuid

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession
from app.services import evidence_service

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/search")
async def search_evidence(
    db: DbSession, current_user: CurrentUser, q: str = Query(min_length=2)
) -> list[dict]:
    rows = await evidence_service.search_by_keywords(db, q)
    return [evidence_service.evidence_to_dict(r) for r in rows]


@router.get("/{evidence_id}")
async def get_evidence(evidence_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> dict:
    row = await evidence_service.get_evidence(db, evidence_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Evidence source not found.")
    return evidence_service.evidence_to_dict(row)
