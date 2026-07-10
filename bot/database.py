from collections.abc import AsyncIterator
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from bot.config import settings
from bot.models import Base, Group, PendingVerification
from bot.utils.time import utcnow_naive


engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


def new_verification_token() -> str:
    return uuid4().hex


async def get_group(session: AsyncSession, chat_id: int) -> Group | None:
    result = await session.execute(select(Group).where(Group.chat_id == chat_id))
    return result.scalar_one_or_none()


async def add_group(session: AsyncSession, chat_id: int, title: str, added_by: int) -> Group:
    group = Group(chat_id=chat_id, title=title, captcha_enabled=True, added_by=added_by)
    session.add(group)
    await session.commit()
    return group


async def remove_group(session: AsyncSession, chat_id: int) -> bool:
    group = await get_group(session, chat_id)
    if group is None:
        return False
    await session.delete(group)
    await session.commit()
    return True


async def set_captcha(session: AsyncSession, chat_id: int, enabled: bool) -> bool:
    result = await session.execute(
        update(Group).where(Group.chat_id == chat_id).values(captcha_enabled=enabled)
    )
    await session.commit()
    return bool(result.rowcount)


async def set_rules(session: AsyncSession, chat_id: int, rules: str) -> bool:
    result = await session.execute(update(Group).where(Group.chat_id == chat_id).values(rules=rules))
    await session.commit()
    return bool(result.rowcount)


async def create_pending_verification(
    session: AsyncSession,
    user_id: int,
    user_chat_id: int,
    chat_id: int,
    query_id: str,
) -> PendingVerification:
    verification = PendingVerification(
        user_id=user_id,
        user_chat_id=user_chat_id,
        chat_id=chat_id,
        query_id=query_id,
        token=new_verification_token(),
    )
    session.add(verification)
    await session.commit()
    await session.refresh(verification)
    return verification


async def get_verification_by_token(
    session: AsyncSession,
    token: str,
    include_group: bool = False,
) -> PendingVerification | None:
    statement = select(PendingVerification).where(PendingVerification.token == token)
    if include_group:
        statement = statement.options(selectinload(PendingVerification.group))
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_pending_for_user(session: AsyncSession, user_id: int) -> list[PendingVerification]:
    result = await session.execute(
        select(PendingVerification)
        .options(selectinload(PendingVerification.group))
        .where(PendingVerification.user_id == user_id, PendingVerification.status == "pending")
        .order_by(PendingVerification.created_at.desc())
    )
    return list(result.scalars().all())


async def mark_verification(session: AsyncSession, verification: PendingVerification, status: str) -> None:
    verification.status = status
    verification.resolved_at = utcnow_naive()
    await session.commit()


async def increment_attempts(session: AsyncSession, verification: PendingVerification) -> None:
    verification.attempt_count += 1
    await session.commit()


async def expire_old_verifications(session: AsyncSession, days: int = 7) -> int:
    cutoff = utcnow_naive() - timedelta(days=days)
    result = await session.execute(
        update(PendingVerification)
        .where(PendingVerification.status == "pending", PendingVerification.created_at < cutoff)
        .values(status="expired", resolved_at=utcnow_naive())
    )
    await session.commit()
    return int(result.rowcount or 0)


async def delete_pending_for_group(session: AsyncSession, chat_id: int) -> int:
    result = await session.execute(delete(PendingVerification).where(PendingVerification.chat_id == chat_id))
    await session.commit()
    return int(result.rowcount or 0)
