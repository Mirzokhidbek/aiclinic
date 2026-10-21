"""M4 booking flow through the HTTP API on a real Postgres."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.telegram import sign_init_data
from app.booking.models import Slot
from app.booking.service import expire_pending
from app.db import tenant_session
from app.main import create_app
from app.retrieval.embeddings import HashingEmbedder
from app.seed import seed_tenant
from app.tenants.models import Tenant

SEED = Path(__file__).resolve().parents[3] / "seed" / "nur_klinika"
BOT_TOKEN = "123456:test-token"
TZ = ZoneInfo("Asia/Tashkent")


class NoopPool:
    async def enqueue_job(self, *args: Any, **kwargs: Any) -> None: ...


@pytest.fixture(scope="module")
async def tenant(sessionmaker: async_sessionmaker[AsyncSession]) -> Tenant:
    return await seed_tenant(sessionmaker, SEED, HashingEmbedder())


@pytest.fixture
async def client(tenant: Tenant) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.state.arq = NoopPool()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def login(client: httpx.AsyncClient, telegram_id: int) -> dict[str, str]:
    init_data = sign_init_data(
        {
            "auth_date": str(int(datetime.now(UTC).timestamp())),
            "user": json.dumps({"id": telegram_id, "first_name": f"User{telegram_id}"}),
        },
        BOT_TOKEN,
    )
    r = await client.post(
        "/v1/auth/telegram", json={"init_data": init_data, "tenant_slug": "nur-klinika"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def key() -> dict[str, str]:
    return {"Idempotency-Key": uuid.uuid4().hex}


async def first_free_slot(client: httpx.AsyncClient, auth: dict[str, str], name: str) -> str:
    services = (await client.get("/v1/services", headers=auth)).json()
    service = next(s for s in services if s["name"] == name)
    tomorrow = (datetime.now(TZ) + timedelta(days=1)).date().isoformat()
    r = await client.get(
        f"/v1/services/{service['id']}/availability", params={"date": tomorrow}, headers=auth
    )
    assert r.status_code == 200, r.text
    slots = r.json()["slots"]
    assert slots, "seed should create slots for tomorrow"
    return str(slots[0]["id"])


async def test_auth_rejects_bad_init_data(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/v1/auth/telegram",
        json={"init_data": "auth_date=1&user=%7B%7D&hash=bad", "tenant_slug": "nur-klinika"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_init_data"


async def test_requires_token(client: httpx.AsyncClient) -> None:
    r = await client.get("/v1/services")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


async def test_services_catalog(client: httpx.AsyncClient) -> None:
    auth = await login(client, 1001)
    services = (await client.get("/v1/services", headers=auth)).json()
    by_name = {s["name"]: s for s in services}
    assert by_name["Stomatolog qabuli"]["price_uzs"] == 150000
    dental = (
        await client.get("/v1/services", params={"category": "Diagnostika"}, headers=auth)
    ).json()
    assert {s["category"] for s in dental} == {"Diagnostika"}


async def test_book_confirm_cancel_flow(client: httpx.AsyncClient) -> None:
    auth = await login(client, 1002)
    slot_id = await first_free_slot(client, auth, "Terapevt qabuli")

    r = await client.post("/v1/bookings", json={"slot_id": slot_id}, headers=auth)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "idempotency_key_required"

    idem = key()
    r = await client.post("/v1/bookings", json={"slot_id": slot_id}, headers={**auth, **idem})
    assert r.status_code == 201, r.text
    booking = r.json()
    assert booking["status"] == "pending" and booking["confirm_token"]

    # Same Idempotency-Key -> same booking, no second seat taken
    replay = await client.post("/v1/bookings", json={"slot_id": slot_id}, headers={**auth, **idem})
    assert replay.status_code == 201 and replay.json()["id"] == booking["id"]

    bad = await client.post(
        f"/v1/bookings/{booking['id']}/confirm",
        json={"confirm_token": "wrong-token"},
        headers=auth,
    )
    assert bad.status_code == 404

    ok = await client.post(
        f"/v1/bookings/{booking['id']}/confirm",
        json={"confirm_token": booking["confirm_token"]},
        headers=auth,
    )
    assert ok.status_code == 200 and ok.json()["status"] == "confirmed"
    assert ok.json()["confirm_token"] is None

    mine = (await client.get("/v1/bookings/me", headers=auth)).json()
    assert [b["id"] for b in mine] == [booking["id"]]

    # Another customer can't see or cancel it
    other = await login(client, 1003)
    assert (await client.get(f"/v1/bookings/{booking['id']}", headers=other)).status_code == 404
    r = await client.post(f"/v1/bookings/{booking['id']}/cancel", headers=other)
    assert r.status_code == 404

    cancelled = await client.post(f"/v1/bookings/{booking['id']}/cancel", headers=auth)
    assert cancelled.json()["status"] == "cancelled"
    # seat is free again
    assert await first_free_slot(client, auth, "Terapevt qabuli") == slot_id


async def test_double_booking_is_impossible(
    client: httpx.AsyncClient, sessionmaker: async_sessionmaker[AsyncSession], tenant: Tenant
) -> None:
    customers = [await login(client, 2000 + i) for i in range(10)]
    slot_id = await first_free_slot(client, customers[0], "Kardiolog qabuli")

    responses = await asyncio.gather(
        *(
            client.post("/v1/bookings", json={"slot_id": slot_id}, headers={**auth, **key()})
            for auth in customers
        )
    )
    codes = sorted(r.status_code for r in responses)
    assert codes == [201] + [409] * 9, [r.text for r in responses]
    assert {r.json()["error"]["code"] for r in responses if r.status_code == 409} == {"slot_full"}

    async with tenant_session(tenant.id, sessionmaker) as s:
        slot = (await s.execute(select(Slot).where(Slot.id == uuid.UUID(slot_id)))).scalar_one()
    assert slot.booked_count == 1 == slot.capacity


async def test_pending_booking_expires_and_releases_seat(
    client: httpx.AsyncClient, sessionmaker: async_sessionmaker[AsyncSession], tenant: Tenant
) -> None:
    auth = await login(client, 3001)
    slot_id = await first_free_slot(client, auth, "Nevrolog qabuli")
    booking = (
        await client.post("/v1/bookings", json={"slot_id": slot_id}, headers={**auth, **key()})
    ).json()

    async with tenant_session(tenant.id, sessionmaker) as s:
        assert await expire_pending(s, tenant.id, datetime.now(UTC)) == 0
        # >= 1: pending bookings left by earlier tests expire too
        assert await expire_pending(s, tenant.id, datetime.now(UTC) + timedelta(minutes=16)) >= 1

    r = await client.post(
        f"/v1/bookings/{booking['id']}/confirm",
        json={"confirm_token": booking["confirm_token"]},
        headers=auth,
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "booking_not_pending"
    assert await first_free_slot(client, auth, "Nevrolog qabuli") == slot_id
