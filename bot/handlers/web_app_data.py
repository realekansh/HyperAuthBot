import json

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.verification import complete_verification

router = Router(name="web_app_data")


@router.message(F.web_app_data)
async def handle_web_app_data(message: Message, session: AsyncSession) -> None:
    try:
        payload = json.loads(message.web_app_data.data)
    except (TypeError, json.JSONDecodeError):
        return

    token = payload.get("token")
    action = payload.get("action")

    if not isinstance(token, str) or not isinstance(action, str):
        return

    if message.from_user is None:
        return

    normalized_action = "decline" if action == "captcha_failed" else action
    result = await complete_verification(
        session=session,
        bot=message.bot,
        token=token,
        action=normalized_action,
        actor_user_id=message.from_user.id,
    )

    if result.ok:
        await message.answer(result.message)
    elif "expired" in result.message.lower():
        await message.answer(
            "This verification session expired. Please send a new join request."
        )
    elif "belongs to another user" in result.message.lower():
        return
