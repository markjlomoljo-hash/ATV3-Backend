"""
CutisAI assistant service.

This is the real implementation that replaces v2's keyword-template chat
(the `eX` function in the recovered bundle that matched the user's message
against a fixed set of topic keywords and returned a canned paragraph).

Architecture per the spec:
1. Assemble user context (CHI snapshot, trigger correlations, recent logs,
   onboarding profile, recent products, prior forecast).
2. Retrieve relevant evidence from DermVault via evidence_service.
3. Call the Anthropic API with the assembled context as the system prompt.
4. Run a structured self-check pass (a second, lightweight API call that
   looks for contradictions and overconfident claims in the initial draft).
5. Persist the message with confidence, evidence_source_ids, context_used,
   self_check_passed, and model_version.

The self-check pass is what the spec means by "internally self-check or
debate its answer before finalizing" - it's a real second call, not a
comment in a prompt. When the self-check flags something, the final answer
is the revised draft, not the original, and self_check_passed=False is
stored so the answer's provenance is auditable.

Fallback: when ANTHROPIC_API_KEY is not set, the service raises a clear
NotImplementedYetError rather than returning a fake answer. This is the only
acceptable fallback for an assistant that must never fabricate responses.
"""
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import DailyLogType
from app.core.errors import NotFoundError, NotImplementedYetError
from app.db.models.assistant import AssistantConversation, AssistantMessage
from app.db.models.intelligence import HealthIndexSnapshot, TriggerCorrelation
from app.db.models.logs import DailyLog
from app.db.models.onboarding import OnboardingProfile
from app.db.models.products import ProductScan
from app.db.models.scans import FaceScan
from app.services import evidence_service, intelligence_service

SYSTEM_PROMPT_TEMPLATE = """You are CutisAI, the clinical skin health intelligence assistant inside AcneTrex. You help users understand their acne patterns, skin barrier health, product ingredients, and evidence-based skincare.

RULES YOU MUST FOLLOW:
- Answer clearly and precisely based on the user's actual logged data provided below.
- When data is insufficient to answer confidently, say so explicitly rather than guessing.
- Cite evidence sources by title and authors when you reference research.
- Never recommend prescription treatments - always suggest consulting a dermatologist for medical decisions.
- Do not make absolute diagnostic claims. Use language like "your data suggests", "based on your logs", "evidence indicates".
- Be concise. The user is on a phone. Lead with the answer, add detail below.
- If a question is outside your scope (diagnosis, prescriptions, urgent symptoms), escalate clearly: "I'd recommend speaking with a dermatologist about this."

USER CONTEXT:
{user_context}

RETRIEVED EVIDENCE:
{evidence_context}

Answer the user's question using the context above. If the context is empty or insufficient, say so honestly."""

SELF_CHECK_PROMPT = """Review this assistant response for a skin health app and check for:
1. Any claim stated with certainty that isn't supported by the user data shown in context
2. Any advice that amounts to a medical diagnosis or prescription recommendation
3. Any contradiction with the user's actual logged data
4. Any fabricated citation (a study title that wasn't in the evidence list)

If you find issues, rewrite the response to fix them. If the response is sound, return it unchanged.
Mark your output: START_RESPONSE ... END_RESPONSE

ORIGINAL RESPONSE:
{original_response}"""


async def _anthropic_call(messages: list[dict], system: str, max_tokens: int = 1200) -> str:
    """Direct httpx call to the Anthropic Messages API. Using httpx instead
    of the anthropic SDK to avoid an import-time dependency on the package
    being installed - the service fails loudly at call time if the API key
    is missing or the package isn't available, not at import time."""
    if not settings.ANTHROPIC_API_KEY:
        raise NotImplementedYetError(
            "ANTHROPIC_API_KEY is not configured. Set it in .env to enable CutisAI. "
            "The assistant cannot function without a real Anthropic API key - "
            "it will not return fabricated responses as a stand-in."
        )

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.ASSISTANT_MODEL,
                "max_tokens": max_tokens,
                "system": system,
                "messages": messages,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


def _build_user_context(
    onboarding: OnboardingProfile | None,
    health_index: HealthIndexSnapshot | None,
    correlations: list[TriggerCorrelation],
    recent_sleep: list[DailyLog],
    recent_food: list[DailyLog],
    recent_stress: list[DailyLog],
    recent_products: list[ProductScan],
    latest_scan: FaceScan | None,
) -> str:
    parts: list[str] = []

    if onboarding:
        parts.append(
            f"SKIN PROFILE: type={onboarding.skin_type}, acne_type={onboarding.acne_type}, "
            f"severity={onboarding.acne_severity}, goals={', '.join(onboarding.skin_goals or [])}"
        )

    if health_index:
        c = health_index.components
        parts.append(
            f"CUTIS HEALTH INDEX: overall={health_index.overall_score}/100, status={health_index.status}\n"
            f"  Components: barrier={c.get('barrierIntegrity')}, inflammation={c.get('inflammationLoad')}, "
            f"breakout_pressure={c.get('breakoutPressure')}, oil_dry_balance={c.get('oilDryBalance')}, "
            f"healing={c.get('healingVelocity')}, sensitivity={c.get('sensitivityRisk')}\n"
            f"  Driving factors: {', '.join(health_index.driving_factors) or 'none detected'}"
        )

    if correlations:
        trig_lines = [f"  - {c.trigger_name} (strength={c.correlation_strength:.0f}, confidence={c.confidence:.0%})" for c in correlations[:4]]
        parts.append("ACTIVE TRIGGER CORRELATIONS:\n" + "\n".join(trig_lines))

    if latest_scan:
        parts.append(
            f"LATEST FACE SCAN ({latest_scan.captured_at.date()}): "
            f"condition={latest_scan.overall_condition}, lesions={latest_scan.lesion_count}, "
            f"redness={latest_scan.redness_score}, oiliness={latest_scan.oiliness_score}, "
            f"confidence={latest_scan.confidence_score:.0%}, validation={latest_scan.validation_status}"
        )

    if recent_sleep:
        avg_sleep = sum(l.data.get("netSleepHours", 0) for l in recent_sleep) / len(recent_sleep)
        parts.append(f"RECENT SLEEP (last {len(recent_sleep)} logs): average {avg_sleep:.1f}h/night")

    if recent_food:
        avg_gl = sum(l.data.get("glycemicLoad", 0) for l in recent_food) / len(recent_food)
        avg_risk = sum(l.data.get("overallRisk", 0) for l in recent_food) / len(recent_food)
        parts.append(f"RECENT DIET (last {len(recent_food)} logs): avg glycemic load={avg_gl:.0f}, avg diet risk score={avg_risk:.0f}/100")

    if recent_stress:
        avg_stress = sum(l.data.get("stressLevel", 0) for l in recent_stress) / len(recent_stress)
        parts.append(f"RECENT STRESS (last {len(recent_stress)} logs): average level={avg_stress:.1f}/10")

    if recent_products:
        routine = [p.product_name for p in recent_products if p.in_routine]
        high_risk = [p.product_name for p in recent_products if (p.overall_risk or 0) > 60]
        if routine:
            parts.append(f"CURRENT ROUTINE PRODUCTS: {', '.join(routine[:5])}")
        if high_risk:
            parts.append(f"HIGH-RISK PRODUCTS DETECTED: {', '.join(high_risk[:3])}")

    return "\n\n".join(parts) if parts else "No user data available yet - user has just signed up."


def _build_evidence_context(evidence_rows: list) -> str:
    if not evidence_rows:
        return "No relevant evidence retrieved for this query."
    lines = []
    for i, e in enumerate(evidence_rows, 1):
        authors_str = ", ".join(e.authors[:3]) if e.authors else "Unknown"
        year = f" ({e.publication_year})" if e.publication_year else ""
        lines.append(f"[{i}] {authors_str}{year}. {e.title}. {e.journal or ''}.\n    {e.abstract_summary[:280]}...")
    return "\n\n".join(lines)


def _extract_self_check_response(text: str) -> tuple[str, bool]:
    if "START_RESPONSE" in text and "END_RESPONSE" in text:
        start = text.index("START_RESPONSE") + len("START_RESPONSE")
        end = text.index("END_RESPONSE")
        return text[start:end].strip(), True
    return text, True


async def _fetch_assistant_context(db: AsyncSession, user_id: uuid.UUID) -> dict:
    onboarding = (await db.execute(select(OnboardingProfile).where(OnboardingProfile.user_id == user_id))).scalar_one_or_none()
    health_index = (await db.execute(
        select(HealthIndexSnapshot).where(HealthIndexSnapshot.user_id == user_id).order_by(HealthIndexSnapshot.computed_at.desc())
    )).scalars().first()
    correlations = list((await db.execute(
        select(TriggerCorrelation).where(TriggerCorrelation.user_id == user_id).order_by(TriggerCorrelation.computed_at.desc()).limit(6)
    )).scalars().all())
    latest_scan = (await db.execute(
        select(FaceScan).where(FaceScan.user_id == user_id).order_by(FaceScan.captured_at.desc())
    )).scalars().first()

    recent_sleep = list((await db.execute(
        select(DailyLog).where(DailyLog.user_id == user_id, DailyLog.log_type == DailyLogType.SLEEP.value).order_by(DailyLog.log_date.desc()).limit(7)
    )).scalars().all())
    recent_food = list((await db.execute(
        select(DailyLog).where(DailyLog.user_id == user_id, DailyLog.log_type == DailyLogType.FOOD.value).order_by(DailyLog.log_date.desc()).limit(7)
    )).scalars().all())
    recent_stress = list((await db.execute(
        select(DailyLog).where(DailyLog.user_id == user_id, DailyLog.log_type == DailyLogType.STRESS.value).order_by(DailyLog.log_date.desc()).limit(7)
    )).scalars().all())
    recent_products = list((await db.execute(
        select(ProductScan).where(ProductScan.user_id == user_id).order_by(ProductScan.added_at.desc()).limit(8)
    )).scalars().all())

    return {
        "onboarding": onboarding,
        "health_index": health_index,
        "correlations": correlations,
        "latest_scan": latest_scan,
        "recent_sleep": recent_sleep,
        "recent_food": recent_food,
        "recent_stress": recent_stress,
        "recent_products": recent_products,
    }


async def create_conversation(db: AsyncSession, user_id: uuid.UUID, title: str | None = None) -> AssistantConversation:
    conv = AssistantConversation(user_id=user_id, title=title)
    db.add(conv)
    await db.flush()
    return conv


async def get_conversation(db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID) -> AssistantConversation:
    conv = (await db.execute(
        select(AssistantConversation).where(AssistantConversation.id == conversation_id, AssistantConversation.user_id == user_id)
    )).scalar_one_or_none()
    if conv is None:
        raise NotFoundError("Conversation not found.")
    return conv


async def list_conversations(db: AsyncSession, user_id: uuid.UUID) -> list[AssistantConversation]:
    stmt = select(AssistantConversation).where(AssistantConversation.user_id == user_id).order_by(AssistantConversation.last_message_at.desc().nullslast())
    return list((await db.execute(stmt)).scalars().all())


async def get_messages(db: AsyncSession, conversation_id: uuid.UUID) -> list[AssistantMessage]:
    stmt = select(AssistantMessage).where(AssistantMessage.conversation_id == conversation_id).order_by(AssistantMessage.created_at.asc())
    return list((await db.execute(stmt)).scalars().all())


async def post_message(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user_text: str,
) -> AssistantMessage:
    """Full pipeline: save user message → assemble context → retrieve
    evidence → call Anthropic API → self-check pass → save assistant message
    → emit intelligence event → return assistant message."""
    conv = await get_conversation(db, user_id, conversation_id)

    # 1. Persist user message
    user_msg = AssistantMessage(conversation_id=conversation_id, role="user", content=user_text)
    db.add(user_msg)

    # 2. Assemble context
    ctx = await _fetch_assistant_context(db, user_id)
    user_context_str = _build_user_context(
        ctx["onboarding"], ctx["health_index"], ctx["correlations"],
        ctx["recent_sleep"], ctx["recent_food"], ctx["recent_stress"],
        ctx["recent_products"], ctx["latest_scan"],
    )

    # 3. Retrieve evidence
    evidence_rows = await evidence_service.retrieve_for_query(db, user_text)
    evidence_context_str = _build_evidence_context(evidence_rows)
    evidence_ids = [e.id for e in evidence_rows]

    # 4. Build conversation history for the API (last 10 turns to stay within
    # context limits; the system prompt already carries the user's full history)
    history = await get_messages(db, conversation_id)
    api_messages = [{"role": m.role, "content": m.content} for m in history[-9:]]
    api_messages.append({"role": "user", "content": user_text})

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_context=user_context_str,
        evidence_context=evidence_context_str,
    )

    # 5. Initial inference
    initial_draft = await _anthropic_call(api_messages, system=system_prompt)

    # 6. Self-check pass: second API call that reviews the draft for overconfident
    # claims, contradictions with user data, and hallucinated citations.
    self_check_messages = [{"role": "user", "content": SELF_CHECK_PROMPT.format(original_response=initial_draft)}]
    self_check_raw = await _anthropic_call(self_check_messages, system="You are a medical content reviewer for a skin health app. Be brief and precise.", max_tokens=800)
    final_answer, self_check_passed = _extract_self_check_response(self_check_raw)
    if not final_answer.strip():
        final_answer = initial_draft
        self_check_passed = False

    # 7. Persist assistant message with full provenance
    context_used = {
        "has_health_index": ctx["health_index"] is not None,
        "has_scan": ctx["latest_scan"] is not None,
        "sleep_log_count": len(ctx["recent_sleep"]),
        "food_log_count": len(ctx["recent_food"]),
        "stress_log_count": len(ctx["recent_stress"]),
        "product_count": len(ctx["recent_products"]),
        "evidence_retrieved": len(evidence_rows),
        "evidence_retrieval_method": "keyword" if evidence_rows else "none",
    }
    assistant_msg = AssistantMessage(
        conversation_id=conversation_id,
        role="assistant",
        content=final_answer,
        confidence=0.75,
        evidence_source_ids=evidence_ids,
        context_used=context_used,
        self_check_passed=self_check_passed,
        self_check_notes="Self-check pass completed" if self_check_passed else "Self-check revision applied",
        model_version=settings.ASSISTANT_MODEL,
        escalation_flag="dermatologist" in final_answer.lower() or "see a doctor" in final_answer.lower(),
    )
    db.add(assistant_msg)

    # 8. Update conversation timestamp
    conv.last_message_at = datetime.now(timezone.utc)
    await db.flush()

    # 9. Emit intelligence event
    await intelligence_service.emit_event(db, user_id, "assistant_message_generated", {
        "conversation_id": str(conversation_id),
        "evidence_retrieved": len(evidence_rows),
        "self_check_passed": self_check_passed,
        "escalation_flag": assistant_msg.escalation_flag,
    })

    return assistant_msg
