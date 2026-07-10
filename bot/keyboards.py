from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def open_verification_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Open Verification", web_app=WebAppInfo(url=url))]
        ]
    )


def pending_groups_keyboard(items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"verify_group:{token}")]
        for title, token in items
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_verification_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Start Verification", web_app=WebAppInfo(url=url))],
            [InlineKeyboardButton(text="Back", callback_data="verify_back")],
        ]
    )


def setrules_confirm_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Yes, save them", callback_data=f"setrules_confirm:{chat_id}")],
            [InlineKeyboardButton(text="No, cancel", callback_data="setrules_cancel")],
        ]
    )
