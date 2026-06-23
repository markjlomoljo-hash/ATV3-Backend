"""
Forecasting, scoring, and intelligence/telemetry models.

ModelVersion + ModelRun exist so every scored/forecasted output is
traceable to *which* model produced it (the spec's "no hardcoded answers...
every output must be traceable to actual data, retrieval, model reasoning"
requirement). IntelligenceEvent is the backing store for the AI status /
task board UI - every "status" shown to the user must originate from a row
written here by a real service action, never a decorative animation.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class ModelVersion(Base, RecordMixin):
    """Registry of every model/pipeline version ever deployed - face
    analysis, forecasting, ingredient risk scoring, assistant routing.
    ModelRun rows reference this so a result can always answer 'which exact
    model produced this'."""

    __tablename__ = "model_versions"

    service: Mapped[str] = mapped_column(String(64), nullable=False)   # face_pipeline|forecast_pipeline|product_pipeline|assistant_routing
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    calibration_params: Mapped[dict] = mapped_column(JSONB, default=dict)


class ModelRun(Base, RecordMixin):
    """One row per inference invocation - input feature summary, output
    summary, latency, and outcome. This is what intelligence_service reads
    to compute real 'AI activity' status instead of a fake animation."""

    __tablename__ = "model_runs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    model_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False)
    input_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(24), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class HealthIndexSnapshot(Base, RecordMixin):
    __tablename__ = "health_index_snapshots"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    components: Mapped[dict] = mapped_column(JSONB, nullable=False)   # barrierIntegrity, inflammationLoad, ...
    driving_factors: Mapped[list[str]] = mapped_column(JSONB, default=list)
    data_density: Mapped[str] = mapped_column(String(16), nullable=False)  # low|moderate|high|very_high
    validation_status: Mapped[str] = mapped_column(String(24), nullable=False)


class TriggerCorrelation(Base, RecordMixin):
    __tablename__ = "trigger_correlations"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trigger_name: Mapped[str] = mapped_column(String(120), nullable=False)
    correlation_strength: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)   # e.g. pearson_lagged, logistic_coef
    supporting_data: Mapped[dict] = mapped_column(JSONB, default=dict)


class Forecast(Base, RecordMixin):
    __tablename__ = "forecasts"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon: Mapped[str] = mapped_column(String(8), nullable=False)   # 7d|14d|30d
    current_risk: Mapped[float] = mapped_column(Float, nullable=False)
    forecasted_risk: Mapped[float] = mapped_column(Float, nullable=False)
    best_case_risk: Mapped[float] = mapped_column(Float, nullable=False)
    worst_case_risk: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_interval_low: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_interval_high: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(24), nullable=False)
    key_drivers: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    recommendations: Mapped[list[str]] = mapped_column(JSONB, default=list)
    estimated_improvement_days: Mapped[int | None] = mapped_column(Integer, nullable=True)


class WhatIfScenario(Base, RecordMixin):
    __tablename__ = "what_if_scenarios"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    base_forecast_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("forecasts.id", ondelete="SET NULL"), nullable=True)
    changed_factors: Mapped[dict] = mapped_column(JSONB, nullable=False)   # {factor: magnitude, ...}
    simulated_risk: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_improvement_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)


class PredictionFeedback(Base, RecordMixin):
    """User-reported ground truth against a prior forecast/scan/scenario -
    the input that calibration_service uses for safe per-user recalibration
    (never uncontrolled retraining)."""

    __tablename__ = "prediction_feedback"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    forecast_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("forecasts.id", ondelete="SET NULL"), nullable=True)
    outcome_reported: Mapped[str] = mapped_column(String(32), nullable=False)  # breakout_occurred|no_change|improved|worsened
    was_helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IntelligenceEvent(Base, RecordMixin):
    """Backing store for the AI Status / Intelligence Core UI. Every
    meaningful AI/ML action (scan analyzed, forecast generated, evidence
    retrieved, calibration updated, milestone reached) writes one row here.
    intelligence_service reads recent rows to compute the readiness score and
    'what is the AI doing right now' status shown to the user - real state,
    not a canned animation."""

    __tablename__ = "intelligence_events"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)  # scan_analyzed|forecast_generated|evidence_retrieved|calibration_updated|milestone
    event_detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
