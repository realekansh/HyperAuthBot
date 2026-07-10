from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database import add_group, delete_pending_for_group, get_group, remove_group, set_captcha, set_rules
from bot.filters.owner_filter import IsOwner
from bot.keyboards import setrules_confirm_keyboard
from bot.utils.telegram_formatting import html_escape, normalize_title, truncate

router = Router(name="admin_commands")


class RulesState(StatesGroup):
    waiting_for_rules = State()


def command_args(message: Message) -> str:
    text = message.text or ""
    return text.split(maxsplit=1)[1].strip() if len(text.split(maxsplit=1)) == 2 else ""


def parse_private_group_args(args: str) -> tuple[int | None, str | None]:
    parts = args.split(maxsplit=1)
    if not parts:
        return None, None
    try:
        chat_id = int(parts[0])
    except ValueError:
        return None, None
    title = parts[1].strip() if len(parts) > 1 else str(chat_id)
    return chat_id, title


@router.message(Command("addgroup"), IsOwner())
async def addgroup_command(message: Message, session: AsyncSession) -> None:
    if message.chat.type in {"group", "supergroup"}:
        chat_id = message.chat.id
        title = normalize_title(message.chat.title, fallback=str(chat_id))
    else:
        chat_id, title = parse_private_group_args(command_args(message))
        if chat_id is None or title is None:
            await message.answer("Usage: /addgroup -100123456789 Group Name")
            return

    existing = await get_group(session, chat_id)
    if existing is not None:
        await message.answer("This group is already in my watchlist.")
        return

    await add_group(session, chat_id=chat_id, title=title, added_by=settings.OWNER_ID)
    await message.answer(
        f"Done. I will now act as HyperAuth Guardian Bot in <b>{html_escape(title)}</b>.\n"
        "Make sure I am an administrator with the Invite Users permission in that group.",
        parse_mode="HTML",
    )


@router.message(Command("removegroup"), IsOwner())
async def removegroup_command(message: Message, session: AsyncSession) -> None:
    if message.chat.type in {"group", "supergroup"}:
        chat_id = message.chat.id
    else:
        chat_id, _ = parse_private_group_args(command_args(message))
        if chat_id is None:
            await message.answer("Usage: /removegroup -100123456789")
            return

    group = await get_group(session, chat_id)
    if group is None:
        await message.answer("This group is not in my watchlist.")
        return

    title = group.title
    await delete_pending_for_group(session, chat_id)
    await remove_group(session, chat_id)
    await message.answer(f"HyperAuth Guardian Bot deactivated for <b>{html_escape(title)}</b>.", parse_mode="HTML")


@router.message(Command("captcha"), IsOwner())
async def captcha_command(message: Message, session: AsyncSession) -> None:
    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("Run this command inside the target group.")
        return
    group = await get_group(session, message.chat.id)
    if group is None:
        await message.answer("This group is not in my watchlist yet. Use /addgroup first.")
        return

    arg = command_args(message).lower()
    if arg not in {"on", "off"}:
        await message.answer("Usage: /captcha on or /captcha off")
        return
    enabled = arg == "on"
    await set_captcha(session, message.chat.id, enabled)
    await message.answer(f"Captcha is now {'ON' if enabled else 'OFF'} for this group.")


@router.message(Command("setrules"), IsOwner())
async def setrules_command(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("Run this command inside the target group.")
        return
    group = await get_group(session, message.chat.id)
    if group is None:
        await message.answer("This group is not in my watchlist yet. Use /addgroup first.")
        return
    await state.set_state(RulesState.waiting_for_rules)
    await state.update_data(chat_id=message.chat.id)
    await message.answer(
        "Send me the rules text now. I support Telegram formatting such as bold, italic, code blocks, and links."
    )


@router.message(RulesState.waiting_for_rules, IsOwner())
async def receive_rules_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    rules_text = message.text or ""
    data = await state.get_data()
    chat_id = int(data["chat_id"])
    group = await get_group(session, chat_id)
    if group is None:
        await state.clear()
        await message.answer("This group is no longer in my watchlist. No changes were made.")
        return

    await state.update_data(rules_text=rules_text)
    preview = html_escape(truncate(rules_text))
    await message.answer(
        "Here is a preview of the rules:\n\n"
        f"<blockquote>{preview}</blockquote>\n\n"
        f"Do you want to save these as the rules for <b>{html_escape(group.title)}</b>?",
        parse_mode="HTML",
        reply_markup=setrules_confirm_keyboard(chat_id),
    )


@router.callback_query(F.data.startswith("setrules_confirm:"), IsOwner())
async def confirm_rules(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    data = await state.get_data()
    rules_text = data.get("rules_text")
    chat_id = int(callback.data.split(":", 1)[1])
    if not isinstance(rules_text, str):
        await callback.answer("No rules text is waiting to be saved.", show_alert=True)
        return
    await set_rules(session, chat_id, rules_text)
    await state.clear()
    await callback.message.edit_text("Rules saved. New join requesters will see these rules before joining.")
    await callback.answer()


@router.callback_query(F.data == "setrules_cancel", IsOwner())
async def cancel_rules(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is not None:
        await callback.message.edit_text("Cancelled. No changes were made.")
    await state.clear()
    await callback.answer()
