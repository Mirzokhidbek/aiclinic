import hmac
from typing import Any

from arq.connections import ArqRedis
from fastapi import APIRouter, Header, Request

from app.config import get_settings
from app.errors import ApiError

router = APIRouter(prefix="/v1/telegram", tags=["telegram"])

SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"  # noqa: S105 (header name)


def verify_secret(received: str | None) -> bool:
    expected = get_settings().telegram_webhook_secret.get_secret_value()
    return bool(expected) and received is not None and hmac.compare_digest(received, expected)


@router.post("/webhook/{tenant_slug}")
async def telegram_webhook(
    tenant_slug: str,
    request: Request,
    secret: str | None = Header(default=None, alias=SECRET_HEADER),
) -> dict[str, bool]:
    if not verify_secret(secret):
        raise ApiError(401, "invalid_secret", "Invalid webhook secret")
    update: dict[str, Any] = await request.json()
    pool: ArqRedis = request.app.state.arq
    await pool.enqueue_job(
        "process_update", tenant_slug, update, _job_id=f"tg:{tenant_slug}:{update.get('update_id')}"
    )
    return {"ok": True}
