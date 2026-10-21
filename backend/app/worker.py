"""arq worker: processes Telegram updates off the request path."""

import logging
from datetime import UTC, datetime
from typing import Any, ClassVar

from aiogram.types import Update
from arq import cron
from arq.connections import RedisSettings

from app.ai.llm import get_llm
from app.booking.service import expire_pending
from app.bot.dispatcher import bot_for, close_bots, get_dispatcher
from app.config import get_settings
from app.conversation.pipeline import Deps
from app.db import get_engine, get_sessionmaker, tenant_session
from app.observability.logging import configure_logging
from app.retrieval.embeddings import get_embedder
from app.tenants.service import get_tenant_by_slug, list_tenants

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    ctx["deps"] = Deps(
        settings=settings, llm=get_llm(), embedder=get_embedder(), sessionmaker=get_sessionmaker()
    )


async def shutdown(ctx: dict[str, Any]) -> None:
    await close_bots()
    await get_engine().dispose()


async def process_update(ctx: dict[str, Any], tenant_slug: str, update: dict[str, Any]) -> None:
    deps: Deps = ctx["deps"]
    async with deps.sessionmaker() as session:
        tenant = await get_tenant_by_slug(session, tenant_slug)
    if tenant is None:
        logger.warning("unknown_tenant", extra={"tenant": tenant_slug})
        return
    bot = bot_for(tenant)
    await get_dispatcher().feed_update(
        bot, Update.model_validate(update, context={"bot": bot}), tenant=tenant, deps=deps
    )


async def expire_bookings(ctx: dict[str, Any]) -> int:
    """Release seats held by pending bookings that were never confirmed."""
    deps: Deps = ctx["deps"]
    async with deps.sessionmaker() as session:
        tenants = await list_tenants(session)
    total = 0
    for tenant in tenants:
        async with tenant_session(tenant.id, deps.sessionmaker) as session:
            total += await expire_pending(session, tenant.id, datetime.now(UTC))
    if total:
        logger.info("bookings_expired", extra={"count": total})
    return total


class WorkerSettings:
    functions: ClassVar = [process_update]
    cron_jobs: ClassVar = [cron(expire_bookings, second={0}, run_at_startup=True)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 20
    job_timeout = 120
