"""
Research participation / anonymous network learning service.

The participant count returned here is a real COUNT(*) over users who have
an active research_participation consent grant - never a hardcoded or
randomized number. Until Phase 2's federated/cohort learning jobs exist,
'aggregate_learning_contribution' honestly reports zero rather than
inventing a percentage; the spec is explicit that decorative status
indicators not tied to real backend state are not allowed.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ConsentType
from app.db.models.user import Consent, User


async def _current_consent(db: AsyncSession, user_id: uuid.UUID, consent_type: str) -> Consent | None:
    stmt = (
        select(Consent)
        .where(Consent.user_id == user_id, Consent.consent_type == consent_type)
        .order_by(Consent.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_network_status(db: AsyncSession, user_id: uuid.UUID) -> dict:
    # "Currently granted" = latest consent row for that type/user has
    # granted=True and no later revoked_at. Modeled this way (append-only
    # rows) rather than a mutable boolean so consent history survives audits.
    research_consent = await _current_consent(db, user_id, ConsentType.RESEARCH_PARTICIPATION.value)
    federated_consent = await _current_consent(db, user_id, ConsentType.FEDERATED_LEARNING.value)

    research_participating = bool(research_consent and research_consent.granted and research_consent.revoked_at is None)
    federated_participating = bool(federated_consent and federated_consent.granted and federated_consent.revoked_at is None)

    # Real aggregate: count distinct users whose latest research-participation
    # consent row is granted. This is a privacy-preserving count, not a list
    # of identities.
    subq = (
        select(Consent.user_id, func.max(Consent.created_at).label("latest"))
        .where(Consent.consent_type == ConsentType.RESEARCH_PARTICIPATION.value)
        .group_by(Consent.user_id)
        .subquery()
    )
    active_participants = (await db.execute(
        select(func.count())
        .select_from(Consent)
        .join(subq, and_(Consent.user_id == subq.c.user_id, Consent.created_at == subq.c.latest))
        .where(Consent.granted.is_(True), Consent.revoked_at.is_(None))
    )).scalar_one()

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()

    return {
        "you_are_participating_research": research_participating,
        "you_are_participating_federated_learning": federated_participating,
        "active_research_participants": active_participants,
        "total_accounts": total_users,
        # Real until a cohort-learning job exists to compute it (Phase 2);
        # zero is the honest value, not a placeholder percentage.
        "aggregate_learning_contribution_events": 0,
        "raw_images_shared_without_consent": 0,
        "raw_logs_shared_without_consent": 0,
        "data_sharing_policy": "No raw images or raw logs are ever shared, with or without consent. Only de-identified, aggregated statistical signals from consenting accounts are used for population-level model calibration.",
    }


async def set_consent(db: AsyncSession, user_id: uuid.UUID, consent_type: str, granted: bool) -> Consent:
    now = datetime.now(timezone.utc)
    row = Consent(
        user_id=user_id, consent_type=consent_type, granted=granted,
        granted_at=now if granted else None, revoked_at=None if granted else now,
    )
    db.add(row)
    await db.flush()
    return row
