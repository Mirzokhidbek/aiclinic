"""Services, slots and bookings. Pure business logic: must never import from app.ai."""

import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.errors import ConflictError, GoneError, NotFoundError
from app.booking.models import Booking, Service, Slot

PENDING_TTL = timedelta(minutes=15)
ACTIVE_STATUSES = ("pending", "confirmed")


@dataclass(frozen=True)
class BookingView:
    booking: Booking
    slot: Slot
    service: Service


async def list_services(
    session: AsyncSession, tenant_id: uuid.UUID, category: str | None = None
) -> list[Service]:
    stmt = select(Service).where(Service.tenant_id == tenant_id, Service.active.is_(True))
    if category:
        stmt = stmt.where(Service.category == category)
    result = await session.execute(stmt.order_by(Service.category, Service.price_uzs))
    return list(result.scalars())


async def get_service(
    session: AsyncSession, tenant_id: uuid.UUID, service_id: uuid.UUID
) -> Service:
    service = (
        await session.execute(
            select(Service).where(
                Service.id == service_id, Service.tenant_id == tenant_id, Service.active.is_(True)
            )
        )
    ).scalar_one_or_none()
    if service is None:
        raise NotFoundError("service_not_found", "Service not found")
    return service


async def available_slots(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
    day: date,
    tz: ZoneInfo,
    now: datetime,
) -> list[Slot]:
    await get_service(session, tenant_id, service_id)
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = start + timedelta(days=1)
    result = await session.execute(
        select(Slot)
        .where(
            Slot.tenant_id == tenant_id,
            Slot.service_id == service_id,
            Slot.starts_at >= max(start, now),
            Slot.starts_at < end,
            Slot.booked_count < Slot.capacity,
        )
        .order_by(Slot.starts_at)
    )
    return list(result.scalars())


async def _view(session: AsyncSession, booking: Booking) -> BookingView:
    row = (
        await session.execute(
            select(Slot, Service)
            .join(Service, Service.id == Slot.service_id)
            .where(Slot.id == booking.slot_id)
        )
    ).one()
    return BookingView(booking=booking, slot=row[0], service=row[1])


async def _by_idempotency_key(
    session: AsyncSession, tenant_id: uuid.UUID, key: str
) -> Booking | None:
    return (
        await session.execute(
            select(Booking).where(Booking.tenant_id == tenant_id, Booking.idempotency_key == key)
        )
    ).scalar_one_or_none()


def _replay(existing: Booking, customer_id: uuid.UUID, slot_id: uuid.UUID) -> Booking:
    if existing.customer_id != customer_id or existing.slot_id != slot_id:
        raise ConflictError(
            "idempotency_key_reused", "Idempotency key was used for another request"
        )
    return existing


async def create_booking(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    slot_id: uuid.UUID,
    idempotency_key: str,
    now: datetime,
) -> BookingView:
    """Hold one seat in the slot as a pending booking that expires in 15 minutes.

    The slot row is locked (SELECT ... FOR UPDATE) so concurrent requests for the same
    slot are serialized and booked_count can never exceed capacity.
    """
    existing = await _by_idempotency_key(session, tenant_id, idempotency_key)
    if existing is not None:
        return await _view(session, _replay(existing, customer_id, slot_id))

    slot = (
        await session.execute(
            select(Slot).where(Slot.id == slot_id, Slot.tenant_id == tenant_id).with_for_update()
        )
    ).scalar_one_or_none()
    if slot is None:
        raise NotFoundError("slot_not_found", "Slot not found")

    # A concurrent request with the same key may have committed while we waited for the lock.
    existing = await _by_idempotency_key(session, tenant_id, idempotency_key)
    if existing is not None:
        return await _view(session, _replay(existing, customer_id, slot_id))

    if slot.starts_at <= now:
        raise GoneError("slot_in_past", "This time has already passed")
    duplicate = (
        await session.execute(
            select(Booking.id).where(
                Booking.tenant_id == tenant_id,
                Booking.customer_id == customer_id,
                Booking.slot_id == slot_id,
                Booking.status.in_(ACTIVE_STATUSES),
            )
        )
    ).first()
    if duplicate is not None:
        raise ConflictError("already_booked", "You already have a booking for this time")
    if slot.booked_count >= slot.capacity:
        raise ConflictError("slot_full", "This time is already taken")

    slot.booked_count += 1
    booking = Booking(
        tenant_id=tenant_id,
        customer_id=customer_id,
        slot_id=slot.id,
        status="pending",
        confirm_token=secrets.token_urlsafe(24),
        idempotency_key=idempotency_key,
        expires_at=now + PENDING_TTL,
    )
    session.add(booking)
    await session.flush()
    return await _view(session, booking)


async def _lock_booking(
    session: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID, booking_id: uuid.UUID
) -> Booking:
    booking = (
        await session.execute(
            select(Booking)
            .where(
                Booking.id == booking_id,
                Booking.tenant_id == tenant_id,
                Booking.customer_id == customer_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if booking is None:
        raise NotFoundError("booking_not_found", "Booking not found")
    return booking


async def _release_seat(session: AsyncSession, booking: Booking) -> None:
    slot = (
        await session.execute(select(Slot).where(Slot.id == booking.slot_id).with_for_update())
    ).scalar_one()
    slot.booked_count = max(0, slot.booked_count - 1)


async def get_booking(
    session: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID, booking_id: uuid.UUID
) -> BookingView:
    booking = (
        await session.execute(
            select(Booking).where(
                Booking.id == booking_id,
                Booking.tenant_id == tenant_id,
                Booking.customer_id == customer_id,
            )
        )
    ).scalar_one_or_none()
    if booking is None:
        raise NotFoundError("booking_not_found", "Booking not found")
    return await _view(session, booking)


async def confirm_booking(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    booking_id: uuid.UUID,
    confirm_token: str,
    now: datetime,
) -> BookingView:
    booking = await _lock_booking(session, tenant_id, customer_id, booking_id)
    if not hmac.compare_digest(booking.confirm_token, confirm_token):
        raise NotFoundError("booking_not_found", "Booking not found")
    if booking.status == "confirmed":
        return await _view(session, booking)
    if booking.status != "pending":
        raise ConflictError("booking_not_pending", f"Booking is {booking.status}")
    if booking.expires_at is not None and booking.expires_at <= now:
        await _release_seat(session, booking)
        booking.status = "cancelled"
        raise GoneError("booking_expired", "The reservation expired, please choose a time again")
    booking.status = "confirmed"
    booking.expires_at = None
    return await _view(session, booking)


async def cancel_booking(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    booking_id: uuid.UUID,
    now: datetime,
) -> BookingView:
    booking = await _lock_booking(session, tenant_id, customer_id, booking_id)
    if booking.status == "cancelled":
        return await _view(session, booking)
    view = await _view(session, booking)
    if view.slot.starts_at <= now:
        raise ConflictError("booking_in_past", "Past bookings can't be cancelled")
    await _release_seat(session, booking)
    booking.status = "cancelled"
    booking.expires_at = None
    return view


async def my_bookings(
    session: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID
) -> list[BookingView]:
    rows = (
        await session.execute(
            select(Booking, Slot, Service)
            .join(Slot, Slot.id == Booking.slot_id)
            .join(Service, Service.id == Slot.service_id)
            .where(Booking.tenant_id == tenant_id, Booking.customer_id == customer_id)
            .order_by(Slot.starts_at.desc())
        )
    ).all()
    return [BookingView(booking=b, slot=s, service=sv) for b, s, sv in rows]


async def expire_pending(session: AsyncSession, tenant_id: uuid.UUID, now: datetime) -> int:
    """Cancel pending bookings past their expiry and release their seats."""
    expired = (
        (
            await session.execute(
                select(Booking)
                .where(
                    Booking.tenant_id == tenant_id,
                    Booking.status == "pending",
                    Booking.expires_at <= now,
                )
                .with_for_update(skip_locked=True)
            )
        )
        .scalars()
        .all()
    )
    for booking in expired:
        await _release_seat(session, booking)
        booking.status = "cancelled"
    return len(expired)
