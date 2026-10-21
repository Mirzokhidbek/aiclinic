import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.auth.crypto import decrypt
from app.auth.telegram import InvalidInitDataError, verify_init_data
from app.auth.tokens import TTL, Principal, issue_token
from app.conversation.service import upsert_customer
from app.db import get_sessionmaker, set_tenant
from app.errors import ApiError
from app.tenants.service import get_tenant_by_slug

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class TelegramAuthIn(BaseModel):
    init_data: str = Field(min_length=10, max_length=4096)
    tenant_slug: str = Field(min_length=1, max_length=64)


class TenantOut(BaseModel):
    slug: str
    name: str


class CustomerOut(BaseModel):
    id: uuid.UUID
    name: str | None


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (OAuth token type, not a secret)
    expires_in: int
    role: str
    tenant: TenantOut
    customer: CustomerOut


@router.post("/telegram", response_model=AuthOut)
async def auth_telegram(body: TelegramAuthIn) -> AuthOut:
    async with get_sessionmaker()() as session, session.begin():
        tenant = await get_tenant_by_slug(session, body.tenant_slug)
        if tenant is None or tenant.bot_token_enc is None:
            raise ApiError(404, "tenant_not_found", "Unknown business")
        try:
            data = verify_init_data(body.init_data, decrypt(tenant.bot_token_enc))
        except InvalidInitDataError as exc:
            raise ApiError(
                401, "invalid_init_data", "Telegram login could not be verified"
            ) from exc
        await set_tenant(session, tenant.id)
        customer = await upsert_customer(
            session, tenant.id, data.user.id, data.user.full_name, data.user.language_code
        )
        principal = Principal(tenant_id=tenant.id, subject_id=customer.id, role="customer")
        return AuthOut(
            access_token=issue_token(principal),
            expires_in=int(TTL.total_seconds()),
            role="customer",
            tenant=TenantOut(slug=tenant.slug, name=tenant.name),
            customer=CustomerOut(id=customer.id, name=customer.name),
        )
