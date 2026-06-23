"""
Audit Service - Enhanced Audit Logging for Health-Data Entities

Every write (create or update) to a health-data entity must produce an
AuditLog record immediately after the operation succeeds. This service
provides centralized audit logging to enforce the Zero-Fabrication Contract
requirement that all meaningful actions are traceable.

AuditLog records are append-only and store field names (not values) to
protect user privacy while maintaining a complete audit trail.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import AuditLog
from app.core.constants import CURRENT_SOURCE_TAG


async def emit_health_data_audit(
    db: AsyncSession,
    user_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    operation: str,
    changed_fields: list[str] | None = None,
    source: str = CURRENT_SOURCE_TAG,
    app_version: str = "3.0.0",
) -> AuditLog:
    """
    Emit an audit log record for a health-data entity write operation.

    Args:
        db: AsyncSession for database operations
        user_id: ID of the user who owns the entity
        entity_type: Type of entity (e.g., "FaceScan", "DailyLog", "ProductScan")
        entity_id: ID of the entity being written
        operation: Type of operation ("create" or "update")
        changed_fields: List of field names that were changed (not values)
        source: Source of the operation (default: "app_v3")
        app_version: Application version (default: "3.0.0")

    Returns:
        The created AuditLog record
    """
    audit_log = AuditLog(
        user_id=user_id,
        event_type=f"{entity_type}_{operation}",
        payload={
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "operation": operation,
            "changed_fields": changed_fields or [],
            "source": source,
            "app_version": app_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(audit_log)
    await db.flush()
    return audit_log


async def emit_auth_audit(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    event_type: str,
    payload: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Emit an audit log record for authentication-related events.

    Args:
        db: AsyncSession for database operations
        user_id: ID of the user (may be None for pre-auth events)
        event_type: Type of event (e.g., "login", "logout", "password_reset")
        payload: Additional event data
        ip_address: IP address of the requester

    Returns:
        The created AuditLog record
    """
    audit_log = AuditLog(
        user_id=user_id,
        event_type=event_type,
        payload=payload or {},
        ip_address=ip_address,
    )
    db.add(audit_log)
    await db.flush()
    return audit_log


async def emit_consent_audit(
    db: AsyncSession,
    user_id: uuid.UUID,
    consent_type: str,
    granted: bool,
    policy_version: str = "1",
) -> AuditLog:
    """
    Emit an audit log record for consent-related events.

    Args:
        db: AsyncSession for database operations
        user_id: ID of the user
        consent_type: Type of consent (e.g., "research_participation")
        granted: Whether consent was granted or revoked
        policy_version: Version of the policy

    Returns:
        The created AuditLog record
    """
    audit_log = AuditLog(
        user_id=user_id,
        event_type=f"consent_{consent_type}",
        payload={
            "consent_type": consent_type,
            "granted": granted,
            "policy_version": policy_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(audit_log)
    await db.flush()
    return audit_log


async def emit_data_export_audit(
    db: AsyncSession,
    user_id: uuid.UUID,
    export_format: str,
    entity_count: int,
) -> AuditLog:
    """
    Emit an audit log record for data export events.

    Args:
        db: AsyncSession for database operations
        user_id: ID of the user
        export_format: Format of the export (e.g., "json", "pdf")
        entity_count: Number of entities included in the export

    Returns:
        The created AuditLog record
    """
    audit_log = AuditLog(
        user_id=user_id,
        event_type="data_export",
        payload={
            "export_format": export_format,
            "entity_count": entity_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(audit_log)
    await db.flush()
    return audit_log
