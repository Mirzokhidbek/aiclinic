"""booking: services, slots, bookings

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tenant() -> sa.Column[sa.Uuid]:
    return sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False)


def _created() -> sa.Column[sa.DateTime]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _tenant(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("price_uzs", sa.BigInteger(), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _created(),
        sa.UniqueConstraint("tenant_id", "name"),
    )
    op.create_table(
        "slots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _tenant(),
        sa.Column(
            "service_id",
            sa.Uuid(),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("booked_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("service_id", "starts_at"),
        sa.CheckConstraint("booked_count >= 0 AND booked_count <= capacity", name="ck_slots_count"),
    )
    op.create_index(
        "ix_slots_tenant_service_start", "slots", ["tenant_id", "service_id", "starts_at"]
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _tenant(),
        sa.Column("customer_id", sa.Uuid(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("slot_id", sa.Uuid(), sa.ForeignKey("slots.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("confirm_token", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        _created(),
        sa.UniqueConstraint("tenant_id", "idempotency_key"),
    )
    op.create_index("ix_bookings_customer", "bookings", ["tenant_id", "customer_id"])
    op.create_index(
        "ix_bookings_pending_expiry",
        "bookings",
        ["expires_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_table("bookings")
    op.drop_table("slots")
    op.drop_table("services")
