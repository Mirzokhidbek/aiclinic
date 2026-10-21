import json
from datetime import UTC, datetime, timedelta

import pytest

from app.auth.telegram import InvalidInitDataError, sign_init_data, verify_init_data

TOKEN = "123456:test-token"
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


def init_data(auth_date: datetime = NOW, **extra: str) -> str:
    user = {"id": 42, "first_name": "Ali", "last_name": "Valiyev", "language_code": "uz"}
    fields = {
        "auth_date": str(int(auth_date.timestamp())),
        "query_id": "AAE",
        "user": json.dumps(user, separators=(",", ":")),
        **extra,
    }
    return sign_init_data(fields, TOKEN)


def test_valid_init_data() -> None:
    data = verify_init_data(init_data(start_param="nur-klinika"), TOKEN, now=NOW)
    assert data.user.id == 42
    assert data.user.full_name == "Ali Valiyev"
    assert data.start_param == "nur-klinika"


def test_signature_field_is_part_of_check_string() -> None:
    raw = init_data(signature="abc")
    assert verify_init_data(raw, TOKEN, now=NOW).user.id == 42
    with pytest.raises(InvalidInitDataError):
        verify_init_data(raw.replace("signature=abc", "signature=xyz"), TOKEN, now=NOW)


def test_rejects_tampered_user() -> None:
    raw = init_data().replace("%22id%22%3A42", "%22id%22%3A43")
    with pytest.raises(InvalidInitDataError, match="signature"):
        verify_init_data(raw, TOKEN, now=NOW)


def test_rejects_other_bot_token() -> None:
    with pytest.raises(InvalidInitDataError):
        verify_init_data(init_data(), "999:other", now=NOW)


def test_rejects_old_auth_date() -> None:
    with pytest.raises(InvalidInitDataError, match="expired"):
        verify_init_data(init_data(NOW - timedelta(hours=25)), TOKEN, now=NOW)


def test_rejects_missing_hash() -> None:
    with pytest.raises(InvalidInitDataError):
        verify_init_data("auth_date=1&user=%7B%7D", TOKEN, now=NOW)
