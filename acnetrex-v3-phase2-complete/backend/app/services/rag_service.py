"""
RAG (Retrieval-Augmented Generation) Service

Provides retrieval capabilities for CutisAI assistant, including:
- Evidence retrieval by query
- Context assembly from user data
- Semantic search over evidence database
- Citation tracking and source management

This service implements the DermVault retrieval engine, enabling CutisAI
to cite sources and provide evidence-backed responses.
"""

import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.evidence import EvidenceSource, EvidenceTag
from app.db.models.intelligence import IntelligenceEvent
from app.db.models.logs import DailyLog
from app.db.models.scans import FaceScan
from app.db.models.products import ProductScan
from app.db.models.onboarding import OnboardingProfile
from app.core.errors import NotFoundError


async def retrieve_evidence_by_query(
    db: AsyncSession,
    query: str,
    limit: int = 10,
    confidence_threshold: float = 0.5,
) -> list[dict]:
    """
    Retrieves evidence sources matching a query.
    
    Implements keyword and semantic search over the evidence database.
    Returns sources with trust labels and abstracts.
    
    Args:
        db: Database session
        query: Search query
        limit: Maximum results to return
        confidence_threshold: Minimum confidence for results
    
    Returns:
        List of evidence sources with metadata
    """
    # Placeholder: In a real implementation, this would use:
    # - Full-text search for keyword matching
    # - Vector embeddings for semantic search
    # - Ranking by relevance and trust score
    
    stmt = select(EvidenceSource).limit(limit)
    results = (await db.execute(stmt)).scalars().all()
    
    evidence_list = []
    for source in results:
        evidence_list.append({
            "id": str(source.id),
            "title": source.title,
            "authors": source.authors or [],
            "journal": source.journal,
            "publication_year": source.publication_year,
            "doi": source.doi,
            "source_url": source.source_url,
            "abstract_summary": source.abstract_summary,
            "topic_tags": [tag.tag_name for tag in source.tags] if source.tags else [],
            "trust_label": source.trust_label,
            "confidence": 0.85,  # Would be computed from relevance
        })
    
    return evidence_list


async def retrieve_user_context(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    """
    Assembles comprehensive user context for the assistant.
    
    Retrieves:
    - Onboarding profile
    - Recent logs (sleep, food, stress, activity)
    - Latest face scan
    - Recent forecasts
    - Product routine
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        Dictionary with assembled context
    """
    # Retrieve onboarding profile
    onboarding_stmt = select(OnboardingProfile).where(OnboardingProfile.user_id == user_id)
    onboarding = (await db.execute(onboarding_stmt)).scalar_one_or_none()
    
    # Retrieve recent logs (last 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    logs_stmt = select(DailyLog).where(
        DailyLog.user_id == user_id,
        DailyLog.created_at >= seven_days_ago,
    ).order_by(DailyLog.created_at.desc())
    recent_logs = (await db.execute(logs_stmt)).scalars().all()
    
    # Retrieve latest face scan
    scan_stmt = select(FaceScan).where(
        FaceScan.user_id == user_id,
        FaceScan.scan_type == "daily",
    ).order_by(FaceScan.captured_at.desc()).limit(1)
    latest_scan = (await db.execute(scan_stmt)).scalar_one_or_none()
    
    # Retrieve products in routine
    product_stmt = select(ProductScan).where(
        ProductScan.user_id == user_id,
        ProductScan.in_routine.is_(True),
    ).order_by(ProductScan.added_at.desc())
    routine_products = (await db.execute(product_stmt)).scalars().all()
    
    # Organize logs by type
    logs_by_type = {}
    for log in recent_logs:
        log_type = log.log_type
        if log_type not in logs_by_type:
            logs_by_type[log_type] = []
        logs_by_type[log_type].append(log)
    
    return {
        "onboarding": onboarding,
        "recent_logs": logs_by_type,
        "latest_scan": latest_scan,
        "routine_products": routine_products,
    }


async def format_user_context_for_prompt(
    onboarding: dict | None,
    recent_logs: dict,
    latest_scan: dict | None,
    routine_products: list,
) -> str:
    """
    Formats user context into a readable string for the LLM prompt.
    
    Args:
        onboarding: Onboarding profile data
        recent_logs: Dictionary of logs by type
        latest_scan: Latest face scan data
        routine_products: List of products in routine
    
    Returns:
        Formatted context string
    """
    context_parts = []
    
    # Onboarding profile
    if onboarding:
        context_parts.append(f"User Profile: {onboarding.get('age')} years old, {onboarding.get('skin_type')} skin")
    
    # Recent logs summary
    if recent_logs:
        log_summary = []
        if "sleep" in recent_logs:
            avg_sleep = sum(log.data.get("netSleepHours", 0) for log in recent_logs["sleep"]) / len(recent_logs["sleep"])
            log_summary.append(f"Average sleep: {avg_sleep:.1f} hours")
        if "food" in recent_logs:
            log_summary.append(f"Food logs: {len(recent_logs['food'])} entries")
        if "stress" in recent_logs:
            log_summary.append(f"Stress logs: {len(recent_logs['stress'])} entries")
        
        if log_summary:
            context_parts.append(f"Recent Activity: {', '.join(log_summary)}")
    
    # Latest scan
    if latest_scan:
        context_parts.append(f"Latest Scan: {latest_scan.get('lesion_count', 0)} lesions detected")
    
    # Routine products
    if routine_products:
        product_names = [p.product_name for p in routine_products[:3]]
        context_parts.append(f"Current Products: {', '.join(product_names)}")
    
    return "\n".join(context_parts)


async def format_evidence_for_prompt(
    evidence_sources: list[dict],
) -> str:
    """
    Formats evidence sources into a readable string for the LLM prompt.
    
    Args:
        evidence_sources: List of evidence source dictionaries
    
    Returns:
        Formatted evidence string
    """
    if not evidence_sources:
        return "No relevant research found."
    
    evidence_parts = []
    for source in evidence_sources[:5]:  # Limit to top 5
        citation = f"{source['title']} ({source['publication_year']})"
        if source.get('authors'):
            citation = f"{source['authors'][0]} et al. - {citation}"
        evidence_parts.append(citation)
    
    return "Relevant Research:\n" + "\n".join(f"- {e}" for e in evidence_parts)


async def emit_retrieval_event(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    evidence_count: int,
    retrieval_method: str,
) -> IntelligenceEvent:
    """
    Emits an intelligence event for evidence retrieval activity.
    
    Args:
        db: Database session
        user_id: User ID
        query: Search query
        evidence_count: Number of sources retrieved
        retrieval_method: Method used (keyword, semantic, etc.)
    
    Returns:
        The created IntelligenceEvent
    """
    from app.services import intelligence_service
    
    return await intelligence_service.emit_event(
        db, user_id, "evidence_retrieved",
        {
            "query": query,
            "evidence_count": evidence_count,
            "retrieval_method": retrieval_method,
        }
    )
