"""Verify Telegram Mini App initData (https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)."""

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl

from pydantic import BaseModel

MAX_AGE = timedelta(hours=24)


class InvalidInitDataError(ValueError):
    pass


class TelegramUser(BaseModel):
    id: int
    first_name: str = ""
    last_name: str = ""
    username: str | None = None
    language_code: str | None = None

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.first_name, self.last_name) if p) or (self.username or "")


class InitData(BaseModel):
    user: TelegramUser
    auth_date: datetime
    start_param: str | None = None


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def sign_init_data(fields: dict[str, str], bot_token: str) -> str:
    """Build a signed initData query string (used by tests and local dev tooling)."""
    from urllib.parse import urlencode

    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    digest = hmac.new(_secret_key(bot_token), check.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": digest})


def verify_init_data(
    init_data: str, bot_token: str, *, now: datetime | None = None, max_age: timedelta = MAX_AGE
) -> InitData:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received = pairs.pop("hash", None)
    if not received:
        raise InvalidInitDataError("missing hash")
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    expected = hmac.new(_secret_key(bot_token), check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise InvalidInitDataError("bad signature")

    try:
        auth_date = datetime.fromtimestamp(int(pairs["auth_date"]), UTC)
        user = TelegramUser.model_validate(json.loads(pairs["user"]))
    except (KeyError, ValueError) as exc:
        raise InvalidInitDataError("malformed initData") from exc
    current = now or datetime.now(UTC)
    if current - auth_date > max_age:
        raise InvalidInitDataError("initData expired")
    return InitData(user=user, auth_date=auth_date, start_param=pairs.get("start_param"))
