"""Bounded tool loop on the Anthropic SDK (no frameworks)."""

import logging
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from anthropic.types.beta import BetaMessageParam, BetaToolResultBlockParam

from app.ai.llm import LLMClient, LLMUnavailableError, Usage
from app.ai.prompts import SYSTEM_PROMPT_VERSION
from app.ai.tools import HANDLERS, TOOLS, ToolContext
from app.retrieval.search import SearchHit

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5

FALLBACK_REPLY = (
    "Kechirasiz, hozir javob bera olmayapman. Savolingizni operatorga yo'naltiraman, "
    "tez orada siz bilan bog'lanishadi."
)


@dataclass(frozen=True)
class Turn:
    role: str  # "customer" | "assistant"
    content: str


@dataclass
class AgentResult:
    text: str
    model: str
    sources: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    usage: Usage
    latency_ms: int
    trace_id: str
    prompt_version: str = SYSTEM_PROMPT_VERSION
    failed: bool = False
    hits: list[SearchHit] = field(default_factory=list)


def wrap_customer_message(text: str) -> str:
    return f"<customer_message>\n{text}\n</customer_message>"


def build_messages(history: Sequence[Turn], question: str) -> list[BetaMessageParam]:
    """Convert stored turns into alternating user/assistant messages ending with the question."""
    messages: list[BetaMessageParam] = []
    for turn in [*history, Turn("customer", question)]:
        role: Literal["user", "assistant"] = "user" if turn.role == "customer" else "assistant"
        content = wrap_customer_message(turn.content) if role == "user" else turn.content
        if messages and messages[-1]["role"] == role:
            previous = cast(str, messages[-1]["content"])
            messages[-1] = {"role": role, "content": f"{previous}\n\n{content}"}
        elif not messages and role == "assistant":
            continue  # API requires the first message to be from the user
        else:
            messages.append({"role": role, "content": content})
    return messages


def select_sources(
    hits: Sequence[SearchHit], threshold: float, limit: int = 3
) -> list[dict[str, Any]]:
    """Unique document titles of hits above threshold (best first); top hit if none pass."""
    ranked = sorted(hits, key=lambda h: h.score, reverse=True)
    chosen = [h for h in ranked if h.score >= threshold] or ranked[:1]
    sources: list[dict[str, Any]] = []
    seen: set[uuid.UUID] = set()
    for hit in chosen:
        if hit.document_id in seen:
            continue
        seen.add(hit.document_id)
        sources.append(
            {
                "document_id": str(hit.document_id),
                "title": hit.title,
                "heading_path": hit.heading_path,
                "score": hit.score,
            }
        )
        if len(sources) == limit:
            break
    return sources


async def run_agent(
    *,
    llm: LLMClient,
    model: str,
    system_prompt: str,
    history: Sequence[Turn],
    question: str,
    ctx: ToolContext,
    source_threshold: float,
) -> AgentResult:
    started = time.monotonic()
    trace_id = uuid.uuid4().hex
    usage = Usage()
    tool_calls: list[dict[str, Any]] = []
    messages = build_messages(history, question)
    used_model = model

    def result(text: str, *, failed: bool = False) -> AgentResult:
        return AgentResult(
            text=text,
            model=used_model,
            sources=[] if failed else select_sources(ctx.hits, source_threshold),
            tool_calls=tool_calls,
            usage=usage,
            latency_ms=int((time.monotonic() - started) * 1000),
            trace_id=trace_id,
            failed=failed,
            hits=list(ctx.hits),
        )

    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            response = await llm.create(
                model=model, system=system_prompt, tools=TOOLS, messages=messages
            )
        except LLMUnavailableError:
            logger.exception("llm_unavailable", extra={"trace_id": trace_id})
            return result(FALLBACK_REPLY, failed=True)
        usage.add(response)
        used_model = response.model

        if response.stop_reason == "refusal":
            return result(FALLBACK_REPLY, failed=True)

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            return result(text or FALLBACK_REPLY, failed=not text)

        # Pass the assistant turn back unchanged (thinking blocks included).
        messages.append(
            cast(
                BetaMessageParam,
                {"role": "assistant", "content": [b.to_dict() for b in response.content]},
            )
        )
        results: list[BetaToolResultBlockParam] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            args = cast(dict[str, Any], block.input)
            tool_calls.append({"name": block.name, "input": args})
            handler = HANDLERS.get(block.name)
            if handler is None:
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Unknown tool: {block.name}",
                        "is_error": True,
                    }
                )
                continue
            try:
                output = await handler(ctx, args)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
            except Exception:
                logger.exception("tool_failed", extra={"tool": block.name, "trace_id": trace_id})
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Tool failed.",
                        "is_error": True,
                    }
                )
        messages.append({"role": "user", "content": results})

    return result(FALLBACK_REPLY, failed=True)
