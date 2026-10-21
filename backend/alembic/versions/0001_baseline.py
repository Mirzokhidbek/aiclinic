"""baseline: tenants, customers, conversations, messages, documents, chunks

Revision ID: 0001
Revises:
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 768


def _id() -> sa.Column[sa.Uuid]:
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _tenant() -> sa.Column[sa.Uuid]:
    return sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False)


def _created() -> sa.Column[sa.DateTime]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "tenants",
        _id(),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("bot_token_enc", sa.Text()),
        sa.Column("settings", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("plan", sa.String(32), nullable=False, server_default="free"),
        _created(),
    )
    op.create_table(
        "customers",
        _id(),
        _tenant(),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(200)),
        sa.Column("phone_enc", sa.Text()),
        sa.Column("language", sa.String(16)),
        _created(),
        sa.UniqueConstraint("tenant_id", "telegram_id"),
    )
    op.create_table(
        "conversations",
        _id(),
        _tenant(),
        sa.Column("customer_id", sa.Uuid(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ai"),
        sa.Column("assigned_to", sa.Uuid()),
        _created(),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_conversations_tenant_customer", "conversations", ["tenant_id", "customer_id", "status"]
    )
    op.create_table(
        "messages",
        _id(),
        _tenant(),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", pg.JSONB()),
        sa.Column("sources", pg.JSONB()),
        sa.Column("trace_id", sa.String(64)),
        sa.Column("model", sa.String(64)),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("cost_usd", sa.Numeric(12, 6)),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("feedback", sa.SmallInteger()),
        _created(),
    )
    op.create_index(
        "ix_messages_conversation_created", "messages", ["conversation_id", "created_at"]
    )
    op.create_table(
        "documents",
        _id(),
        _tenant(),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False, server_default="file"),
        sa.Column("s3_key", sa.Text()),
        sa.Column("url", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
        _created(),
    )
    op.create_table(
        "chunks",
        _id(),
        _tenant(),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_version", sa.Integer(), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("heading_path", sa.Text(), nullable=False, server_default=""),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("tsv", pg.TSVECTOR(), sa.Computed("to_tsvector('simple', text)", persisted=True)),
        sa.Column("metadata", pg.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_chunks_tenant_document", "chunks", ["tenant_id", "document_id"])
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index("ix_chunks_tsv", "chunks", ["tsv"], postgresql_using="gin")


def downgrade() -> None:
    for table in ("chunks", "documents", "messages", "conversations", "customers", "tenants"):
        op.drop_table(table)
