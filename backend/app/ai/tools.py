"""Tool schemas + handlers. Tenant/customer always come from ToolContext, never model input."""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from html import escape
from typing import Any

from anthropic.types.beta import BetaToolParam
from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.embeddings import Embedder
from app.retrieval.search import SearchHit, vector_search


@dataclass
class ToolContext:
    session: AsyncSession
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    embedder: Embedder
    top_k: int = 5
    hits: list[SearchHit] = field(default_factory=list)


SEARCH_KNOWLEDGE: BetaToolParam = {
    "name": "search_knowledge",
    "description": (
        "Search the clinic's own documents (FAQ, price list, services, working hours, "
        "address, policies). Returns the most relevant passages with their document title. "
        "Call this before answering any factual question. Write the query in Uzbek Latin."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Standalone search query, e.g. 'stomatolog qabuli narxi'.",
            }
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    "strict": True,
}

TOOLS: list[BetaToolParam] = [SEARCH_KNOWLEDGE]


def format_hits(hits: list[SearchHit]) -> str:
    if not hits:
        return "No matching documents found."
    parts = [
        f'<document index="{i}" title="{escape(h.title)}" section="{escape(h.heading_path)}" '
        f'score="{h.score:.2f}">\n{h.text}\n</document>'
        for i, h in enumerate(hits, start=1)
    ]
    return "\n".join(parts)


async def search_knowledge(ctx: ToolContext, args: dict[str, Any]) -> str:
    query = str(args.get("query", "")).strip()
    if not query:
        return "Error: query is empty."
    hits = await vector_search(ctx.session, ctx.tenant_id, query, ctx.embedder, top_k=ctx.top_k)
    ctx.hits.extend(hits)
    return format_hits(hits)


Handler = Callable[[ToolContext, dict[str, Any]], Awaitable[str]]

HANDLERS: dict[str, Handler] = {"search_knowledge": search_knowledge}
