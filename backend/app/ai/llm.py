"""Thin wrapper over the Anthropic SDK: timeouts, retries, model fallback, cost."""

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from typing import Any, Protocol

import anthropic
from anthropic.types.beta import BetaMessage, BetaMessageParam, BetaToolParam

from app.config import get_settings

logger = logging.getLogger(__name__)

# USD per million tokens: (input, output, cache_read, cache_write_5m)
PRICING: dict[str, tuple[Decimal, Decimal, Decimal, Decimal]] = {
    "claude-sonnet-5-5": (Decimal("2.00"), Decimal("10.00"), Decimal("0.20"), Decimal("2.50")),
    "claude-haiku-5-5": (Decimal("0.10"), Decimal("0.50"), Decimal("0.01"), Decimal("0.125")),
}

# Server-side refusal fallback; supported on Sonnet 5.5 (Claude API only).
_FALLBACK_BETA = "server-side-fallback-2026-07-01"
_MODELS_WITH_SERVER_FALLBACK = {"claude-sonnet-5-5"}


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: Decimal = field(default_factory=lambda: Decimal(0))

    def add(self, message: BetaMessage) -> None:
        u = message.usage
        cache_read = u.cache_read_input_tokens or 0
        cache_write = u.cache_creation_input_tokens or 0
        self.input_tokens += u.input_tokens
        self.output_tokens += u.output_tokens
        self.cache_read_tokens += cache_read
        self.cache_write_tokens += cache_write
        prices = PRICING.get(message.model)
        if prices:
            p_in, p_out, p_read, p_write = prices
            million = Decimal(1_000_000)
            self.cost_usd += (
                u.input_tokens * p_in
                + u.output_tokens * p_out
                + cache_read * p_read
                + cache_write * p_write
            ) / million


class LLMClient(Protocol):
    async def create(
        self,
        *,
        model: str,
        system: str,
        tools: Sequence[BetaToolParam],
        messages: Sequence[BetaMessageParam],
        max_tokens: int = 4096,
    ) -> BetaMessage: ...


class LLMUnavailableError(RuntimeError):
    pass


class AnthropicLLM:
    def __init__(self, client: anthropic.AsyncAnthropic, main_model: str, fast_model: str) -> None:
        self._client = client
        self._main = main_model
        self._fast = fast_model

    def _other(self, model: str) -> str:
        return self._fast if model == self._main else self._main

    async def _call(
        self,
        model: str,
        system: str,
        tools: Iterable[BetaToolParam],
        messages: Iterable[BetaMessageParam],
        max_tokens: int,
    ) -> BetaMessage:
        extra: dict[str, Any] = {}
        if model in _MODELS_WITH_SERVER_FALLBACK:
            extra = {"betas": [_FALLBACK_BETA], "fallbacks": "default"}
        message: BetaMessage = await self._client.beta.messages.create(
            model=model,
            max_tokens=max_tokens,
            # System prompt + tenant settings are stable per tenant -> cache them.
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            tools=list(tools),
            messages=list(messages),
            output_config={"effort": "low"},
            **extra,
        )
        return message

    async def create(
        self,
        *,
        model: str,
        system: str,
        tools: Sequence[BetaToolParam],
        messages: Sequence[BetaMessageParam],
        max_tokens: int = 4096,
    ) -> BetaMessage:
        if not (self._client.api_key or self._client.auth_token):
            raise LLMUnavailableError("ANTHROPIC_API_KEY is not set")
        try:
            return await self._call(model, system, tools, messages, max_tokens)
        except (
            anthropic.RateLimitError,
            anthropic.InternalServerError,
            anthropic.APIConnectionError,
        ) as exc:
            fallback = self._other(model)
            logger.warning(
                "llm_fallback",
                extra={"from_model": model, "to_model": fallback, "error": type(exc).__name__},
            )
        except anthropic.APIError as exc:
            # Auth, bad request, etc.: retrying on another model won't help.
            raise LLMUnavailableError(f"{type(exc).__name__}: {exc}") from exc
        try:
            return await self._call(fallback, system, tools, messages, max_tokens)
        except anthropic.APIError as exc:
            raise LLMUnavailableError(str(exc)) from exc


@lru_cache
def get_llm() -> AnthropicLLM:
    settings = get_settings()
    client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key.get_secret_value() or None,
        timeout=settings.llm_timeout_s,
        max_retries=settings.llm_max_retries,
    )
    return AnthropicLLM(client, settings.llm_model_main, settings.llm_model_fast)
