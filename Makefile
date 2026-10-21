.PHONY: up down logs migrate seed test lint fmt typecheck check

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
