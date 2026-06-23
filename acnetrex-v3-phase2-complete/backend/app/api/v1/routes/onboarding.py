from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.onboarding import OnboardingOut, OnboardingPatchRequest
from app.services import onboarding_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("", response_model=OnboardingOut)
async def get_onboarding(db: DbSession, current_user: CurrentUser) -> OnboardingOut:
    profile = await onboarding_service.get_or_create_onboarding(db, current_user.id)
    return OnboardingOut.model_validate(profile)


@router.patch("", response_model=OnboardingOut)
async def patch_onboarding(payload: OnboardingPatchRequest, db: DbSession, current_user: CurrentUser) -> OnboardingOut:
    profile = await onboarding_service.patch_onboarding(db, current_user.id, payload)
    return OnboardingOut.model_validate(profile)


@router.post("/complete", response_model=OnboardingOut)
async def complete_onboarding(db: DbSession, current_user: CurrentUser) -> OnboardingOut:
    profile = await onboarding_service.complete_onboarding(db, current_user.id)
    return OnboardingOut.model_validate(profile)
