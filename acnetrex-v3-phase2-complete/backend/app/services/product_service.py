"""
Product/ingredient service - orchestrates ml/product_pipeline.py against the
real `ingredient_profiles` table (seeded by app/db/seed.py from the real v2
dictionary, extendable from there) and persists both the ProductScan verdict
and the per-ingredient breakdown.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models.products import IngredientProfile, ProductIngredientResult, ProductScan
from app.ml import product_pipeline
from app.services import intelligence_service
from app.services.validation_service import validate_product_analysis


async def _load_ingredient_profiles(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(IngredientProfile))).scalars().all()
    return [
        {"id": str(r.id), "name": r.name, "aliases": r.aliases, "comedogenic_rating": r.comedogenic_rating, "irritant_risk": r.irritant_risk, "barrier_support": r.barrier_support}
        for r in rows
    ]


async def analyze_product(
    db: AsyncSession, user_id: uuid.UUID, product_name: str, brand: str | None, category: str | None,
    input_method: str, raw_ingredient_text: str, image_s3_key: str | None = None,
) -> ProductScan:
    profiles = await _load_ingredient_profiles(db)
    matched = product_pipeline.match_ingredients(raw_ingredient_text, profiles)
    score = product_pipeline.score_product(matched)
    validation_status = validate_product_analysis(len(matched))

    scan = ProductScan(
        user_id=user_id, product_name=product_name, brand=brand, category=category,
        input_method=input_method, image_s3_key=image_s3_key, raw_ingredient_text=raw_ingredient_text,
        overall_risk=score["overall_risk"], comedogenic_score=score["comedogenic_score"],
        irritation_risk=score["irritation_risk"], barrier_support_score=score["barrier_support_score"],
        acne_trigger_likelihood=score["acne_trigger_likelihood"], conclusion=score["conclusion"],
        confidence_level={"high": 0.85, "moderate": 0.6, "low": 0.3}[score["confidence_level"]],
        model_version="product_pipeline_v3.0.0", in_routine=False, added_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    await db.flush()

    for i, m in enumerate(matched):
        db.add(ProductIngredientResult(
            product_scan_id=scan.id,
            ingredient_profile_id=uuid.UUID(m.profile_id) if m.profile_id else None,
            matched_text=m.name, position_in_list=i,
            risk_contribution={
                "comedogenic_rating": m.comedogenic_rating, "irritant_risk": m.irritant_risk,
                "barrier_support": m.barrier_support, "acne_association": m.acne_association,
            },
        ))
    await db.flush()

    await intelligence_service.emit_event(db, user_id, "product_analyzed", {
        "product_name": product_name, "overall_risk": score["overall_risk"], "validation_status": validation_status,
        "ingredients_matched": len(matched),
    })
    return scan


async def list_products(db: AsyncSession, user_id: uuid.UUID) -> list[ProductScan]:
    stmt = select(ProductScan).where(ProductScan.user_id == user_id).order_by(ProductScan.added_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def patch_product(db: AsyncSession, user_id: uuid.UUID, product_id: uuid.UUID, in_routine: bool | None) -> ProductScan:
    scan = (await db.execute(select(ProductScan).where(ProductScan.id == product_id, ProductScan.user_id == user_id))).scalar_one_or_none()
    if scan is None:
        raise NotFoundError("Product scan not found.")
    if in_routine is not None:
        scan.in_routine = in_routine
    await db.flush()
    return scan
