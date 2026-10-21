# Clinic AI — AI customer support for Uzbek businesses (Telegram bot + Mini App)

Multi-tenant support platform: customers ask the Telegram bot in Uzbek and get answers grounded in the business's own documents, with sources. Demo tenant: **Nur Klinika**. Spec: [BUILD.md](BUILD.md).

**Status:** Milestone 1 (foundations + FAQ bot).

## Architecture (M1)

```
Telegram ──► bot (long-poll locally) ─┐
Telegram ──► api /v1/telegram/webhook ┴─► Redis (arq) ──► worker
                                                         │
                     aiogram handler ─► pipeline ─► Claude agent loop (anthropic SDK)
                                                         │  tool: search_knowledge
                                                         ▼
                                     Postgres + pgvector (chunks, messages, tenants)
```

- `backend/app/ai/` — Anthropic client wrapper (timeouts, retries, model fallback, prompt caching, cost), bounded tool loop, versioned prompts.
- `backend/app/retrieval/` — heading-aware chunking, pluggable embedder (local fastembed `paraphrase-multilingual-mpnet-base-v2`, 768-d), vector search.
- `backend/app/bot/` — aiogram handlers, webhook route (secret-checked, enqueue + 200), polling/webhook registration service.
- `seed/nur_klinika/` — demo price list, FAQ, services/doctors (realistic but fictional).

## Run locally

Requirements: Docker Desktop, `make`. For development without Docker: [uv](https://docs.astral.sh/uv/).

1. `cp .env.example .env` and fill in `TELEGRAM_BOT_TOKEN`, `ANTHROPIC_API_KEY`, `TELEGRAM_WEBHOOK_SECRET`, `JWT_SECRET` and `ENCRYPTION_KEY`. Generate the Fernet key with:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. `make up` starts postgres, redis, s3 (SeaweedFS), langfuse, api, worker and bot.
3. `make seed` runs the migrations, creates Nur Klinika and indexes its documents. The first run downloads the embedding model (~1 GB).
4. Message the bot: `Stomatolog qabuli necha pul?` → "150 000 so'm", with "Manba: Narxlar ro'yxati".

With `PUBLIC_BASE_URL` empty, the bot service long-polls Telegram. When it is set, it registers `PUBLIC_BASE_URL/v1/telegram/webhook/<tenant>` instead.

## Development

```bash
make lint typecheck test   # ruff, mypy --strict, pytest
```

The integration tests use testcontainers (`pgvector/pgvector:pg16`) and are skipped when Docker isn't available. CI runs them.

## Eval results

Evals start in M2. Retrieval improvements will be tracked here.
