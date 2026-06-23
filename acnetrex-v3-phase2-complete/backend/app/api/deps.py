"""Shared FastAPI dependencies. get_current_user is what every protected
route depends on - it's the single place that turns a bearer token into a
real, session-checked User, so auth can never be accidentally bypassed by a
route forgetting to check something."""
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.session import get_db
from app.services import auth_service

_bearer_scheme = HTTPBearer(auto_error=True)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> User:
    return await auth_service.get_user_from_token(db, credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]
