"""
DermVault evidence model.

Replaces v2's hardcoded `gb` evidence array (a fixed list of references baked
into the JS bundle) with a real, queryable, semantically-searchable table.
The `embedding` column is a pgvector column searched via cosine distance in
evidence_service / rag_service - this is what makes retrieval real instead
of a static lookup table. Full text is generally not stored (publisher
licensing); abstract_summary + source_url is what the spec calls for when
"full text cannot be stored": title, authors, journal, year, abstract/summary,
trustworthy source link.
"""
from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base, RecordMixin


class EvidenceSource(Base, RecordMixin):
    __tablename__ = "evidence_sources"

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    authors: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    journal: Mapped[str | None] = mapped_column(String(256), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    pubmed_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    abstract_summary: Mapped[str] = mapped_column(Text, nullable=False)
    topic_tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    trust_label: Mapped[str] = mapped_column(String(64), default="peer_reviewed")  # peer_reviewed|systematic_review|preprint|clinical_guideline
    retrieved_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # pgvector embedding for semantic search over title+abstract. Dimension
    # is configurable because different embedding providers/models use
    # different sizes - keep this in lockstep with whatever
    # rag_service.embed() actually calls.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.EMBEDDING_DIM), nullable=True)
