"""
Importing this module registers every table on Base.metadata. Alembic's
env.py imports this (not individual model files) so `alembic revision
--autogenerate` always sees the full schema, and nothing can be silently
left out of a migration because someone forgot an import somewhere else.
"""
from app.db.base import Base  # noqa: F401

from app.db.models.user import User, AuthSession, Consent, AuditLog, MigrationRecord  # noqa: F401
from app.db.models.onboarding import OnboardingProfile  # noqa: F401
from app.db.models.scans import FaceScan  # noqa: F401
from app.db.models.logs import DailyLog  # noqa: F401
from app.db.models.products import IngredientProfile, ProductScan, ProductIngredientResult  # noqa: F401
from app.db.models.intelligence import (  # noqa: F401
    ModelVersion,
    ModelRun,
    HealthIndexSnapshot,
    TriggerCorrelation,
    Forecast,
    WhatIfScenario,
    PredictionFeedback,
    IntelligenceEvent,
)
from app.db.models.assistant import AssistantConversation, AssistantMessage  # noqa: F401
from app.db.models.evidence import EvidenceSource  # noqa: F401

__all__ = [
    "Base",
    "User", "AuthSession", "Consent", "AuditLog", "MigrationRecord",
    "OnboardingProfile",
    "FaceScan",
    "DailyLog",
    "IngredientProfile", "ProductScan", "ProductIngredientResult",
    "ModelVersion", "ModelRun", "HealthIndexSnapshot", "TriggerCorrelation",
    "Forecast", "WhatIfScenario", "PredictionFeedback", "IntelligenceEvent",
    "AssistantConversation", "AssistantMessage",
    "EvidenceSource",
]
