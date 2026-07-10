from types import SimpleNamespace

import pytest

from bot.utils.bot_api_10_1 import (
    AnswerChatJoinRequestQuery,
    SendChatJoinRequestWebApp,
    answer_chat_join_request_query,
    get_query_id,
    send_chat_join_request_web_app,
)


class FakeBot:
    def __init__(self) -> None:
        self.methods = []

    async def __call__(self, method):
        self.methods.append(method)
        return True


def test_get_query_id_from_attribute() -> None:
    assert get_query_id(SimpleNamespace(query_id="query-1")) == "query-1"


def test_get_query_id_from_model_extra() -> None:
    assert get_query_id(SimpleNamespace(model_extra={"query_id": "query-2"})) == "query-2"


@pytest.mark.asyncio
async def test_send_chat_join_request_web_app_uses_custom_method() -> None:
    bot = FakeBot()

    result = await send_chat_join_request_web_app(bot, "query-1", "https://example.com/webapp?token=abc")

    assert result is True
    assert isinstance(bot.methods[0], SendChatJoinRequestWebApp)
    assert bot.methods[0].query_id == "query-1"
    assert bot.methods[0].web_app.url == "https://example.com/webapp?token=abc"


@pytest.mark.asyncio
async def test_answer_chat_join_request_query_uses_custom_method() -> None:
    bot = FakeBot()

    result = await answer_chat_join_request_query(bot, "query-1", True)

    assert result is True
    assert isinstance(bot.methods[0], AnswerChatJoinRequestQuery)
    assert bot.methods[0].query_id == "query-1"
    assert bot.methods[0].ok is True
