"""Seed services and generate bookable slots from seed/<tenant>/services.json."""

import uuid
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.models import Service, Slot


def _parse(hhmm: str) -> time:
    hours, minutes = hhmm.split(":")
    return time(int(hours), int(minutes))


def slot_times(
    start_day: date, days: int, hours: dict[str, list[str]], duration_min: int, tz: ZoneInfo
) -> list[datetime]:
    """Back-to-back appointment start times inside working hours for each day."""
    step = timedelta(minutes=max(30, duration_min))
    result: list[datetime] = []
    for offset in range(days):
        day = start_day + timedelta(days=offset)
        opening, closing = hours["sunday" if day.weekday() == 6 else "weekday"]
        current = datetime.combine(day, _parse(opening), tzinfo=tz)
        end = datetime.combine(day, _parse(closing), tzinfo=tz)
        while current + timedelta(minutes=duration_min) <= end:
            result.append(current)
            current += step
    return result


async def seed_services(
    session: AsyncSession, tenant_id: uuid.UUID, spec: dict[str, Any], tz: ZoneInfo, today: date
) -> tuple[int, int]:
    services = 0
    slots = 0
    for item in spec["services"]:
        stmt = (
            insert(Service)
            .values(id=uuid.uuid4(), tenant_id=tenant_id, active=True, **item)
            .on_conflict_do_update(
                index_elements=[Service.tenant_id, Service.name],
                set_={k: item[k] for k in ("category", "price_uzs", "duration_min", "description")},
            )
            .returning(Service.id)
        )
        service_id = (await session.execute(stmt)).scalar_one()
        services += 1
        times = slot_times(today, spec["slot_days"], spec["hours"], item["duration_min"], tz)
        if times:
            result = await session.execute(
                insert(Slot)
                .values(
                    [
                        {
                            "id": uuid.uuid4(),
                            "tenant_id": tenant_id,
                            "service_id": service_id,
                            "starts_at": t,
                            "capacity": 1,
                            "booked_count": 0,
                        }
                        for t in times
                    ]
                )
                .on_conflict_do_nothing(index_elements=[Slot.service_id, Slot.starts_at])
                .returning(Slot.id)
            )
            slots += len(result.all())
    return services, slots
