"""
Forecast/health-index routes - real implementation. The Cutis Health Index,
TriggerGraph correlations, ClearPath forecast, and What-If simulator are all
backed by ml/health_index_pipeline.py, ml/trigger_pipeline.py, and
ml/forecast_pipeline.py - exact ports of the real v2 formulas operating on
real persisted user history, orchestrated by forecast_service.py.
"""
import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.forecast import ForecastRequest, WhatIfRequest
from app.services import forecast_service

router = APIRouter(tags=["forecast"])


def _snapshot_out(s) -> dict:
    return {
        "id": str(s.id), "computed_at": s.computed_at.isoformat(), "overall_score": s.overall_score,
        "status": s.status, "components": s.components, "driving_factors": s.driving_factors,
        "data_density": s.data_density, "validation_status": s.validation_status,
    }


def _forecast_out(f) -> dict:
    return {
        "id": str(f.id), "generated_at": f.generated_at.isoformat(), "horizon": f.horizon,
        "current_risk": f.current_risk, "forecasted_risk": f.forecasted_risk,
        "best_case_risk": f.best_case_risk, "worst_case_risk": f.worst_case_risk,
        "confidence_interval_low": f.confidence_interval_low, "confidence_interval_high": f.confidence_interval_high,
        "confidence": f.confidence, "validation_status": f.validation_status,
        "key_drivers": f.key_drivers, "recommendations": f.recommendations,
        "estimated_improvement_days": f.estimated_improvement_days,
    }


@router.get("/health-index/latest")
async def health_index_latest(db: DbSession, current_user: CurrentUser) -> dict:
    snapshot = await forecast_service.get_latest_health_index(db, current_user.id)
    return _snapshot_out(snapshot)


@router.get("/health-index/history")
async def health_index_history(db: DbSession, current_user: CurrentUser) -> list[dict]:
    rows = await forecast_service.get_health_index_history(db, current_user.id)
    return [_snapshot_out(r) for r in rows]


@router.post("/forecast")
async def create_forecast(payload: ForecastRequest, db: DbSession, current_user: CurrentUser) -> dict:
    forecast = await forecast_service.generate_forecast(db, current_user.id, payload.horizon_days)
    return _forecast_out(forecast)


@router.post("/what-if")
async def what_if(payload: WhatIfRequest, db: DbSession, current_user: CurrentUser) -> dict:
    scenario = await forecast_service.run_what_if(
        db, current_user.id, [cf.model_dump() for cf in payload.changed_factors], payload.base_forecast_id,
    )
    return {
        "id": str(scenario.id), "baseline_risk": scenario.changed_factors,
        "simulated_risk": scenario.simulated_risk, "estimated_improvement_days": scenario.estimated_improvement_days,
        "explanation": scenario.explanation,
    }
