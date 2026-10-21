"""Seed demo tenants from seed/<tenant>/tenant.json and ingest their documents.

Usage: python -m app.seed [seed_dir]
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.crypto import encrypt
from app.booking.seed import seed_services
from app.config import get_settings
from app.db import get_engine, get_sessionmaker, set_tenant
from app.observability.logging import configure_logging
from app.retrieval.embeddings import Embedder, get_embedder
from app.retrieval.ingest import ingest_text, upsert_document
from app.tenants.models import Tenant
from app.tenants.service import tenant_settings

logger = logging.getLogger(__name__)

DEFAULT_SEED_DIR = Path(os.environ.get("SEED_DIR", Path(__file__).resolve().parents[2] / "seed"))

# Which env var holds each tenant's bot token (second tenant arrives in M7).
BOT_TOKEN_ENV = {"nur-klinika": "TELEGRAM_BOT_TOKEN"}


async def seed_tenant(
    sessionmaker: async_sessionmaker[AsyncSession], tenant_dir: Path, embedder: Embedder
) -> Tenant:
    spec: dict[str, Any] = json.loads((tenant_dir / "tenant.json").read_text(encoding="utf-8"))
    settings = get_settings()
    async with sessionmaker() as session, session.begin():
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == spec["slug"]))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(slug=spec["slug"])
            session.add(tenant)
        tenant.name = spec["name"]
        tenant.plan = spec.get("plan", "free")
        tenant.settings = spec.get("settings", {})
        env_name = BOT_TOKEN_ENV.get(spec["slug"])
        token = os.environ.get(env_name, "") if env_name else ""
        if not token and env_name == "TELEGRAM_BOT_TOKEN":
            token = settings.telegram_bot_token.get_secret_value()
        if token:
            tenant.bot_token_enc = encrypt(token)
        await session.flush()

        await set_tenant(session, tenant.id)
        for doc in spec.get("documents", []):
            text = (tenant_dir / doc["file"]).read_text(encoding="utf-8")
            document = await upsert_document(session, tenant.id, doc["title"])
            count = await ingest_text(session, document, text, embedder)
            logger.info(
                "document_indexed",
                extra={
                    "tenant": tenant.slug,
                    "title": doc["title"],
                    "chunks": count,
                    "version": document.version,
                },
            )
        services_file = tenant_dir / "services.json"
        if services_file.exists():
            tz = ZoneInfo(tenant_settings(tenant).timezone)
            services, slots = await seed_services(
                session,
                tenant.id,
                json.loads(services_file.read_text(encoding="utf-8")),
                tz,
                datetime.now(tz).date(),
            )
            logger.info(
                "services_seeded",
                extra={"tenant": tenant.slug, "services": services, "new_slots": slots},
            )
    return tenant


def tenant_dirs(seed_dir: Path) -> list[Path]:
    return sorted(p for p in seed_dir.iterdir() if (p / "tenant.json").exists())


async def main(seed_dir: Path) -> None:
    configure_logging(get_settings().log_level)
    embedder = get_embedder()
    sessionmaker = get_sessionmaker()
    for tenant_dir in tenant_dirs(seed_dir):
        tenant = await seed_tenant(sessionmaker, tenant_dir, embedder)
        logger.info(
            "tenant_seeded",
            extra={"tenant": tenant.slug, "has_bot_token": tenant.bot_token_enc is not None},
        )
    await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SEED_DIR))
