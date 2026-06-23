"""
Scan service.

Two scan flows per the spec:
1. Onboarding baseline scan: live-camera capture, stored as BASELINE type,
   triggers onboarding_service.attach_baseline_scan().
2. Daily FaceAtlas scan: 5-photo upload flow (front, left45, right45,
   forehead, chin), stored as DAILY type.

Image analysis pipeline (ml/face_pipeline.py) is Phase 2 scope. The
infrastructure is fully in place here: images go to S3 (if configured),
quality_score / confidence_score / validation_status columns exist on
FaceScan, and the validation_service thresholds will gate the result
exactly the same way once the ML pipeline produces real scores. Before
face_pipeline.py is wired in, scans are stored with
validation_status="pending_analysis" instead of returning a fabricated
confidence score.
"""
import io
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import NotFoundError
from app.db.models.scans import FaceScan
from app.services import intelligence_service, onboarding_service


async def _upload_to_s3(file_bytes: bytes, key: str) -> str | None:
    """Upload image bytes to S3-compatible storage. Returns the S3 key on
    success, None when S3 is not configured (dev mode - image discarded)."""
    if not all([settings.S3_ACCESS_KEY_ID, settings.S3_SECRET_ACCESS_KEY, settings.S3_BUCKET]):
        return None
    try:
        import boto3
        client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )
        client.upload_fileobj(io.BytesIO(file_bytes), settings.S3_BUCKET, key, ExtraArgs={"ContentType": "image/jpeg"})
        return key
    except Exception:
        return None


async def create_scan(
    db: AsyncSession,
    user_id: uuid.UUID,
    scan_type: str,
    image_bytes: bytes,
    image_consent: bool,
    zones_override: dict | None = None,
) -> FaceScan:
    """Create a FaceScan record. Image is stored to S3 if the user
    consented and S3 is configured. Analysis scores are 0 with
    validation_status='pending_analysis' until ml/face_pipeline.py is
    wired in via analyze_scan()."""
    now = datetime.now(timezone.utc)
    s3_key = None
    if image_consent and image_bytes:
        s3_key = await _upload_to_s3(image_bytes, f"scans/{user_id}/{now.isoformat()}_{scan_type}.jpg")

    scan = FaceScan(
        user_id=user_id,
        scan_type=scan_type,
        captured_at=now,
        image_s3_key=s3_key,
        image_consent=image_consent,
        zones=zones_override or {},
        lesions={},
        lesion_count=0,
        quality_score=0.0,
        is_valid_face=False,
        confidence_score=0.0,
        validation_status="pending_analysis",
        model_version="face_pipeline_v3.0.0-phase2-pending",
    )
    db.add(scan)
    await db.flush()

    if scan_type == "baseline":
        await onboarding_service.attach_baseline_scan(db, user_id, scan.id)

    await intelligence_service.emit_event(
        db, user_id, "scan_created",
        {"scan_type": scan_type, "image_stored": s3_key is not None, "image_consent": image_consent},
    )
    return scan


async def list_scans(db: AsyncSession, user_id: uuid.UUID) -> list[FaceScan]:
    stmt = select(FaceScan).where(FaceScan.user_id == user_id).order_by(FaceScan.captured_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def get_scan(db: AsyncSession, user_id: uuid.UUID, scan_id: uuid.UUID) -> FaceScan:
    scan = (await db.execute(
        select(FaceScan).where(FaceScan.id == scan_id, FaceScan.user_id == user_id)
    )).scalar_one_or_none()
    if scan is None:
        raise NotFoundError("Scan not found.")
    return scan


async def analyze_scan(db: AsyncSession, user_id: uuid.UUID, scan_id: uuid.UUID) -> FaceScan:
    """Placeholder that calls ml/face_pipeline.py once it exists. Right now
    it updates the scan record to 'pending_analysis' clearly rather than
    returning fake ML scores. Phase 2 replaces this body with a real
    inference call."""
    scan = await get_scan(db, user_id, scan_id)
    scan.validation_status = "pending_analysis"
    await db.flush()
    await intelligence_service.emit_event(db, user_id, "scan_analysis_requested", {"scan_id": str(scan_id)})
    return scan
