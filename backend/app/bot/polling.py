"""Bot service entrypoint.

- PUBLIC_BASE_URL set: register a webhook per tenant (updates arrive at the API).
- Otherwise (local dev): long-poll Telegram and enqueue updates to the same worker job.
"""

import asyncio
import logging

from aiogram import Bot
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.bot.dispatcher import bot_for, close_bots
from app.config import get_settings
from app.db import get_sessionmaker
from app.observability.logging import configure_logging
from app.tenants.models import Tenant
from app.tenants.service import list_tenants

logger = logging.getLogger(__name__)


async def register_webhook(bot: Bot, tenant: Tenant) -> None:
    settings = get_settings()
    url = f"{settings.public_base_url.rstrip('/')}/v1/telegram/webhook/{tenant.slug}"
    await bot.set_webhook(
        url,
        secret_token=settings.telegram_webhook_secret.get_secret_value(),
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=False,
    )
    logger.info("webhook_registered", extra={"tenant": tenant.slug, "url": url})


async def poll(bot: Bot, tenant: Tenant, pool: ArqRedis) -> None:
    await bot.delete_webhook(drop_pending_updates=False)
    offset: int | None = None
    logger.info("polling_started", extra={"tenant": tenant.slug})
    while True:
        try:
            updates = await bot.get_updates(
                offset=offset, timeout=30, allowed_updates=["message", "callback_query"]
            )
        except Exception:
            logger.exception("polling_error", extra={"tenant": tenant.slug})
            await asyncio.sleep(5)
            continue
        for update in updates:
            offset = update.update_id + 1
            await pool.enqueue_job(
                "process_update",
                tenant.slug,
                update.model_dump(mode="json", exclude_none=True),
                _job_id=f"tg:{tenant.slug}:{update.update_id}",
            )


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    while True:
        async with get_sessionmaker()() as session:
            tenants = [t for t in await list_tenants(session) if t.bot_token_enc]
        if tenants:
            break
        logger.warning("no tenants with a bot token yet; run `make seed`")
        await asyncio.sleep(10)
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        if settings.public_base_url:
            for tenant in tenants:
                await register_webhook(bot_for(tenant), tenant)
            await asyncio.Event().wait()
        else:
            await asyncio.gather(*(poll(bot_for(t), t, pool) for t in tenants))
    finally:
        await pool.aclose()
        await close_bots()


if __name__ == "__main__":
    asyncio.run(main())
