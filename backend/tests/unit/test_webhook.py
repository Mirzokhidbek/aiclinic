from typing import Any

import httpx

from app.main import create_app


class FakePool:
    def __init__(self) -> None:
        self.jobs: list[tuple[Any, ...]] = []

    async def enqueue_job(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.jobs.append((name, *args))


def client(pool: FakePool) -> httpx.AsyncClient:
    app = create_app()
    app.state.arq = pool
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_rejects_bad_secret() -> None:
    pool = FakePool()
    async with client(pool) as c:
        r = await c.post(
            "/v1/telegram/webhook/nur-klinika",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        )
    assert r.status_code == 401
    assert r.json() == {"error": {"code": "invalid_secret", "message": "Invalid webhook secret"}}
    assert pool.jobs == []


async def test_rejects_missing_secret() -> None:
    async with client(FakePool()) as c:
        r = await c.post("/v1/telegram/webhook/nur-klinika", json={"update_id": 1})
    assert r.status_code == 401


async def test_enqueues_valid_update() -> None:
    pool = FakePool()
    update = {"update_id": 7, "message": {"text": "salom"}}
    async with client(pool) as c:
        r = await c.post(
            "/v1/telegram/webhook/nur-klinika",
            json=update,
            headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        )
    assert r.status_code == 200
    assert pool.jobs == [("process_update", "nur-klinika", update)]


async def test_health() -> None:
    async with client(FakePool()) as c:
        r = await c.get("/health")
    assert r.json() == {"status": "ok"}
