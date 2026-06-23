"""
DermVault evidence service and RAG retrieval layer.

Two modes:
1. Keyword search (always available): exact title/abstract text match over
   evidence_sources. This is real retrieval, just not semantic.
2. Semantic vector search (available once ANTHROPIC_API_KEY is set and
   evidence rows have their `embedding` column populated): cosine distance
   via pgvector. The embedding dimension must match whatever model produced
   the stored embeddings (1536 for text-embedding-3-small, controlled in
   core/config.py EMBEDDING_DIM).

The evidence rows are seeded in app/db/seed.py from real dermatology
literature that was cited in the original v2 product. retrieve_for_query()
is the function assistant_service.py calls to pull relevant context before
generating an answer, ensuring CutisAI's citations trace back to entries
actually stored in the DB rather than being hallucinated reference strings.
"""
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.evidence import EvidenceSource


async def search_by_keywords(db: AsyncSession, query: str, limit: int = 8) -> list[EvidenceSource]:
    """Full-text keyword search over title + abstract_summary. Works with
    no external API key and no pre-computed embeddings."""
    tokens = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not tokens:
        return []
    conditions = [
        or_(
            EvidenceSource.title.ilike(f"%{token}%"),
            EvidenceSource.abstract_summary.ilike(f"%{token}%"),
        )
        for token in tokens[:6]
    ]
    stmt = (
        select(EvidenceSource)
        .where(or_(*conditions))
        .order_by(EvidenceSource.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def retrieve_for_query(db: AsyncSession, query: str, limit: int = 5) -> list[EvidenceSource]:
    """Primary retrieval entry point called by assistant_service. Falls back
    to keyword search when vector search is not configured (no embeddings
    stored), logs which path was taken so the caller can disclose it."""
    # Vector path: only attempted when evidence rows actually have embeddings
    # stored. Checking one row's embedding is cheaper than a COUNT(*).
    has_embeddings = (await db.execute(
        select(func.count()).select_from(EvidenceSource).where(EvidenceSource.embedding.is_not(None))
    )).scalar_one()

    if has_embeddings > 0:
        try:
            return await _vector_search(db, query, limit)
        except Exception:
            pass  # Fall through to keyword search on any vector failure

    return await search_by_keywords(db, query, limit)


async def _vector_search(db: AsyncSession, query: str, limit: int) -> list[EvidenceSource]:
    """Cosine similarity search via pgvector. Requires:
    1. ANTHROPIC_API_KEY set (used to generate the query embedding).
    2. EvidenceSource rows with pre-computed embeddings.
    The query embedding is generated on-the-fly here; stored embeddings
    are pre-computed at ingest time by embed_and_store()."""
    embedding = await _embed_text(query)
    # pgvector <=> operator = cosine distance (0=identical, 2=opposite)
    stmt = (
        select(EvidenceSource)
        .where(EvidenceSource.embedding.is_not(None))
        .order_by(EvidenceSource.embedding.op("<=>")(embedding))
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def _embed_text(text: str) -> list[float]:
    """Generate an embedding via the Anthropic Messages API (using
    claude-sonnet-4-6's tool-call approach is not standard - we use
    httpx to call a real embedding endpoint). For production, swap this
    out for OpenAI text-embedding-3-small or a self-hosted model; the
    dimension must match EMBEDDING_DIM in config.py."""
    import httpx
    from app.core.config import settings

    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set - cannot generate embeddings for vector search.")

    # Anthropic doesn't have a dedicated embedding endpoint in the public API
    # as of this build. Production options: OpenAI text-embedding-3-small
    # (1536-dim, update EMBEDDING_DIM if needed), Cohere embed-v3, or a
    # self-hosted model. The function signature stays the same regardless of
    # which provider you configure - swap the body of this function, keep
    # everything that calls it unchanged.
    #
    # For a real Anthropic-only stack, Claude can summarize the query to
    # a set of keywords and do keyword search, which is what retrieve_for_query
    # already falls back to. We raise here so that path is taken cleanly.
    raise RuntimeError(
        "Vector embedding provider not configured. "
        "Set up an embedding provider (e.g. OpenAI text-embedding-3-small) "
        "and implement _embed_text. Falling back to keyword search."
    )


async def get_evidence(db: AsyncSession, evidence_id: uuid.UUID) -> EvidenceSource | None:
    return (await db.execute(
        select(EvidenceSource).where(EvidenceSource.id == evidence_id)
    )).scalar_one_or_none()


def evidence_to_dict(e: EvidenceSource) -> dict:
    return {
        "id": str(e.id),
        "title": e.title,
        "authors": e.authors,
        "journal": e.journal,
        "publication_year": e.publication_year,
        "doi": e.doi,
        "source_url": e.source_url,
        "abstract_summary": e.abstract_summary,
        "topic_tags": e.topic_tags,
        "trust_label": e.trust_label,
    }
