import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tenants.models import Tenant


class TenantSettings(BaseModel):
    tone: str = "samimiy va qisqa"
    working_hours: str = ""
    handoff_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    timezone: str = "Asia/Tashkent"


def tenant_settings(tenant: Tenant) -> TenantSettings:
    raw: dict[str, Any] = tenant.settings or {}
    return TenantSettings.model_validate(raw)


async def get_tenant_by_slug(session: AsyncSession, slug: str) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.slug == slug))
    return result.scalar_one_or_none()


async def list_tenants(session: AsyncSession) -> list[Tenant]:
    result = await session.execute(select(Tenant).order_by(Tenant.created_at))
    return list(result.scalars())


async def get_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    return (await session.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
