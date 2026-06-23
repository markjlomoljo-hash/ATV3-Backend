"""
CutisAI conversation routes - real implementation backed by
assistant_service.py (Anthropic API + RAG context + self-check pass).
Requires ANTHROPIC_API_KEY in .env. When the key is absent, the endpoint
returns a 501 with a clear message rather than a fabricated response.
"""
import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession
from app.services import assistant_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


class NewConversationRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


def _conv_out(c) -> dict:
    return {
        "id": str(c.id),
        "title": c.title,
        "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
        "created_at": c.created_at.isoformat(),
    }


def _msg_out(m) -> dict:
    return {
        "id": str(m.id),
        "role": m.role,
        "content": m.content,
        "confidence": m.confidence,
        "evidence_source_ids": [str(e) for e in (m.evidence_source_ids or [])],
        "context_used": m.context_used,
        "self_check_passed": m.self_check_passed,
        "escalation_flag": m.escalation_flag,
        "model_version": m.model_version,
        "created_at": m.created_at.isoformat(),
    }


@router.post("/conversations")
async def create_conversation(
    payload: NewConversationRequest, db: DbSession, current_user: CurrentUser
) -> dict:
    conv = await assistant_service.create_conversation(db, current_user.id, payload.title)
    return _conv_out(conv)


@router.get("/conversations")
async def list_conversations(db: DbSession, current_user: CurrentUser) -> list[dict]:
    rows = await assistant_service.list_conversations(db, current_user.id)
    return [_conv_out(r) for r in rows]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> dict:
    conv = await assistant_service.get_conversation(db, current_user.id, conversation_id)
    messages = await assistant_service.get_messages(db, conversation_id)
    return {**_conv_out(conv), "messages": [_msg_out(m) for m in messages]}


@router.post("/conversations/{conversation_id}/messages")
async def post_message(
    conversation_id: uuid.UUID,
    payload: MessageRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    msg = await assistant_service.post_message(db, current_user.id, conversation_id, payload.content)
    return _msg_out(msg)
