from collections.abc import Sequence
from typing import Any

from anthropic.types.beta import BetaMessage, BetaMessageParam, BetaToolParam


def make_message(
    content: list[dict[str, Any]], stop_reason: str, model: str = "claude-sonnet-5-5"
) -> BetaMessage:
    return BetaMessage.model_validate(
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 1000, "output_tokens": 100},
        }
    )


def tool_use(query: str, tool_id: str = "toolu_1") -> BetaMessage:
    return make_message(
        [
            {
                "type": "tool_use",
                "id": tool_id,
                "name": "search_knowledge",
                "input": {"query": query},
            }
        ],
        "tool_use",
    )


def text(answer: str) -> BetaMessage:
    return make_message([{"type": "text", "text": answer}], "end_turn")


class ScriptedLLM:
    """Returns pre-baked responses in order and records every request."""

    def __init__(self, responses: list[BetaMessage]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def create(
        self,
        *,
        model: str,
        system: str,
        tools: Sequence[BetaToolParam],
        messages: Sequence[BetaMessageParam],
        max_tokens: int = 4096,
    ) -> BetaMessage:
        self.calls.append({"model": model, "system": system, "messages": list(messages)})
        return self.responses.pop(0)
