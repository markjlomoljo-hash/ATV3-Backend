"""
Export service. JSON export is fully real now - it's a direct, complete dump
of the user's actual stored records (profile, onboarding, logs, scans,
products), not a sample report. PDF formatting (typography, charts, clinical
layout) is Phase 2 polish on top of the same real data this function
already assembles.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.logs import DailyLog
from app.db.models.onboarding import OnboardingProfile
from app.db.models.products import ProductScan
from app.db.models.scans import FaceScan
from app.db.models.user import User


async def build_export(db: AsyncSession, user_id: uuid.UUID) -> dict:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
    onboarding = (await db.execute(select(OnboardingProfile).where(OnboardingProfile.user_id == user_id))).scalar_one_or_none()
    logs = (await db.execute(select(DailyLog).where(DailyLog.user_id == user_id).order_by(DailyLog.log_date.desc()))).scalars().all()
    scans = (await db.execute(select(FaceScan).where(FaceScan.user_id == user_id).order_by(FaceScan.captured_at.desc()))).scalars().all()
    products = (await db.execute(select(ProductScan).where(ProductScan.user_id == user_id).order_by(ProductScan.added_at.desc()))).scalars().all()

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "app_version": user.app_version,
        "profile": {"email": user.email, "display_name": user.display_name, "account_created_at": user.created_at.isoformat()},
        "onboarding": {
            "skin_type": onboarding.skin_type if onboarding else None,
            "acne_type": onboarding.acne_type if onboarding else None,
            "acne_severity": onboarding.acne_severity if onboarding else None,
            "skin_goals": onboarding.skin_goals if onboarding else [],
            "health_conditions": onboarding.health_conditions if onboarding else [],
            "maintenance_medications": onboarding.maintenance_medications if onboarding else [],
        } if onboarding else None,
        "daily_logs": [
            {"date": l.log_date.isoformat(), "type": l.log_type, "data": l.data, "source": l.source}
            for l in logs
        ],
        "face_scans": [
            {
                "captured_at": s.captured_at.isoformat(), "scan_type": s.scan_type,
                "overall_condition": s.overall_condition, "lesion_count": s.lesion_count,
                "confidence_score": s.confidence_score, "validation_status": s.validation_status,
                "model_version": s.model_version, "source": s.source,
            }
            for s in scans
        ],
        "product_scans": [
            {
                "product_name": p.product_name, "brand": p.brand, "overall_risk": p.overall_risk,
                "conclusion": p.conclusion, "confidence_level": p.confidence_level, "source": p.source,
            }
            for p in products
        ],
    }
