import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pydantic import BaseModel

from app.config import get_settings

ALGORITHM = "HS256"
TTL = timedelta(hours=12)

Role = Literal["customer", "owner", "operator"]


class Principal(BaseModel):
    tenant_id: uuid.UUID
    subject_id: uuid.UUID  # customer_id for customers, user_id for staff
    role: Role


def _secret() -> str:
    secret = get_settings().jwt_secret.get_secret_value()
    if not secret:
        raise RuntimeError("JWT_SECRET is not set")
    return secret


def issue_token(principal: Principal, now: datetime | None = None) -> str:
    issued = now or datetime.now(UTC)
    payload = {
        "sub": str(principal.subject_id),
        "tid": str(principal.tenant_id),
        "role": principal.role,
        "iat": int(issued.timestamp()),
        "exp": int((issued + TTL).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> Principal:
    payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM], options={"require": ["exp"]})
    return Principal(
        tenant_id=uuid.UUID(payload["tid"]),
        subject_id=uuid.UUID(payload["sub"]),
        role=payload["role"],
    )
