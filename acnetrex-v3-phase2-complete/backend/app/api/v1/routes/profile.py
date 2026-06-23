from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.profile import ProfileOut, ProfilePatchRequest
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
async def get_profile(db: DbSession, current_user: CurrentUser) -> ProfileOut:
    user = await profile_service.get_profile(db, current_user.id)
    return ProfileOut.model_validate(user)


@router.patch("", response_model=ProfileOut)
async def patch_profile(payload: ProfilePatchRequest, db: DbSession, current_user: CurrentUser) -> ProfileOut:
    user = await profile_service.patch_profile(db, current_user.id, payload)
    return ProfileOut.model_validate(user)
