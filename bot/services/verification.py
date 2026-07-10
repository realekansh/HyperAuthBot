from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import get_verification_by_token, mark_verification
from bot.utils.bot_api_10_1 import answer_chat_join_request_query


@dataclass(slots=True)
class VerificationResult:
    ok: bool
    message: str


def _is_expired(expires_at: datetime) -> bool:
    return expires_at < datetime.now(UTC).replace(tzinfo=None)


async def complete_verification(
    *,
    session: AsyncSession,
    bot: Bot,
    token: str,
    action: str,
    actor_user_id: int | None = None,
) -> VerificationResult:
    verification = await get_verification_by_token(session, token, include_group=True)
    if verification is None:
        return VerificationResult(False, "Verification session was not found.")

    if verification.status != "pending":
        return VerificationResult(False, "This verification session is no longer active.")

    if verification.group is None:
        return VerificationResult(False, "The target group is no longer available.")

    if _is_expired(verification.expires_at):
        await mark_verification(session, verification, "expired")
        return VerificationResult(False, "This verification session expired.")

    if actor_user_id is not None and actor_user_id != verification.user_id:
        return VerificationResult(False, "This verification belongs to another user.")

    if action not in {"agree", "decline"}:
        return VerificationResult(False, "Unsupported verification action.")

    try:
        if verification.query_id.startswith("fallback_"):
            if action == "agree":
                await bot.approve_chat_join_request(
                    chat_id=verification.chat_id,
                    user_id=verification.user_id,
                )
            else:
                await bot.decline_chat_join_request(
                    chat_id=verification.chat_id,
                    user_id=verification.user_id,
                )
        else:
            await answer_chat_join_request_query(
                bot,
                query_id=verification.query_id,
                ok=action == "agree",
                text=None if action == "agree" else "Please complete the verification to join.",
            )
    except (TelegramBadRequest, TelegramForbiddenError):
        await mark_verification(session, verification, "expired")
        return VerificationResult(False, "This join request is no longer available.")

    status = "completed" if action == "agree" else "declined"
    await mark_verification(session, verification, status)

    if action == "agree":
        return VerificationResult(True, "Verification completed successfully.")

    return VerificationResult(True, "Verification declined.")
