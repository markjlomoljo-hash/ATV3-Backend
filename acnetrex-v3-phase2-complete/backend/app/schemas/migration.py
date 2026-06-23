"""Schemas for the one-time legacy localStorage import endpoint. The
frontend reads acnetrex_auth_v2 / acnetrex_data_v2 / acnetrex_ai_v2 from
localStorage and POSTs the raw parsed JSON here - this service never reads
the browser's storage directly since it has no access to it."""
from typing import Any

from pydantic import BaseModel, Field


class LegacyMigrationRequest(BaseModel):
    consent_to_import: bool = Field(description="Must be true - explicit user consent to import old local data")
    legacy_auth_v2: dict[str, Any] | None = None
    legacy_data_v2: dict[str, Any] | None = None
    legacy_ai_v2: dict[str, Any] | None = None


class LegacyMigrationResult(BaseModel):
    imported: int
    skipped: int
    failed: int
    details: list[dict]
