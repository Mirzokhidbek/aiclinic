# CLAUDE.md

This project follows the spec in [BUILD.md](BUILD.md). It is the single source of truth: read it before any work and follow it strictly.

@BUILD.md

## Mandatory rules (summary — BUILD.md wins on any conflict)

- **Milestones in order.** Work M1 → M8 sequentially. Do not start a milestone until the previous one meets every acceptance criterion in BUILD.md §10.
- **Fixed tech stack (§2).** Python 3.12 + `uv`, aiogram 3 (webhook), FastAPI + Pydantic v2 + SQLAlchemy 2 async + Alembic, `arq`, PostgreSQL 16 + pgvector, Redis 7, MinIO/S3, Langfuse, React 18 + TS + Vite + Tailwind for the Mini App. Do not swap any of these without asking.
- **No LangChain / LlamaIndex.** Build RAG and the agent loop directly on the `anthropic` SDK. Models: `claude-sonnet-5-5` (main), `claude-haiku-5-5` (fast, routing, judge).
- **Repository layout** must match §3.
- **Multi-tenancy:** every tenant-owned table has `tenant_id` + RLS policy; set `SET LOCAL app.tenant_id` per request/job. Never let the model choose `tenant_id` or `customer_id` — tools take them from request context.
- **Booking:** lock slot row with `SELECT ... FOR UPDATE`; bookings require `Idempotency-Key`.
- **Layering:** `booking/` must never import from `ai/`. Tools call into `booking/` and `retrieval/`, never the reverse.
- **Security:** no raw SQL with user input; no secrets or PII in logs/traces (masking helper is mandatory); secrets only from env, never committed.
- **Types:** type hints everywhere, mypy strict on `app/`, ruff clean; Pydantic models at every boundary.
- **Prompts** are versioned files (`ai/prompts/system_v1.md`, ...); record prompt version on each trace.
- **Evals:** every new AI behavior ships with eval items in the same PR (§8 gates).
- **API errors** use `{"error": {"code": "...", "message": "..."}}`; all routes under `/v1`.
- **Git:** small PRs, Conventional Commits.
