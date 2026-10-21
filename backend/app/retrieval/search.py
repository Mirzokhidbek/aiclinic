import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.embeddings import Embedder
from app.retrieval.models import Chunk, Document


class SearchHit(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    title: str
    heading_path: str
    text: str
    score: float


async def vector_search(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    query: str,
    embedder: Embedder,
    top_k: int = 5,
) -> list[SearchHit]:
    query_vec = await embedder.embed_query(query)
    distance = Chunk.embedding.cosine_distance(query_vec).label("distance")
    stmt = (
        select(Chunk, Document.title, distance)
        .join(Document, Document.id == Chunk.document_id)
        .where(
            Chunk.tenant_id == tenant_id,
            Document.tenant_id == tenant_id,
            Document.status == "indexed",
            Chunk.document_version == Document.version,
        )
        .order_by(distance)
        .limit(top_k)
    )
    rows = (await session.execute(stmt)).all()
    return [
        SearchHit(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            title=title,
            heading_path=chunk.heading_path,
            text=chunk.text,
            score=round(1.0 - float(dist), 4),
        )
        for chunk, title, dist in rows
    ]
