"""
Product/ingredient intelligence models.

v2 had a hardcoded ingredient dictionary baked into the JS bundle (~20
entries). That's exactly the kind of "developer fed data" the spec says to
eliminate: IngredientProfile replaces it with a real, queryable, versionable
reference table that product_service can grow over time and link to
evidence_sources, instead of a fixed list shipped in a bundle. ProductScan is
the user-facing record of a single analysis; ProductIngredientResult is the
per-ingredient breakdown for that specific scan (so the UI can show "why" a
product scored the way it did, ingredient by ingredient).
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class IngredientProfile(Base, RecordMixin):
    """Canonical, queryable ingredient reference data. Seeded from
    dermatology literature at deploy time (see services/product_service.py
    seed routine) and extendable - this is reference data the analysis
    pipeline reads, not a hardcoded branch in the analysis function."""

    __tablename__ = "ingredient_profiles"

    name: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    comedogenic_rating: Mapped[float | None] = mapped_column(Float, nullable=True)   # 0-5 scale, standard cosmetic literature scale
    irritant_risk: Mapped[str | None] = mapped_column(String(16), nullable=True)      # low|moderate|high
    hormonal_disruption_risk: Mapped[str | None] = mapped_column(String(16), nullable=True)
    occlusive_rating: Mapped[str | None] = mapped_column(String(16), nullable=True)
    barrier_support: Mapped[str | None] = mapped_column(String(16), nullable=True)    # supportive|neutral|disruptive
    mechanism_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_source_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)


class ProductScan(Base, RecordMixin):
    __tablename__ = "product_scans"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_method: Mapped[str] = mapped_column(String(16), nullable=False)  # manual|photo|label_ocr
    image_s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_ingredient_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    overall_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    comedogenic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    irritation_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    barrier_support_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    acne_trigger_likelihood: Mapped[float | None] = mapped_column(Float, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    in_routine: Mapped[bool] = mapped_column(Boolean, default=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductIngredientResult(Base, RecordMixin):
    """One row per ingredient identified within a specific ProductScan, with
    that ingredient's contribution to the overall verdict."""

    __tablename__ = "product_ingredients"

    product_scan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("product_scans.id", ondelete="CASCADE"), nullable=False)
    ingredient_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ingredient_profiles.id", ondelete="SET NULL"), nullable=True)
    matched_text: Mapped[str] = mapped_column(String(200), nullable=False)
    position_in_list: Mapped[int | None] = mapped_column(Integer, nullable=True)  # ingredient order signals concentration
    risk_contribution: Mapped[dict] = mapped_column(JSONB, default=dict)
