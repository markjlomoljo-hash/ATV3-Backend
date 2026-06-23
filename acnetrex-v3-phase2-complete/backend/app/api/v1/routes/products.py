"""Product/ingredient routes - real implementation via product_service.py,
which queries the live ingredient_profiles table instead of v2's hardcoded
dictionary."""
import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.products import ProductAnalyzeRequest, ProductPatchRequest
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])


def _scan_out(s) -> dict:
    return {
        "id": str(s.id), "product_name": s.product_name, "brand": s.brand, "category": s.category,
        "input_method": s.input_method, "overall_risk": s.overall_risk, "comedogenic_score": s.comedogenic_score,
        "irritation_risk": s.irritation_risk, "barrier_support_score": s.barrier_support_score,
        "acne_trigger_likelihood": s.acne_trigger_likelihood, "conclusion": s.conclusion,
        "confidence_level": s.confidence_level, "in_routine": s.in_routine, "added_at": s.added_at.isoformat(),
        "source": s.source,
    }


@router.post("/analyze")
async def analyze_product(payload: ProductAnalyzeRequest, db: DbSession, current_user: CurrentUser) -> dict:
    scan = await product_service.analyze_product(
        db, current_user.id, payload.product_name, payload.brand, payload.category,
        payload.input_method, payload.raw_ingredient_text,
    )
    return _scan_out(scan)


@router.post("")
async def save_product(payload: ProductAnalyzeRequest, db: DbSession, current_user: CurrentUser) -> dict:
    # Same as /analyze - "save" in the product UI means "analyze and persist",
    # there's no separate unanalyzed-save state in this data model.
    scan = await product_service.analyze_product(
        db, current_user.id, payload.product_name, payload.brand, payload.category,
        payload.input_method, payload.raw_ingredient_text,
    )
    return _scan_out(scan)


@router.get("")
async def list_products(db: DbSession, current_user: CurrentUser) -> list[dict]:
    rows = await product_service.list_products(db, current_user.id)
    return [_scan_out(r) for r in rows]


@router.patch("/{product_id}")
async def patch_product(product_id: uuid.UUID, payload: ProductPatchRequest, db: DbSession, current_user: CurrentUser) -> dict:
    scan = await product_service.patch_product(db, current_user.id, product_id, payload.in_routine)
    return _scan_out(scan)
