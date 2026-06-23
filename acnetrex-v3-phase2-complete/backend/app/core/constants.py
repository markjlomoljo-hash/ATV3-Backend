"""Shared enums/constants. Centralized so log types, statuses, etc. can't
drift between models, schemas, and services."""
from enum import StrEnum


class DailyLogType(StrEnum):
    SLEEP = "sleep"
    FOOD = "food"
    STRESS = "stress"
    ACTIVITY = "activity"
    CONTACT = "contact"
    HYDRATION = "hydration"
    CYCLE = "cycle"


class FaceScanType(StrEnum):
    BASELINE = "baseline"   # onboarding live-camera scan
    DAILY = "daily"          # 5-photo FaceAtlas flow


class ScanQuality(StrEnum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class HealthIndexStatus(StrEnum):
    HEALTHY = "healthy"
    STABLE = "stable"
    WATCHLIST = "watchlist"
    AT_RISK = "at_risk"
    COMPROMISED = "compromised"


class ValidationStatus(StrEnum):
    PASSED = "passed"
    INSUFFICIENT_DATA = "insufficient_data"
    LOW_CONFIDENCE = "low_confidence"
    FAILED = "failed"


class ModelTier(StrEnum):
    BOOTSTRAP = "bootstrap"
    DEVELOPING = "developing"
    CALIBRATED = "calibrated"
    ADVANCED = "advanced"


class ConsentType(StrEnum):
    PRIVACY = "privacy"               # baseline terms, required
    RESEARCH_PARTICIPATION = "research_participation"
    FEDERATED_LEARNING = "federated_learning"
    IMAGE_STORAGE = "image_storage"


class AppRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


LEGACY_SOURCE_TAG = "localStorage_v2"
CURRENT_SOURCE_TAG = "app_v3"

# Same-day-merge applies to every one of these log types (per spec section
# "SAME-DAY LOG MERGE RULE"). Centralized so log_service and the API schema
# validators can't disagree about which types are daily-mergeable.
MERGEABLE_DAILY_LOG_TYPES = {t.value for t in DailyLogType}
