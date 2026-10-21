import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from functools import lru_cache

from sqlalchemy import DateTime, func, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def set_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Scope the current transaction to a tenant (read by RLS policies)."""
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)}
    )


@asynccontextmanager
async def tenant_session(
    tenant_id: uuid.UUID, sessionmaker: async_sessionmaker[AsyncSession] | None = None
) -> AsyncIterator[AsyncSession]:
    """One transaction scoped to a tenant. Commits on success, rolls back on error."""
    maker = sessionmaker or get_sessionmaker()
    async with maker() as session, session.begin():
        await set_tenant(session, tenant_id)
        yield session
