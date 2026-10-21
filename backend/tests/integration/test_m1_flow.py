"""M1 acceptance (offline): seeded Nur Klinika answers the price question with a source."""

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.conversation.models import Message
from app.conversation.pipeline import Deps, IncomingMessage, handle_customer_message
from app.db import tenant_session
from app.retrieval.embeddings import HashingEmbedder
from app.retrieval.models import Chunk
from app.retrieval.search import vector_search
from app.seed import seed_tenant
from tests.fakes import ScriptedLLM, text, tool_use

SEED = Path(__file__).resolve().parents[3] / "seed" / "nur_klinika"
EMBEDDER = HashingEmbedder()


async def test_seed_search_and_answer(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    tenant = await seed_tenant(sessionmaker, SEED, EMBEDDER)
    assert tenant.bot_token_enc and "test-token" not in tenant.bot_token_enc

    # Re-seeding bumps the version and leaves only the new chunks.
    tenant = await seed_tenant(sessionmaker, SEED, EMBEDDER)
    async with tenant_session(tenant.id, sessionmaker) as s:
        versions = (await s.execute(select(func.distinct(Chunk.document_version)))).scalars()
        assert set(versions) == {2}

        hits = await vector_search(s, tenant.id, "Stomatolog qabuli necha pul?", EMBEDDER)
    assert hits[0].title == "Narxlar ro'yxati"
    assert any("150 000" in h.text for h in hits)

    llm = ScriptedLLM(
        [
            tool_use("Stomatolog qabuli narxi"),
            text("Stomatolog qabuli 150 000 so'm turadi. Manba: Narxlar ro'yxati"),
        ]
    )
    deps = Deps(settings=get_settings(), llm=llm, embedder=EMBEDDER, sessionmaker=sessionmaker)
    reply = await handle_customer_message(
        deps,
        tenant,
        IncomingMessage(
            telegram_id=42, name="Ali", language="uz", text="Stomatolog qabuli necha pul?"
        ),
    )
    assert "150 000" in reply.text
    assert "Narxlar ro'yxati" in reply.sources
    assert "<document" in llm.calls[1]["messages"][-1]["content"][0]["content"]

    async with tenant_session(tenant.id, sessionmaker) as s:
        rows = (await s.execute(select(Message).order_by(Message.created_at))).scalars().all()
    assert [m.role for m in rows] == ["customer", "assistant"]
    assert rows[1].sources and rows[1].sources[0]["title"] == "Narxlar ro'yxati"
    assert rows[1].input_tokens == 2000 and rows[1].trace_id
