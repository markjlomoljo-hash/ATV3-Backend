"""
Scan routes. Image upload is real (stored to S3 when configured, noted as
consent-gated). Analysis scores are stored as "pending_analysis" until
ml/face_pipeline.py is wired in - the route returns the real pending scan
record rather than fabricated ML scores.
"""
import uuid

from fastapi import APIRouter, Form, UploadFile

from app.api.deps import CurrentUser, DbSession
from app.services import scan_service

router = APIRouter(prefix="/scans", tags=["scans"])

MAX_IMAGE_BYTES = 12 * 1024 * 1024  # 12 MB


def _scan_out(s) -> dict:
    return {
        "id": str(s.id),
        "scan_type": s.scan_type,
        "captured_at": s.captured_at.isoformat(),
        "overall_condition": s.overall_condition,
        "lesion_count": s.lesion_count,
        "redness_score": s.redness_score,
        "oiliness_score": s.oiliness_score,
        "dryness_score": s.dryness_score,
        "quality_score": s.quality_score,
        "confidence_score": s.confidence_score,
        "validation_status": s.validation_status,
        "model_version": s.model_version,
        "image_stored": s.image_s3_key is not None,
        "image_consent": s.image_consent,
        "zones": s.zones,
        "lesions": s.lesions,
        "source": s.source,
    }


@router.post("")
async def create_scan(
    db: DbSession,
    current_user: CurrentUser,
    scan_type: str = Form(default="daily"),
    image_consent: bool = Form(default=False),
    image: UploadFile | None = None,
) -> dict:
    image_bytes = b""
    if image is not None:
        image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
        if len(image_bytes) > MAX_IMAGE_BYTES:
            from fastapi import HTTPException
            raise HTTPException(status_code=413, detail="Image exceeds 12 MB limit.")
    scan = await scan_service.create_scan(db, current_user.id, scan_type, image_bytes, image_consent)
    return _scan_out(scan)


@router.get("")
async def list_scans(db: DbSession, current_user: CurrentUser) -> list[dict]:
    rows = await scan_service.list_scans(db, current_user.id)
    return [_scan_out(r) for r in rows]


@router.get("/{scan_id}")
async def get_scan(scan_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> dict:
    scan = await scan_service.get_scan(db, current_user.id, scan_id)
    return _scan_out(scan)


@router.post("/{scan_id}/analyze")
async def analyze_scan(scan_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> dict:
    scan = await scan_service.analyze_scan(db, current_user.id, scan_id)
    return _scan_out(scan)
