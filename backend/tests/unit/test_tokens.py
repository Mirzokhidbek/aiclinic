import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.auth.tokens import Principal, decode_token, issue_token


def test_roundtrip() -> None:
    p = Principal(tenant_id=uuid.uuid4(), subject_id=uuid.uuid4(), role="customer")
    assert decode_token(issue_token(p)) == p


def test_expired_token_rejected() -> None:
    p = Principal(tenant_id=uuid.uuid4(), subject_id=uuid.uuid4(), role="customer")
    token = issue_token(p, now=datetime.now(UTC) - timedelta(days=1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)
