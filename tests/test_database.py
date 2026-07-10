import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.database import (
    add_group,
    create_pending_verification,
    get_group,
    get_pending_for_user,
    get_verification_by_token,
    mark_verification,
)
from bot.models import Base


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db_session:
        yield db_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_group_and_pending_verification_flow(session) -> None:
    group = await add_group(session, -1001, "Test Group", 123456789)
    assert group.chat_id == -1001

    fetched_group = await get_group(session, -1001)
    assert fetched_group is not None
    assert fetched_group.title == "Test Group"

    verification = await create_pending_verification(
        session=session,
        user_id=42,
        user_chat_id=4200,
        chat_id=-1001,
        query_id="query-1",
    )
    assert verification.status == "pending"
    assert verification.token

    fetched = await get_verification_by_token(session, verification.token, include_group=True)
    assert fetched is not None
    assert fetched.group.title == "Test Group"

    pending = await get_pending_for_user(session, 42)
    assert len(pending) == 1

    await mark_verification(session, verification, "completed")
    pending_after = await get_pending_for_user(session, 42)
    assert pending_after == []
