"""
CutisAI conversation models.

Replaces v2's locally-persisted `acnetrex_ai_v2` keyword-template chat with
real conversation rows the backend assistant_service writes to after each
turn. Every assistant message stores which evidence it cited and the
self-check pass result, so "explain uncertainty honestly" and "cite relevant
research" are auditable, not just prompted-for.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin


class AssistantConversation(Base, RecordMixin):
    __tablename__ = "assistant_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AssistantMessage(Base, RecordMixin):
    __tablename__ = "assistant_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user|assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Only populated for role=assistant ---
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_source_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    context_used: Mapped[dict] = mapped_column(JSONB, default=dict)        # which tools/context were pulled in (CHI, logs, forecast, etc.)
    self_check_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    self_check_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    escalation_flag: Mapped[bool] = mapped_column(Boolean, default=False)            # set true when guardrails route to "see a dermatologist"
