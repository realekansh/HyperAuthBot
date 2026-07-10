from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database import get_pending_for_user, get_verification_by_token, increment_attempts
from bot.keyboards import pending_groups_keyboard, start_verification_keyboard
from bot.utils.telegram_formatting import html_escape, normalize_title

router = Router(name="commands")


def verification_url(token: str) -> str:
    return f"{settings.MINI_APP_URL}?token={token}"


@router.message(Command("start"), F.chat.type == "private")
async def start_command(message: Message) -> None:
    await message.answer(
        "Hey there. I am <b>HyperAuth Guardian Bot</b>, here to make sure only real humans get into the groups I protect.\n\n"
        "When you request to join a group that I watch over, I open a quick verification window. "
        "You complete the check, read the group rules, and confirm that you agree.\n\n"
        "If you ever miss the verification prompt, use /verify to check your pending requests anytime.",
        parse_mode="HTML",
    )


@router.message(Command("verify"), F.chat.type == "private")
async def verify_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    pending = [item for item in await get_pending_for_user(session, message.from_user.id) if item.group is not None]
    if not pending:
        await message.answer(
            "You do not have any pending join requests right now. If you have already been approved, check the group directly."
        )
        return

    items = [(normalize_title(item.group.title), item.token) for item in pending]
    await message.answer(
        "You have pending join requests. Tap a group below to verify:",
        reply_markup=pending_groups_keyboard(items),
    )


@router.callback_query(F.data == "verify_back")
async def verify_back(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    pending = [item for item in await get_pending_for_user(session, callback.from_user.id) if item.group is not None]
    items = [(normalize_title(item.group.title), item.token) for item in pending]
    await callback.message.edit_text(
        "You have pending join requests. Tap a group below to verify:",
        reply_markup=pending_groups_keyboard(items),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("verify_group:"))
async def verify_group_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    token = callback.data.split(":", 1)[1]
    verification = await get_verification_by_token(session, token, include_group=True)
    if verification is None or verification.status != "pending" or verification.group is None:
        await callback.answer("This verification is no longer available.", show_alert=True)
        return
    if callback.from_user.id != verification.user_id:
        await callback.answer("This verification belongs to another user.", show_alert=True)
        return
    if verification.attempt_count >= 3:
        await callback.answer("Too many verification attempts for this request.", show_alert=True)
        return

    await increment_attempts(session, verification)
    title = html_escape(normalize_title(verification.group.title))
    await callback.message.edit_text(
        f"Ready to verify for <b>{title}</b>?\n\nTap the button below to open the verification window.",
        parse_mode="HTML",
        reply_markup=start_verification_keyboard(verification_url(token)),
    )
    await callback.answer()


@router.message(Command("help"), F.chat.type == "private")
async def help_command(message: Message) -> None:
    if message.from_user is None or message.from_user.id != settings.OWNER_ID:
        return
    await message.answer(
        "<b>HyperAuth Guardian Bot Command Reference</b>\n\n"
        "<b>Owner Commands</b>\n"
        "/addgroup - Add a group to the allowlist. Run it in the target group, or send the group chat ID and title in private.\n"
        "/removegroup - Remove a group from the allowlist. Run it in the group, or send the group chat ID in private.\n"
        "/captcha on - Enable the click-captcha step for a group.\n"
        "/captcha off - Disable captcha for a group.\n"
        "/setrules - Set or update the rules for a group.\n"
        "/help - Show this command reference.\n\n"
        "<b>User Commands</b>\n"
        "/start - Learn what the bot does.\n"
        "/verify - Check pending join requests and verify from here.",
        parse_mode="HTML",
    )
