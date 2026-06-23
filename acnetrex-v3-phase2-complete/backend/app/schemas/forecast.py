import uuid

from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    horizon_days: int = Field(default=7, ge=1, le=30)


class ChangedFactor(BaseModel):
    factor: str
    direction: str = Field(pattern=r"^(improve|worsen)$")
    magnitude: float = Field(ge=0, le=100)


class WhatIfRequest(BaseModel):
    changed_factors: list[ChangedFactor]
    base_forecast_id: uuid.UUID | None = None
