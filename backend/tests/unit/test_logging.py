import json
import logging

from app.observability.logging import JsonFormatter, mask_pii


def test_mask_pii() -> None:
    text = "Tel: +998 90 123 45 67, email ali@example.com, karta 8600 1234 5678 9012"
    masked = mask_pii(text)
    assert "123 45 67" not in masked
    assert "ali@example.com" not in masked
    assert "8600" not in masked
    assert "[PHONE]" in masked and "[EMAIL]" in masked and "[CARD]" in masked


def test_mask_bot_token() -> None:
    assert mask_pii("token 1234567890:AAFakeTokenForTestsOnly_abcdefghijklmn") == "token [TOKEN]"


def test_prices_are_not_masked() -> None:
    assert mask_pii("Narxi 150 000 so'm") == "Narxi 150 000 so'm"


def test_json_formatter_masks_extra_fields() -> None:
    record = logging.makeLogRecord(
        {"msg": "call +998901234567", "levelname": "INFO", "name": "t", "phone": "+998901234567"}
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["msg"] == "call [PHONE]"
    assert payload["phone"] == "[PHONE]"
