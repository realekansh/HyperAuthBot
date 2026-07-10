import asyncio

import uvicorn

from bot.application import ALLOWED_UPDATES, configure_logging, create_bot, create_dispatcher
from bot.config import settings
from bot.database import init_db
from webapp.server import create_app


async def run_polling() -> None:
    configure_logging()
    await init_db()
    bot = create_bot()
    dispatcher = create_dispatcher()
    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot, allowed_updates=ALLOWED_UPDATES)


async def run_webhook() -> None:
    configure_logging()
    await init_db()
    bot = create_bot()
    dispatcher = create_dispatcher()
    await bot.set_webhook(
        settings.WEBHOOK_URL,
        allowed_updates=ALLOWED_UPDATES,
        secret_token=settings.WEBHOOK_SECRET or None,
        drop_pending_updates=False,
    )
    app = create_app(bot=bot, dispatcher=dispatcher)
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        log_config=None,
    )
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    if settings.WEBHOOK_URL:
        asyncio.run(run_webhook())
    else:
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
