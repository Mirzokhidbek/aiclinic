import uuid
from datetime import UTC, date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, Query

from app.auth.deps import CustomerDep, CustomerSessionDep
from app.booking import service
from app.booking.schemas import (
    AvailabilityOut,
    BookingConfirm,
    BookingCreate,
    BookingOut,
    ServiceOut,
    SlotOut,
)
from app.errors import ApiError
from app.tenants.service import get_tenant, tenant_settings

router = APIRouter(prefix="/v1", tags=["booking"])


def _now() -> datetime:
    return datetime.now(UTC)


@router.get("/services", response_model=list[ServiceOut])
async def list_services(
    principal: CustomerDep, session: CustomerSessionDep, category: str | None = None
) -> list[ServiceOut]:
    services = await service.list_services(session, principal.tenant_id, category)
    return [ServiceOut.of(s) for s in services]


@router.get("/services/{service_id}", response_model=ServiceOut)
async def get_service(
    service_id: uuid.UUID, principal: CustomerDep, session: CustomerSessionDep
) -> ServiceOut:
    return ServiceOut.of(await service.get_service(session, principal.tenant_id, service_id))


@router.get("/services/{service_id}/availability", response_model=AvailabilityOut)
async def availability(
    service_id: uuid.UUID,
    principal: CustomerDep,
    session: CustomerSessionDep,
    day: Annotated[date, Query(alias="date")],
) -> AvailabilityOut:
    tenant = await get_tenant(session, principal.tenant_id)
    tz = ZoneInfo(tenant_settings(tenant).timezone)
    svc = await service.get_service(session, principal.tenant_id, service_id)
    slots = await service.available_slots(session, principal.tenant_id, service_id, day, tz, _now())
    return AvailabilityOut(
        service=ServiceOut.of(svc), date=day.isoformat(), slots=[SlotOut.of(s) for s in slots]
    )


@router.post("/bookings", response_model=BookingOut, status_code=201)
async def create_booking(
    body: BookingCreate,
    principal: CustomerDep,
    session: CustomerSessionDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> BookingOut:
    if not idempotency_key or not 8 <= len(idempotency_key) <= 128:
        raise ApiError(400, "idempotency_key_required", "Idempotency-Key header is required")
    view = await service.create_booking(
        session,
        tenant_id=principal.tenant_id,
        customer_id=principal.subject_id,
        slot_id=body.slot_id,
        idempotency_key=idempotency_key,
        now=_now(),
    )
    return BookingOut.of(view, with_token=view.booking.status == "pending")


@router.get("/bookings/me", response_model=list[BookingOut])
async def my_bookings(principal: CustomerDep, session: CustomerSessionDep) -> list[BookingOut]:
    views = await service.my_bookings(session, principal.tenant_id, principal.subject_id)
    return [BookingOut.of(v) for v in views]


@router.get("/bookings/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: uuid.UUID, principal: CustomerDep, session: CustomerSessionDep
) -> BookingOut:
    view = await service.get_booking(session, principal.tenant_id, principal.subject_id, booking_id)
    return BookingOut.of(view)


@router.post("/bookings/{booking_id}/confirm", response_model=BookingOut)
async def confirm_booking(
    booking_id: uuid.UUID,
    body: BookingConfirm,
    principal: CustomerDep,
    session: CustomerSessionDep,
) -> BookingOut:
    view = await service.confirm_booking(
        session,
        tenant_id=principal.tenant_id,
        customer_id=principal.subject_id,
        booking_id=booking_id,
        confirm_token=body.confirm_token,
        now=_now(),
    )
    return BookingOut.of(view)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: uuid.UUID, principal: CustomerDep, session: CustomerSessionDep
) -> BookingOut:
    view = await service.cancel_booking(
        session,
        tenant_id=principal.tenant_id,
        customer_id=principal.subject_id,
        booking_id=booking_id,
        now=_now(),
    )
    return BookingOut.of(view)
