"""Per-message request pipeline (BUILD.md §7.1). M1: gateway -> agent -> persist."""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.agent import AgentResult, Turn, run_agent
from app.ai.llm import LLMClient
from app.ai.prompts import render_system_prompt
from app.ai.tools import ToolContext
from app.config import Settings
from app.conversation import service
from app.db import tenant_session
from app.retrieval.embeddings import Embedder
from app.tenants.models import Tenant
from app.tenants.service import tenant_settings

logger = logging.getLogger(__name__)

OPERATOR_MODE_REPLY = "Xabaringiz operatorga yetkazildi. Tez orada javob berishadi."


@dataclass
class Deps:
    settings: Settings
    llm: LLMClient
    embedder: Embedder
    sessionmaker: async_sessionmaker[AsyncSession]


@dataclass(frozen=True)
class IncomingMessage:
    telegram_id: int
    name: str | None
    language: str | None
    text: str


@dataclass(frozen=True)
class Reply:
    text: str
    sources: list[str]


def format_reply(result: AgentResult) -> Reply:
    titles = [str(s["title"]) for s in result.sources]
    return Reply(text=result.text, sources=titles)


async def handle_customer_message(deps: Deps, tenant: Tenant, msg: IncomingMessage) -> Reply:
    cfg = tenant_settings(tenant)
    async with tenant_session(tenant.id, deps.sessionmaker) as session:
        customer = await service.upsert_customer(
            session, tenant.id, msg.telegram_id, msg.name, msg.language
        )
        conversation = await service.get_open_conversation(session, tenant.id, customer.id)
        history = [
            Turn(m.role, m.content) for m in await service.recent_turns(session, conversation.id)
        ]
        await service.add_message(
            session,
            tenant_id=tenant.id,
            conversation_id=conversation.id,
            role="customer",
            content=msg.text,
        )
        if conversation.status == "operator":
            return Reply(OPERATOR_MODE_REPLY, [])

        system_prompt = render_system_prompt(
            tenant_name=tenant.name, tone=cfg.tone, working_hours=cfg.working_hours
        )
        ctx = ToolContext(
            session=session,
            tenant_id=tenant.id,
            customer_id=customer.id,
            embedder=deps.embedder,
            top_k=deps.settings.retrieval_top_k,
        )
        result = await run_agent(
            llm=deps.llm,
            model=deps.settings.llm_model_main,
            system_prompt=system_prompt,
            history=history,
            question=msg.text,
            ctx=ctx,
            source_threshold=cfg.handoff_threshold,
        )
        await service.add_message(
            session,
            tenant_id=tenant.id,
            conversation_id=conversation.id,
            role="assistant",
            content=result.text,
            tool_calls=result.tool_calls,
            sources=result.sources,
            trace_id=result.trace_id,
            model=result.model,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            cost_usd=result.usage.cost_usd,
            latency_ms=result.latency_ms,
        )
    logger.info(
        "answered",
        extra={
            "tenant": tenant.slug,
            "trace_id": result.trace_id,
            "model": result.model,
            "latency_ms": result.latency_ms,
            "cost_usd": str(result.usage.cost_usd),
            "tools": [c["name"] for c in result.tool_calls],
            "failed": result.failed,
            "prompt_version": result.prompt_version,
        },
    )
    return format_reply(result)
