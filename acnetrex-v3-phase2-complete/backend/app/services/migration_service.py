"""
Legacy v2 -> v3 migration service.

Import-only, by design: the frontend reads the old localStorage keys
(acnetrex_credentials, acnetrex_auth_v2, acnetrex_data_v2, acnetrex_ai_v2),
the user signs up or logs in for real (this service never trusts the old
SHA-256+static-salt hash as a credential), grants explicit import consent,
and then POSTs the raw legacy JSON blobs here. Every imported row is tagged
source="localStorage_v2" and gets a MigrationRecord audit entry. If a v3
record already exists for the same user+date+type, the legacy version is
skipped, not overwritten - "avoid blind overwrites if backend records
already exist" from the migration plan.
"""
import uuid
from datetime import date as date_type, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ConsentType, LEGACY_SOURCE_TAG
from app.core.errors import MigrationError
from app.db.models.assistant import AssistantConversation, AssistantMessage
from app.db.models.logs import DailyLog
from app.db.models.onboarding import OnboardingProfile
from app.db.models.products import ProductScan
from app.db.models.scans import FaceScan
from app.db.models.user import Consent, MigrationRecord

# Legacy field names (camelCase, as produced by the v2 Zustand store) mapped
# to log_type. Anything in legacy_data_v2 under these keys is daily-log
# shaped: a list of objects each carrying a `date` field.
LEGACY_LOG_LIST_KEYS = {
    "sleepLogs": "sleep",
    "foodLogs": "food",
    "stressLogs": "stress",
    "activityLogs": "activity",
    "hydrationLogs": "hydration",
    "cycleLogs": "cycle",
    "contactLogs": "contact",
}


def _parse_date(value: str) -> date_type:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


class MigrationSummary:
    def __init__(self) -> None:
        self.imported = 0
        self.skipped = 0
        self.failed = 0
        self.details: list[dict] = []

    def record(self, status: str, entity_type: str, legacy_id: str | None, detail: str | None = None) -> None:
        if status == "imported":
            self.imported += 1
        elif status == "skipped":
            self.skipped += 1
        else:
            self.failed += 1
        self.details.append({"status": status, "entity_type": entity_type, "legacy_id": legacy_id, "detail": detail})

    def as_dict(self) -> dict:
        return {"imported": self.imported, "skipped": self.skipped, "failed": self.failed, "details": self.details}


async def _write_migration_record(db: AsyncSession, user_id: uuid.UUID, legacy_key: str, legacy_id: str | None, entity_type: str, new_id: uuid.UUID | None, status: str, detail: str | None = None) -> None:
    db.add(MigrationRecord(
        user_id=user_id, legacy_key=legacy_key, legacy_id=legacy_id, entity_type=entity_type,
        new_record_id=new_id, status=status, detail=detail, imported_at=datetime.now(timezone.utc),
    ))


async def import_daily_logs(db: AsyncSession, user_id: uuid.UUID, legacy_data: dict, summary: MigrationSummary) -> None:
    for legacy_key, log_type in LEGACY_LOG_LIST_KEYS.items():
        entries: list[dict] = legacy_data.get(legacy_key) or []
        for entry in entries:
            legacy_id = entry.get("id")
            raw_date = entry.get("date")
            if not raw_date:
                summary.record("skipped", log_type, legacy_id, "missing date")
                continue
            try:
                log_date = _parse_date(raw_date)
            except ValueError:
                summary.record("failed", log_type, legacy_id, f"unparseable date: {raw_date}")
                continue

            existing = (await db.execute(
                select(DailyLog).where(DailyLog.user_id == user_id, DailyLog.log_date == log_date, DailyLog.log_type == log_type)
            )).scalar_one_or_none()
            if existing is not None:
                summary.record("skipped", log_type, legacy_id, "v3 record already exists for this date - not overwritten")
                continue

            data = {k: v for k, v in entry.items() if k not in {"id", "userId", "date", "createdAt"}}
            new_log = DailyLog(user_id=user_id, log_date=log_date, log_type=log_type, data=data, source=LEGACY_SOURCE_TAG)
            db.add(new_log)
            await db.flush()
            await _write_migration_record(db, user_id, "acnetrex_data_v2", legacy_id, log_type, new_log.id, "imported")
            summary.record("imported", log_type, legacy_id)


async def import_face_scans(db: AsyncSession, user_id: uuid.UUID, legacy_data: dict, summary: MigrationSummary) -> None:
    for entry in legacy_data.get("faceScans") or []:
        legacy_id = entry.get("id")
        timestamp = entry.get("timestamp")
        if not timestamp:
            summary.record("skipped", "face_scan", legacy_id, "missing timestamp")
            continue
        try:
            captured_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            summary.record("failed", "face_scan", legacy_id, f"unparseable timestamp: {timestamp}")
            continue

        # v2's scan engine was a mock that never inspected the image (see
        # handoff doc section 10). We import the historical record honestly
        # labeled as such - confidence is floored and model_version makes
        # clear this did not come from the real pipeline, so forecast_service
        # can choose to weight it down rather than treat it as equal-quality
        # evidence to a v3 real-pipeline scan.
        scan = FaceScan(
            user_id=user_id,
            scan_type=entry.get("type", "daily"),
            captured_at=captured_at,
            zones=entry.get("zones") or {},
            lesions={"lesionTypes": entry.get("lesionTypes") or []},
            overall_condition=entry.get("overallCondition"),
            lesion_count=entry.get("lesionCount") or 0,
            redness_score=entry.get("rednessScore"),
            oiliness_score=entry.get("oilinessScore"),
            dryness_score=entry.get("drynessScore"),
            post_inflammatory_marks=entry.get("postInflammatoryMarks") or 0,
            scar_visibility=entry.get("scarVisibility"),
            quality_score=0.0,
            is_valid_face=False,
            confidence_score=0.0,
            validation_status="failed",
            model_version="legacy_v2_mock_unverified",
            health_index_at_scan=entry.get("healthIndex"),
            notes=entry.get("notes"),
            source=LEGACY_SOURCE_TAG,
        )
        db.add(scan)
        await db.flush()
        await _write_migration_record(db, user_id, "acnetrex_data_v2", legacy_id, "face_scan", scan.id, "imported", "imported as unverified - v2 scan engine did not analyze actual image pixels")
        summary.record("imported", "face_scan", legacy_id)


async def import_product_scans(db: AsyncSession, user_id: uuid.UUID, legacy_data: dict, summary: MigrationSummary) -> None:
    for entry in legacy_data.get("productScans") or []:
        legacy_id = entry.get("id")
        added_at_raw = entry.get("addedAt") or entry.get("timestamp")
        try:
            added_at = datetime.fromisoformat(added_at_raw.replace("Z", "+00:00")) if added_at_raw else datetime.now(timezone.utc)
        except ValueError:
            added_at = datetime.now(timezone.utc)

        scan = ProductScan(
            user_id=user_id,
            product_name=entry.get("productName", "Unknown product"),
            brand=entry.get("brand"),
            category=entry.get("category"),
            input_method=entry.get("inputMethod", "manual"),
            overall_risk=entry.get("overallRisk"),
            comedogenic_score=entry.get("comedogenicScore"),
            irritation_risk=entry.get("irritationRisk"),
            barrier_support_score=entry.get("barrierSupportScore"),
            acne_trigger_likelihood=entry.get("acneTriggerLikelihood"),
            conclusion=entry.get("conclusion"),
            confidence_level=entry.get("confidenceLevel"),
            model_version="legacy_v2_hardcoded_dictionary",
            in_routine=entry.get("inRoutine", False),
            added_at=added_at,
            source=LEGACY_SOURCE_TAG,
        )
        db.add(scan)
        await db.flush()
        await _write_migration_record(db, user_id, "acnetrex_data_v2", legacy_id, "product_scan", scan.id, "imported")
        summary.record("imported", "product_scan", legacy_id)


async def import_onboarding(db: AsyncSession, user_id: uuid.UUID, legacy_auth: dict, summary: MigrationSummary) -> None:
    legacy_profile = (legacy_auth or {}).get("onboardingProfile")
    if not legacy_profile:
        return
    existing = (await db.execute(select(OnboardingProfile).where(OnboardingProfile.user_id == user_id))).scalar_one_or_none()
    if existing is not None and existing.completed:
        summary.record("skipped", "onboarding_profile", None, "v3 onboarding already completed - not overwritten")
        return

    field_map = {
        "age": "age", "sex": "sex", "lifeStatus": "life_status",
        "skinType": "skin_type", "acneType": "acne_type", "acneSeverity": "acne_severity",
        "skinGoals": "skin_goals", "familyAcneHistory": "family_acne_history",
        "sleepHours": "sleep_hours", "bedtime": "bedtime", "stressLevel": "stress_level",
        "exerciseFrequency": "exercise_frequency", "dietType": "diet_type", "showerFrequency": "shower_frequency",
        "currentProducts": "current_products", "sunscreenHabit": "sunscreen_habit",
        "exfoliationFrequency": "exfoliation_frequency", "healthConditions": "health_conditions",
        "maintenanceMedications": "maintenance_medications", "trackCycle": "track_cycle",
    }
    target = existing or OnboardingProfile(user_id=user_id)
    for legacy_field, new_field in field_map.items():
        if legacy_field in legacy_profile and legacy_profile[legacy_field] is not None:
            setattr(target, new_field, legacy_profile[legacy_field])
    if "height" in legacy_profile:
        target.height_cm = legacy_profile["height"]
    if "weight" in legacy_profile:
        target.weight_kg = legacy_profile["weight"]
    target.completed = bool(legacy_profile.get("completed", False))
    target.current_step = legacy_profile.get("currentStep", target.current_step)
    target.source = LEGACY_SOURCE_TAG
    if existing is None:
        db.add(target)
    await db.flush()
    await _write_migration_record(db, user_id, "acnetrex_auth_v2", None, "onboarding_profile", target.user_id, "imported")
    summary.record("imported", "onboarding_profile", None)


async def import_consents(db: AsyncSession, user_id: uuid.UUID, legacy_user: dict, summary: MigrationSummary) -> None:
    consent_map = {
        "consentResearch": ConsentType.RESEARCH_PARTICIPATION.value,
        "consentFederated": ConsentType.FEDERATED_LEARNING.value,
    }
    now = datetime.now(timezone.utc)
    for legacy_field, consent_type in consent_map.items():
        if legacy_user.get(legacy_field):
            db.add(Consent(user_id=user_id, consent_type=consent_type, granted=True, granted_at=now, source=LEGACY_SOURCE_TAG))
            summary.record("imported", "consent", legacy_field)


async def import_assistant_history(db: AsyncSession, user_id: uuid.UUID, legacy_ai: dict, summary: MigrationSummary) -> None:
    conversations = (legacy_ai or {}).get("conversations") or []
    for conv in conversations:
        legacy_conv_id = conv.get("id")
        new_conv = AssistantConversation(user_id=user_id, title=conv.get("title"), source=LEGACY_SOURCE_TAG)
        db.add(new_conv)
        await db.flush()
        for msg in conv.get("messages") or []:
            db.add(AssistantMessage(
                conversation_id=new_conv.id,
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                model_version="legacy_v2_keyword_template" if msg.get("role") == "assistant" else None,
                source=LEGACY_SOURCE_TAG,
            ))
        await db.flush()
        await _write_migration_record(db, user_id, "acnetrex_ai_v2", legacy_conv_id, "assistant_conversation", new_conv.id, "imported", "v2 responses were local keyword templates, not LLM output - imported for history only")
        summary.record("imported", "assistant_conversation", legacy_conv_id)


async def run_full_migration(
    db: AsyncSession,
    user_id: uuid.UUID,
    legacy_auth_v2: dict[str, Any] | None,
    legacy_data_v2: dict[str, Any] | None,
    legacy_ai_v2: dict[str, Any] | None,
) -> dict:
    """Entry point called by the migration API route once the user has a
    real v3 account and has explicitly consented to importing their old
    local data. Never call this without that consent already recorded."""
    if not (legacy_auth_v2 or legacy_data_v2 or legacy_ai_v2):
        raise MigrationError("No legacy data provided to migrate.")

    summary = MigrationSummary()
    legacy_data_v2 = legacy_data_v2 or {}

    if legacy_auth_v2:
        await import_onboarding(db, user_id, legacy_auth_v2, summary)
        if legacy_auth_v2.get("user"):
            await import_consents(db, user_id, legacy_auth_v2["user"], summary)

    await import_daily_logs(db, user_id, legacy_data_v2, summary)
    await import_face_scans(db, user_id, legacy_data_v2, summary)
    await import_product_scans(db, user_id, legacy_data_v2, summary)

    if legacy_ai_v2:
        await import_assistant_history(db, user_id, legacy_ai_v2, summary)

    await db.flush()
    return summary.as_dict()
