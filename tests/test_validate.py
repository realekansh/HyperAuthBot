import hashlib
import hmac
from datetime import UTC, datetime
from urllib.parse import urlencode

from webapp.api.validate import validate_init_data


def signed_init_data(payload: dict[str, str], bot_token: str) -> str:
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**payload, "hash": digest})


def test_validate_init_data_accepts_valid_signature() -> None:
    token = "123456789:TEST_TOKEN"
    init_data = signed_init_data(
        {"auth_date": str(int(datetime.now(UTC).timestamp())), "query_id": "abc"},
        token,
    )

    assert validate_init_data(init_data, token) is True


def test_validate_init_data_rejects_tampering() -> None:
    token = "123456789:TEST_TOKEN"
    init_data = signed_init_data(
        {"auth_date": str(int(datetime.now(UTC).timestamp())), "query_id": "abc"},
        token,
    )

    assert validate_init_data(init_data.replace("abc", "def"), token) is False


def test_validate_init_data_rejects_missing_hash() -> None:
    assert validate_init_data("auth_date=1720000000", "123456789:TEST_TOKEN") is False


def test_validate_init_data_rejects_stale_auth_date() -> None:
    token = "123456789:TEST_TOKEN"
    init_data = signed_init_data({"auth_date": "1720000000", "query_id": "abc"}, token)

    assert validate_init_data(init_data, token) is False
