from datetime import UTC, datetime
from urllib.parse import urlencode

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.database import add_group, create_pending_verification
from bot.models import Base
from webapp.api.validate import validate_init_data
from webapp.server import create_app


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'verify.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def signed_init_data(payload: dict[str, str], bot_token: str) -> str:
    import hashlib
    import hmac

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**payload, "hash": digest})


class FakeBot:
    def __init__(self) -> None:
        self.methods = []
        self.approved = []
        self.declined = []

    async def __call__(self, method):
        self.methods.append(method)
        return True

    async def approve_chat_join_request(self, chat_id: int, user_id: int):
        self.approved.append((chat_id, user_id))
        return True

    async def decline_chat_join_request(self, chat_id: int, user_id: int):
        self.declined.append((chat_id, user_id))
        return True


class FakeDispatcher:
    async def feed_update(self, bot, update):
        return None


@pytest.mark.asyncio
async def test_api_verify_accepts_signed_init_data_and_completes(session_factory, monkeypatch):
    import webapp.server as server

    monkeypatch.setattr(server, "SessionFactory", session_factory)
    fake_bot = FakeBot()
    app = create_app(fake_bot, FakeDispatcher())

    async with session_factory() as session:
        group = await add_group(session, -1001, "Verify Group", 123456789)
        verification = await create_pending_verification(
            session=session,
            user_id=42,
            user_chat_id=4200,
            chat_id=group.chat_id,
            query_id="query-1",
        )

    init_data = signed_init_data(
        {
            "auth_date": str(int(datetime.now(UTC).timestamp())),
            "query_id": "abc",
            "user": "{\"id\":42}",
        },
        "123456789:TEST_TOKEN",
    )
    assert validate_init_data(init_data, "123456789:TEST_TOKEN") is True

    with TestClient(app) as client:
        response = client.post(
            "/api/verify",
            json={
                "token": verification.token,
                "action": "agree",
                "initData": init_data,
            },
        )

    assert response.status_code == 200
    assert response.json()["ok"] is True


@pytest.mark.asyncio
async def test_api_verify_rejects_invalid_signature(session_factory, monkeypatch):
    import webapp.server as server

    monkeypatch.setattr(server, "SessionFactory", session_factory)
    app = create_app(FakeBot(), FakeDispatcher())

    with TestClient(app) as client:
        response = client.post(
            "/api/verify",
            json={
                "token": "abc123",
                "action": "agree",
                "initData": "auth_date=1720000000&user=%7B%22id%22%3A42%7D&hash=bad",
            },
        )

    assert response.status_code == 403
    assert response.json()["ok"] is False


@pytest.mark.asyncio
async def test_webapp_response_is_no_store_and_versioned(session_factory, monkeypatch):
    import webapp.server as server

    monkeypatch.setattr(server, "SessionFactory", session_factory)
    fake_bot = FakeBot()
    app = create_app(fake_bot, FakeDispatcher())

    async with session_factory() as session:
        group = await add_group(session, -1002, "Cache Group", 123456789)
        verification = await create_pending_verification(
            session=session,
            user_id=42,
            user_chat_id=4200,
            chat_id=group.chat_id,
            query_id="query-cache",
        )

    with TestClient(app) as client:
        response = client.get(f"/webapp?token={verification.token}")

    assert response.status_code == 200
    assert response.headers["cache-control"].startswith("no-store")
    assert "?v=" in response.text
    assert "/static/app.js?v=" in response.text
    assert "/static/style.css?v=" in response.text


@pytest.mark.asyncio
async def test_webapp_invalid_token_returns_styled_error_page(session_factory, monkeypatch):
    import webapp.server as server

    monkeypatch.setattr(server, "SessionFactory", session_factory)
    app = create_app(FakeBot(), FakeDispatcher())

    with TestClient(app) as client:
        response = client.get("/webapp?token=doesnotexist")

    assert response.status_code == 200
    assert "window.__HYPERAUTH_STATE__" in response.text
    assert '"errorMessage": "Invalid or expired session."' in response.text
    assert 'id="page-error"' in response.text
