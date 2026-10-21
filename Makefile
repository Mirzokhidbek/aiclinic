.PHONY: up down logs migrate seed test lint fmt typecheck check openapi miniapp-dev miniapp-link e2e

COMPOSE := docker compose
BACKEND := cd backend &&

up:            ## Start the full stack
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api worker bot

migrate:       ## Apply DB migrations
	$(COMPOSE) exec api alembic upgrade head

seed: migrate  ## Seed demo tenants and index their documents
	$(COMPOSE) exec api python -m app.seed /seed

test:
	$(BACKEND) TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE=/var/run/docker.sock uv run pytest

lint:
	$(BACKEND) uv run ruff check . && uv run ruff format --check .

fmt:
	$(BACKEND) uv run ruff check --fix . && uv run ruff format .

typecheck:
	$(BACKEND) uv run mypy

check: lint typecheck test

openapi:       ## Regenerate OpenAPI schema and the Mini App's typed client
	$(BACKEND) uv run python -m app.openapi_dump openapi.json
	cd miniapp && npm run gen:api

miniapp-dev:   ## Mini App dev server on :5173 (proxies /v1 to the API)
	cd miniapp && npm run dev

miniapp-link:  ## Print a signed URL that opens the Mini App in a browser as a Telegram user
	cd miniapp && npm run -s dev:link

e2e:           ## Playwright booking flow against the running stack
	cd miniapp && npx playwright test
