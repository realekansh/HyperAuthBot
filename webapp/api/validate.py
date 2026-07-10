import hashlib
import hmac
from datetime import UTC, datetime
import json
from urllib.parse import parse_qsl


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> bool:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", "")
    if not received_hash:
        return False

    auth_date = pairs.get("auth_date")
    if not auth_date:
        return False

    try:
        auth_date_int = int(auth_date)
    except ValueError:
        return False

    now = int(datetime.now(UTC).timestamp())
    if auth_date_int > now or now - auth_date_int > max_age_seconds:
        return False

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_hash, received_hash)


def extract_init_data_user_id(init_data: str) -> int | None:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    user = pairs.get("user")
    if not user:
        return None

    try:
        payload = json.loads(user)
    except json.JSONDecodeError:
        return None

    user_id = payload.get("id")
    return int(user_id) if isinstance(user_id, int) else None
