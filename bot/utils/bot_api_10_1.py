from typing import Any

from aiogram.methods import TelegramMethod
from aiogram.types import WebAppInfo


class SendChatJoinRequestWebApp(TelegramMethod[bool]):
    __returning__ = bool
    __api_method__ = "sendChatJoinRequestWebApp"

    query_id: str
    web_app: WebAppInfo


class AnswerChatJoinRequestQuery(TelegramMethod[bool]):
    __returning__ = bool
    __api_method__ = "answerChatJoinRequestQuery"

    query_id: str
    ok: bool
    text: str | None = None


def get_query_id(chat_join_request: Any) -> str | None:
    query_id = getattr(chat_join_request, "query_id", None)
    if query_id:
        return str(query_id)
    model_extra = getattr(chat_join_request, "model_extra", None) or {}
    query_id = model_extra.get("query_id")
    return str(query_id) if query_id else None


async def send_chat_join_request_web_app(bot: Any, query_id: str, url: str) -> bool:
    method = SendChatJoinRequestWebApp(query_id=query_id, web_app=WebAppInfo(url=url))
    return bool(await bot(method))


async def answer_chat_join_request_query(
    bot: Any,
    query_id: str,
    ok: bool,
    text: str | None = None,
) -> bool:
    method = AnswerChatJoinRequestQuery(query_id=query_id, ok=ok, text=text)
    return bool(await bot(method))
