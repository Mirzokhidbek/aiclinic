from collections.abc import AsyncIterator
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import Principal, decode_token
from app.db import tenant_session
from app.errors import ApiError

_bearer = HTTPBearer(auto_error=False)


async def current_principal(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if creds is None:
        raise ApiError(401, "unauthorized", "Missing bearer token")
    try:
        return decode_token(creds.credentials)
    except jwt.PyJWTError as exc:
        raise ApiError(401, "unauthorized", "Invalid or expired token") from exc


async def current_customer(
    principal: Annotated[Principal, Depends(current_principal)],
) -> Principal:
    if principal.role != "customer":
        raise ApiError(403, "forbidden", "Customer access only")
    return principal


async def customer_session(
    principal: Annotated[Principal, Depends(current_customer)],
) -> AsyncIterator[AsyncSession]:
    """Request-scoped transaction bound to the caller's tenant (never to client input)."""
    async with tenant_session(principal.tenant_id) as session:
        yield session


CustomerDep = Annotated[Principal, Depends(current_customer)]
CustomerSessionDep = Annotated[AsyncSession, Depends(customer_session)]
