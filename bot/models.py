from datetime import datetime, timedelta
from typing import List

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from bot.utils.time import utcnow_naive


class Base(DeclarativeBase):
    pass


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    captcha_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    added_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    pending_verifications: Mapped[List["PendingVerification"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PendingVerification(Base):
    __tablename__ = "pending_verifications"
    __table_args__ = (
        UniqueConstraint("query_id", name="uq_pending_verifications_query_id"),
        UniqueConstraint("token", name="uq_pending_verifications_token"),
        Index("ix_pending_verifications_user_status_created", "user_id", "status", "created_at"),
        Index("ix_pending_verifications_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("groups.chat_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_id: Mapped[str] = mapped_column(String(512), nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: utcnow_naive() + timedelta(days=7),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    group: Mapped[Group] = relationship(back_populates="pending_verifications")
