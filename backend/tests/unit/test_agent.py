import uuid
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import agent as agent_mod
from app.ai.agent import FALLBACK_REPLY, Turn, build_messages, run_agent, select_sources
from app.ai.tools import ToolContext
from app.retrieval.embeddings import HashingEmbedder
from app.retrieval.search import SearchHit
from tests.fakes import ScriptedLLM, make_message, text, tool_use

TENANT = uuid.uuid4()
CUSTOMER = uuid.uuid4()
DOC = uuid.uuid4()


def hit(score: float, title: str = "Narxlar ro'yxati", doc: uuid.UUID = DOC) -> SearchHit:
    return SearchHit(
        chunk_id=uuid.uuid4(),
        document_id=doc,
        title=title,
        heading_path="Narxlar",
        text="Stomatolog qabuli: 150 000 so'm",
        score=score,
    )


def ctx() -> ToolContext:
    return ToolContext(
        session=cast(AsyncSession, None),
        tenant_id=TENANT,
        customer_id=CUSTOMER,
        embedder=HashingEmbedder(),
    )


def test_build_messages_alternates_and_wraps_customer_text() -> None:
    history = [
        Turn("assistant", "salom"),
        Turn("customer", "a"),
        Turn("customer", "b"),
        Turn("assistant", "javob"),
    ]
    messages = build_messages(history, "narxi?")
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert "<customer_message>\na\n</customer_message>" in cast(str, messages[0]["content"])
    assert "<customer_message>\nb\n</customer_message>" in cast(str, messages[0]["content"])
    assert messages[-1]["content"] == "<customer_message>\nnarxi?\n</customer_message>"


def test_select_sources_dedupes_and_thresholds() -> None:
    other = uuid.uuid4()
    hits = [hit(0.8), hit(0.7), hit(0.6, "FAQ", other), hit(0.1, "Low", uuid.uuid4())]
    sources = select_sources(hits, threshold=0.5)
    assert [s["title"] for s in sources] == ["Narxlar ro'yxati", "FAQ"]
    # nothing above threshold -> fall back to best hit
    assert [s["title"] for s in select_sources([hit(0.2)], threshold=0.5)] == ["Narxlar ro'yxati"]


async def test_tool_loop_calls_search_and_returns_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    async def fake_search(
        session: Any, tenant_id: uuid.UUID, query: str, embedder: Any, top_k: int = 5
    ) -> list[SearchHit]:
        seen.update(tenant_id=tenant_id, query=query)
        return [hit(0.82)]

    monkeypatch.setattr("app.ai.tools.vector_search", fake_search)
    llm = ScriptedLLM(
        [
            tool_use("stomatolog qabuli narxi"),
            text("Stomatolog qabuli 150 000 so'm. Manba: Narxlar ro'yxati"),
        ]
    )
    result = await run_agent(
        llm=llm,
        model="claude-sonnet-5-5",
        system_prompt="sys",
        history=[],
        question="Stomatolog qabuli necha pul?",
        ctx=ctx(),
        source_threshold=0.35,
    )

    assert result.text.startswith("Stomatolog qabuli 150 000 so'm")
    assert seen == {"tenant_id": TENANT, "query": "stomatolog qabuli narxi"}
    assert result.tool_calls == [
        {"name": "search_knowledge", "input": {"query": "stomatolog qabuli narxi"}}
    ]
    assert result.sources[0]["title"] == "Narxlar ro'yxati"
    assert result.usage.input_tokens == 2000
    assert result.usage.cost_usd > 0
    # second request carries the tool result back to the model
    tool_turn = llm.calls[1]["messages"][-1]
    assert tool_turn["role"] == "user"
    assert tool_turn["content"][0]["type"] == "tool_result"
    assert "150 000" in tool_turn["content"][0]["content"]


async def test_tool_loop_is_bounded() -> None:
    llm = ScriptedLLM([tool_use("x", f"t{i}") for i in range(agent_mod.MAX_TOOL_ITERATIONS)])
    result = await run_agent(
        llm=llm,
        model="m",
        system_prompt="s",
        history=[],
        question="?",
        ctx=_ctx_with_stub_search(),
        source_threshold=0.3,
    )
    assert result.failed and result.text == FALLBACK_REPLY
    assert len(llm.calls) == agent_mod.MAX_TOOL_ITERATIONS


async def test_refusal_returns_fallback() -> None:
    llm = ScriptedLLM([make_message([], "refusal")])
    result = await run_agent(
        llm=llm,
        model="m",
        system_prompt="s",
        history=[],
        question="?",
        ctx=ctx(),
        source_threshold=0.3,
    )
    assert result.failed and result.text == FALLBACK_REPLY


def _ctx_with_stub_search() -> ToolContext:
    import app.ai.tools as tools

    async def stub(c: ToolContext, args: dict[str, Any]) -> str:
        return "nothing"

    tools.HANDLERS["search_knowledge"] = stub
    return ctx()


@pytest.fixture(autouse=True)
def restore_handlers() -> Any:
    import app.ai.tools as tools

    original = dict(tools.HANDLERS)
    yield
    tools.HANDLERS.clear()
    tools.HANDLERS.update(original)
