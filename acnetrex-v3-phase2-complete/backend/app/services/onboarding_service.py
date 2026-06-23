"""Onboarding service. The 8-step flow saves progress incrementally via
PATCH (current_step advances as the user moves through steps), and
/onboarding/complete is a distinct explicit action so 'completed' can never
be set as a side effect of an unrelated field update."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.onboarding import OnboardingProfile
from app.schemas.onboarding import OnboardingPatchRequest


async def get_or_create_onboarding(db: AsyncSession, user_id: uuid.UUID) -> OnboardingProfile:
    profile = (await db.execute(select(OnboardingProfile).where(OnboardingProfile.user_id == user_id))).scalar_one_or_none()
    if profile is None:
        profile = OnboardingProfile(user_id=user_id)
        db.add(profile)
        await db.flush()
    return profile


async def patch_onboarding(db: AsyncSession, user_id: uuid.UUID, payload: OnboardingPatchRequest) -> OnboardingProfile:
    profile = await get_or_create_onboarding(db, user_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(profile, field, value)
    await db.flush()
    return profile


async def complete_onboarding(db: AsyncSession, user_id: uuid.UUID) -> OnboardingProfile:
    profile = await get_or_create_onboarding(db, user_id)
    profile.completed = True
    profile.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return profile


async def attach_baseline_scan(db: AsyncSession, user_id: uuid.UUID, scan_id: uuid.UUID) -> OnboardingProfile:
    """Called by scan_service after the onboarding live-camera baseline scan
    is analyzed, so onboarding and scan history stay linked without the
    frontend having to coordinate two separate calls."""
    profile = await get_or_create_onboarding(db, user_id)
    profile.baseline_scan_completed = True
    profile.baseline_scan_id = scan_id
    await db.flush()
    return profile
