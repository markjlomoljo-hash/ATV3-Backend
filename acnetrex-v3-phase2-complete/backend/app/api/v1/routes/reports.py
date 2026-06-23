from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.errors import NotImplementedYetError
from app.services import export_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/export.json")
async def export_json(db: DbSession, current_user: CurrentUser) -> dict:
    return await export_service.build_export(db, current_user.id)


@router.get("/export.pdf")
async def export_pdf(db: DbSession, current_user: CurrentUser):
    raise NotImplementedYetError(
        "Clinical-layout PDF rendering (export_service.render_pdf) ships in Phase 2 - the underlying data is already real and available today via GET /reports/export.json."
    )
