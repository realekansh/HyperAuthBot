from datetime import timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.database import add_group, create_pending_verification
from bot.models import Base
from bot.services.verification import complete_verification
from bot.utils.bot_api_10_1 import AnswerChatJoinRequestQuery
from bot.utils.time import utcnow_naive


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db_session:
        yield db_session
    await engine.dispose()


class FakeBot:
    def __init__(self) -> None:
        self.methods: list = []
        self.approved: list[tuple[int, int]] = []
        self.declined: list[tuple[int, int]] = []

    async def __call__(self, method):
        self.methods.append(method)
        return True

    async def approve_chat_join_request(self, chat_id: int, user_id: int):
        self.approved.append((chat_id, user_id))
        return True

    async def decline_chat_join_request(self, chat_id: int, user_id: int):
        self.declined.append((chat_id, user_id))
        return True


@pytest.mark.asyncio
async def test_complete_verification_agree_uses_custom_query_method(session) -> None:
    group = await add_group(session, -1001, "Test Group", 123456789)
    verification = await create_pending_verification(
        session=session,
        user_id=42,
        user_chat_id=4200,
        chat_id=group.chat_id,
        query_id="query-1",
    )

    bot = FakeBot()
    result = await complete_verification(
        session=session,
        bot=bot,
        token=verification.token,
        action="agree",
        actor_user_id=42,
    )

    assert result.ok is True
    assert result.message == "Verification completed successfully."
    assert isinstance(bot.methods[0], AnswerChatJoinRequestQuery)
    assert bot.methods[0].ok is True


@pytest.mark.asyncio
async def test_complete_verification_decline_uses_fallback_join_api(session) -> None:
    group = await add_group(session, -1002, "Fallback Group", 123456789)
    verification = await create_pending_verification(
        session=session,
        user_id=55,
        user_chat_id=5500,
        chat_id=group.chat_id,
        query_id="fallback_5500_deadbeef",
    )

    bot = FakeBot()
    result = await complete_verification(
        session=session,
        bot=bot,
        token=verification.token,
        action="decline",
        actor_user_id=55,
    )

    assert result.ok is True
    assert result.message == "Verification declined."
    assert bot.declined == [(-1002, 55)]


@pytest.mark.asyncio
async def test_complete_verification_rejects_wrong_user(session) -> None:
    group = await add_group(session, -1003, "Mismatch Group", 123456789)
    verification = await create_pending_verification(
        session=session,
        user_id=77,
        user_chat_id=7700,
        chat_id=group.chat_id,
        query_id="query-2",
    )

    bot = FakeBot()
    result = await complete_verification(
        session=session,
        bot=bot,
        token=verification.token,
        action="agree",
        actor_user_id=78,
    )

    assert result.ok is False
    assert "another user" in result.message
    assert bot.methods == []


@pytest.mark.asyncio
async def test_complete_verification_rejects_invalid_action(session) -> None:
    group = await add_group(session, -1004, "Invalid Action Group", 123456789)
    verification = await create_pending_verification(
        session=session,
        user_id=88,
        user_chat_id=8800,
        chat_id=group.chat_id,
        query_id="query-3",
    )

    bot = FakeBot()
    result = await complete_verification(
        session=session,
        bot=bot,
        token=verification.token,
        action="maybe",
        actor_user_id=88,
    )

    assert result.ok is False
    assert "unsupported" in result.message.lower()
    assert bot.methods == []


@pytest.mark.asyncio
async def test_complete_verification_expires_stale_sessions(session) -> None:
    group = await add_group(session, -1005, "Expired Group", 123456789)
    verification = await create_pending_verification(
        session=session,
        user_id=99,
        user_chat_id=9900,
        chat_id=group.chat_id,
        query_id="query-4",
    )
    verification.expires_at = utcnow_naive() - timedelta(seconds=1)
    await session.commit()

    bot = FakeBot()
    result = await complete_verification(
        session=session,
        bot=bot,
        token=verification.token,
        action="agree",
        actor_user_id=99,
    )

    assert result.ok is False
    assert "expired" in result.message.lower()
