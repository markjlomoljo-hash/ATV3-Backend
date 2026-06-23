"""
Forecast service - orchestration layer between the database and the pure
ml/health_index_pipeline.py, ml/trigger_pipeline.py, ml/forecast_pipeline.py
functions. This is where real user history actually gets pulled and turned
into a persisted HealthIndexSnapshot / TriggerCorrelation / Forecast row.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DailyLogType
from app.core.errors import InsufficientDataError, NotFoundError
from app.db.models.intelligence import Forecast, HealthIndexSnapshot, ModelVersion, TriggerCorrelation, WhatIfScenario
from app.db.models.logs import DailyLog
from app.db.models.onboarding import OnboardingProfile
from app.db.models.products import ProductScan
from app.db.models.scans import FaceScan
from app.ml import forecast_pipeline, health_index_pipeline, trigger_pipeline
from app.services import intelligence_service
from app.services.validation_service import require_forecast_data_density


async def _get_model_version(db: AsyncSession, service: str) -> ModelVersion:
    row = (await db.execute(
        select(ModelVersion).where(ModelVersion.service == service, ModelVersion.is_active.is_(True)).order_by(ModelVersion.created_at.desc())
    )).scalars().first()
    if row is None:
        raise NotFoundError(f"No active model version registered for '{service}'. Run python -m app.db.seed.")
    return row


async def _fetch_history(db: AsyncSession, user_id: uuid.UUID):
    scans = (await db.execute(select(FaceScan).where(FaceScan.user_id == user_id))).scalars().all()
    sleep = (await db.execute(select(DailyLog).where(DailyLog.user_id == user_id, DailyLog.log_type == DailyLogType.SLEEP.value))).scalars().all()
    food = (await db.execute(select(DailyLog).where(DailyLog.user_id == user_id, DailyLog.log_type == DailyLogType.FOOD.value))).scalars().all()
    stress = (await db.execute(select(DailyLog).where(DailyLog.user_id == user_id, DailyLog.log_type == DailyLogType.STRESS.value))).scalars().all()
    routine_products = (await db.execute(select(ProductScan).where(ProductScan.user_id == user_id, ProductScan.in_routine.is_(True)))).scalars().all()
    onboarding = (await db.execute(select(OnboardingProfile).where(OnboardingProfile.user_id == user_id))).scalar_one_or_none()
    return scans, sleep, food, stress, routine_products, onboarding


def _log_datetime(log: DailyLog) -> datetime:
    return datetime.combine(log.log_date, datetime.min.time()).replace(tzinfo=timezone.utc)


async def compute_and_store_health_index(db: AsyncSession, user_id: uuid.UUID) -> HealthIndexSnapshot:
    scans, sleep, food, stress, routine_products, onboarding = await _fetch_history(db, user_id)

    scan_points = [health_index_pipeline.ScanPoint(s.captured_at, s.lesion_count, s.redness_score or 0, s.oiliness_score or 0, s.dryness_score or 0) for s in scans]
    sleep_points = [health_index_pipeline.SleepPoint(_log_datetime(l), l.data.get("netSleepHours", 0)) for l in sleep]
    food_points = [health_index_pipeline.FoodPoint(_log_datetime(l), l.data.get("glycemicLoad", 0), l.data.get("overallRisk", 0)) for l in food]
    stress_points = [health_index_pipeline.StressPoint(_log_datetime(l), l.data.get("stressLevel", 0)) for l in stress]
    high_irritation_count = sum(1 for p in routine_products if (p.irritation_risk or 0) > 60)

    result = health_index_pipeline.compute_health_index(
        scan_points, sleep_points, food_points, stress_points, high_irritation_count,
        onboarding.skin_type if onboarding else None,
    )

    snapshot = HealthIndexSnapshot(
        user_id=user_id, computed_at=datetime.now(timezone.utc),
        overall_score=result["overall_score"], status=result["status"], components=result["components"],
        driving_factors=result["driving_factors"], data_density=result["data_density"],
        validation_status=result["validation_status"],
    )
    db.add(snapshot)
    await db.flush()
    await intelligence_service.emit_event(db, user_id, "health_index_computed", {"overall_score": result["overall_score"], "status": result["status"]})
    return snapshot


async def get_latest_health_index(db: AsyncSession, user_id: uuid.UUID) -> HealthIndexSnapshot:
    existing = (await db.execute(
        select(HealthIndexSnapshot).where(HealthIndexSnapshot.user_id == user_id).order_by(HealthIndexSnapshot.computed_at.desc())
    )).scalars().first()
    if existing is None or (datetime.now(timezone.utc) - existing.computed_at).total_seconds() > 3600:
        return await compute_and_store_health_index(db, user_id)
    return existing


async def get_health_index_history(db: AsyncSession, user_id: uuid.UUID, limit: int = 90) -> list[HealthIndexSnapshot]:
    stmt = select(HealthIndexSnapshot).where(HealthIndexSnapshot.user_id == user_id).order_by(HealthIndexSnapshot.computed_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def compute_and_store_trigger_correlations(db: AsyncSession, user_id: uuid.UUID) -> list[TriggerCorrelation]:
    scans, sleep, food, stress, _routine_products, _onboarding = await _fetch_history(db, user_id)

    scan_lite = [trigger_pipeline.ScanLite(s.captured_at, s.lesion_count) for s in scans]
    sleep_lite = [trigger_pipeline.SleepLite(_log_datetime(l), l.data.get("netSleepHours", 0)) for l in sleep]
    food_lite = [trigger_pipeline.FoodLite(_log_datetime(l), l.data.get("glycemicLoad", 0), l.data.get("dairyIntake", False)) for l in food]
    stress_lite = [trigger_pipeline.StressLite(_log_datetime(l), l.data.get("stressLevel", 0)) for l in stress]

    results = trigger_pipeline.compute_trigger_correlations(scan_lite, sleep_lite, food_lite, stress_lite)

    now = datetime.now(timezone.utc)
    rows = []
    for r in results:
        row = TriggerCorrelation(
            user_id=user_id, computed_at=now, trigger_name=r["factor"],
            correlation_strength=r["correlation_strength"], sample_size=r["sample_size"],
            confidence={"high": 0.85, "moderate": 0.6, "low": 0.35}[r["confidence"]],
            method=r["method"], supporting_data={"category": r["category"], "evidence": r["evidence"], "notes": r["notes"]},
        )
        db.add(row)
        rows.append(row)
    await db.flush()
    if rows:
        await intelligence_service.emit_event(db, user_id, "trigger_correlations_computed", {"count": len(rows)})
    return rows


async def generate_forecast(db: AsyncSession, user_id: uuid.UUID, horizon_days: int = 7) -> Forecast:
    scans, sleep, food, stress, _routine, _onboarding = await _fetch_history(db, user_id)
    total_history = len(scans) + len(sleep) + len(food) + len(stress)
    require_forecast_data_density(total_history)

    correlations = await compute_and_store_trigger_correlations(db, user_id)
    correlation_dicts = [{"factor": c.trigger_name, "correlation_strength": c.correlation_strength} for c in correlations]

    latest_scan = max(scans, key=lambda s: s.captured_at, default=None)
    latest_scan_lite = forecast_pipeline.LatestScan(
        lesion_count=latest_scan.lesion_count if latest_scan else 0,
        redness_score=(latest_scan.redness_score or 0) if latest_scan else 0,
        oiliness_score=(latest_scan.oiliness_score or 0) if latest_scan else 0,
    ) if latest_scan else None

    result = forecast_pipeline.compute_forecast(latest_scan_lite, correlation_dicts, total_history, horizon_days)
    model_version = await _get_model_version(db, "forecast_pipeline")

    forecast = Forecast(
        user_id=user_id, model_version_id=model_version.id, generated_at=datetime.now(timezone.utc),
        horizon=result["horizon"], current_risk=result["current_risk"], forecasted_risk=result["forecasted_risk"],
        best_case_risk=result["best_case_risk"], worst_case_risk=result["worst_case_risk"],
        confidence_interval_low=result["confidence_interval_low"], confidence_interval_high=result["confidence_interval_high"],
        confidence={"low": 0.4, "moderate": 0.65, "high": 0.85, "very_high": 0.95}[result["confidence"]],
        validation_status=result["validation_status"], key_drivers=[{"factor": f} for f in result["key_drivers"]],
        recommendations=result["recommendations"], estimated_improvement_days=result["estimated_improvement_days"],
    )
    db.add(forecast)
    await db.flush()
    await intelligence_service.emit_event(db, user_id, "forecast_generated", {"forecasted_risk": result["forecasted_risk"], "horizon": result["horizon"]})
    return forecast


async def run_what_if(db: AsyncSession, user_id: uuid.UUID, changed_factors: list[dict], base_forecast_id: uuid.UUID | None) -> WhatIfScenario:
    if base_forecast_id is not None:
        base = (await db.execute(select(Forecast).where(Forecast.id == base_forecast_id, Forecast.user_id == user_id))).scalar_one_or_none()
        if base is None:
            raise NotFoundError("Base forecast not found.")
        baseline_risk = base.forecasted_risk
    else:
        base = (await db.execute(select(Forecast).where(Forecast.user_id == user_id).order_by(Forecast.generated_at.desc()))).scalars().first()
        if base is None:
            raise InsufficientDataError("Generate a forecast first via POST /v1/forecast before running a what-if scenario.")
        baseline_risk = base.forecasted_risk
        base_forecast_id = base.id

    result = forecast_pipeline.compute_what_if(baseline_risk, changed_factors)

    scenario = WhatIfScenario(
        user_id=user_id, base_forecast_id=base_forecast_id, changed_factors={"factors": changed_factors},
        simulated_risk=result["simulated_risk"], estimated_improvement_days=result["estimated_improvement_days"],
        explanation=result["explanation"],
    )
    db.add(scenario)
    await db.flush()
    await intelligence_service.emit_event(db, user_id, "what_if_simulated", {"simulated_risk": result["simulated_risk"]})
    return scenario
