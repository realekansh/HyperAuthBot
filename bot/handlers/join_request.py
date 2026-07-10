import logging
import uuid

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatJoinRequest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database import create_pending_verification, get_group
from bot.keyboards import open_verification_keyboard
from bot.utils.bot_api_10_1 import (
    get_query_id,
    send_chat_join_request_web_app,
)
from bot.utils.telegram_formatting import html_escape, normalize_title


router = Router(name="join_request")
logger = logging.getLogger(__name__)


def verification_url(token: str) -> str:
    return f"{settings.MINI_APP_URL}?token={token}"


@router.chat_join_request()
async def handle_join_request(event: ChatJoinRequest, session: AsyncSession) -> None:
    group = await get_group(session, event.chat.id)
    if group is None:
        return

    query_id = get_query_id(event)

    verification = await create_pending_verification(
        session=session,
        user_id=event.from_user.id,
        user_chat_id=event.user_chat_id,
        chat_id=event.chat.id,
        query_id=query_id or f"fallback_{event.user_chat_id}_{uuid.uuid4().hex}",
    )

    url = verification_url(verification.token)
    logger.debug(
        "Created verification token for chat_id=%s user_id=%s has_query_id=%s",
        event.chat.id,
        event.from_user.id,
        bool(query_id),
    )

    if query_id:
        try:
            await send_chat_join_request_web_app(
                event.bot,
                query_id=query_id,
                url=url,
            )
        except TelegramBadRequest:
            logger.debug(
                "sendChatJoinRequestWebApp failed for chat_id=%s user_id=%s",
                event.chat.id,
                event.from_user.id,
            )

    try:
        title = html_escape(normalize_title(group.title))
        await event.bot.send_message(
            chat_id=event.user_chat_id,
            text=(
                f"To join <b>{title}</b>, please complete verification.\n\n"
                "Tap the button below to continue."
            ),
            parse_mode="HTML",
            reply_markup=open_verification_keyboard(url),
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        logger.warning(
            "Failed to deliver verification DM for chat_id=%s user_id=%s",
            event.chat.id,
            event.from_user.id,
        )
        return
