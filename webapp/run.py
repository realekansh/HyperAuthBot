import uvicorn

from bot.application import configure_logging, create_bot, create_dispatcher
from bot.config import settings
from webapp.server import create_app

bot = create_bot()
dispatcher = create_dispatcher()

app = create_app(bot, dispatcher)

if __name__ == "__main__":
    configure_logging()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        log_config=None,
    )
