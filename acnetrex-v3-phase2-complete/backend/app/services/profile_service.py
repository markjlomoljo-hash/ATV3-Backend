"""Account profile service - account-level fields only (email, display name).
Onboarding answers live in onboarding_service.py since they're a distinct
concern with their own completion/versioning lifecycle."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models.user import User
from app.schemas.profile import ProfilePatchRequest


async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise NotFoundError("Profile not found.")
    return user


async def patch_profile(db: AsyncSession, user_id: uuid.UUID, payload: ProfilePatchRequest) -> User:
    user = await get_profile(db, user_id)
    if payload.display_name is not None:
        name = payload.display_name.strip()
        if name:
            user.display_name = name
    await db.flush()
    return user
