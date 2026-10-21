import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.chunking import chunk_markdown, embedding_text
from app.retrieval.embeddings import Embedder
from app.retrieval.models import Chunk, Document


async def upsert_document(
    session: AsyncSession, tenant_id: uuid.UUID, title: str, source_type: str = "file"
) -> Document:
    result = await session.execute(
        select(Document).where(Document.tenant_id == tenant_id, Document.title == title)
    )
    document = result.scalar_one_or_none()
    if document is None:
        document = Document(tenant_id=tenant_id, title=title, source_type=source_type)
        session.add(document)
        await session.flush()
    return document


async def ingest_text(
    session: AsyncSession, document: Document, markdown: str, embedder: Embedder
) -> int:
    """Index a new version of the document, switch to it, then drop old chunks."""
    new_version = document.version + 1
    document.status = "indexing"
    pieces = chunk_markdown(markdown)
    vectors = await embedder.embed_documents([embedding_text(document.title, c) for c in pieces])
    session.add_all(
        Chunk(
            tenant_id=document.tenant_id,
            document_id=document.id,
            document_version=new_version,
            ord=piece.ord,
            text=piece.text,
            heading_path=piece.heading_path,
            embedding=vector,
        )
        for piece, vector in zip(pieces, vectors, strict=True)
    )
    document.version = new_version
    document.status = "indexed"
    document.error = None
    await session.flush()
    await session.execute(
        delete(Chunk).where(Chunk.document_id == document.id, Chunk.document_version != new_version)
    )
    return len(pieces)
