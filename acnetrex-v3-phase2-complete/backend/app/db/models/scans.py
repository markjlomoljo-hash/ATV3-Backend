"""
Face scan model.

Preserves every field the recovered v2 `m5` mock scan generator produced
(zones, lesionCount, lesionTypes, redness/oiliness/dryness, PIH, scar
visibility, scanQuality, confidence, validationStatus) so history is
schema-compatible across the upgrade, but adds what v2 never had: a real
image reference, a model_version that ties a result to a specific inference
pipeline run, and a confidence_score the validation_service actually
enforces a minimum on before the result is shown to the user.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class FaceScan(Base, RecordMixin):
    __tablename__ = "face_scans"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scan_type: Mapped[str] = mapped_column(String(16), nullable=False)  # baseline | daily
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # --- Image storage (consent-gated; null if the user didn't consent to
    # image retention - analysis can still run and be discarded post-inference) ---
    image_s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_consent: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Per-zone results: forehead, leftCheek, rightCheek, nose, chin,
    # jawline (daily 5-photo flow) - each holding
    # { zone, condition, lesionCount, redness, oiliness, observations[] } ---
    zones: Mapped[dict] = mapped_column(JSONB, default=dict)

    # --- Lesion classification: [{ type: "papule"|"pustule"|"comedone"|...,
    # count }] ---
    lesions: Mapped[dict] = mapped_column(JSONB, default=dict)

    overall_condition: Mapped[str | None] = mapped_column(String(16), nullable=True)  # none|mild|moderate|severe
    lesion_count: Mapped[int] = mapped_column(Integer, default=0)
    redness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    oiliness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dryness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_inflammatory_marks: Mapped[int] = mapped_column(Integer, default=0)
    scar_visibility: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # --- Inference quality/trust metadata - this is what makes the result
    # real instead of decorative: quality_score and confidence_score are
    # computed by ml/face_pipeline.py from actual image properties, and
    # validation_service refuses to surface a result below
    # settings.MIN_FACE_CONFIDENCE / MIN_IMAGE_QUALITY_SCORE. ---
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_valid_face: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(24), nullable=False)  # passed|insufficient_data|low_confidence|failed
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)

    health_index_at_scan: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
