import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.booking.models import Service, Slot
from app.booking.service import BookingView


class ServiceOut(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    price_uzs: int
    duration_min: int
    description: str

    @classmethod
    def of(cls, s: Service) -> "ServiceOut":
        return cls(
            id=s.id,
            name=s.name,
            category=s.category,
            price_uzs=s.price_uzs,
            duration_min=s.duration_min,
            description=s.description,
        )


class SlotOut(BaseModel):
    id: uuid.UUID
    starts_at: datetime
    seats_left: int

    @classmethod
    def of(cls, s: Slot) -> "SlotOut":
        return cls(id=s.id, starts_at=s.starts_at, seats_left=s.capacity - s.booked_count)


class AvailabilityOut(BaseModel):
    service: ServiceOut
    date: str
    slots: list[SlotOut]


class BookingCreate(BaseModel):
    slot_id: uuid.UUID


class BookingConfirm(BaseModel):
    confirm_token: str = Field(min_length=8, max_length=64)


class BookingOut(BaseModel):
    id: uuid.UUID
    status: str
    starts_at: datetime
    expires_at: datetime | None
    service: ServiceOut
    confirm_token: str | None = None

    @classmethod
    def of(cls, v: BookingView, *, with_token: bool = False) -> "BookingOut":
        return cls(
            id=v.booking.id,
            status=v.booking.status,
            starts_at=v.slot.starts_at,
            expires_at=v.booking.expires_at,
            service=ServiceOut.of(v.service),
            confirm_token=v.booking.confirm_token if with_token else None,
        )
