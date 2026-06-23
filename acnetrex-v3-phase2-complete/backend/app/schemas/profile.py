import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProfilePatchRequest(BaseModel):
    display_name: str | None = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    email_verified: bool
    created_at: datetime
    last_login_at: datetime | None
    app_version: str
    legacy_user_id: str | None
