import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.handlers import admin_commands, commands, join_request, web_app_data
from bot.middlewares.db_middleware import DbSessionMiddleware


ALLOWED_UPDATES = ["message", "callback_query", "chat_join_request"]


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[35m",
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def __init__(self, use_colors: bool, verbose: bool) -> None:
        fmt = (
            "%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s"
            if verbose
            else "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        super().__init__(fmt=fmt, datefmt="%H:%M:%S")
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        if not self.use_colors:
            return message

        color = self.COLORS.get(record.levelno, "")
        if not color:
            return message

        level = f"{color}{self.BOLD}{record.levelname:<8}{self.RESET}"
        return message.replace(record.levelname, level, 1)


def configure_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL)
    verbose = settings.LOG_LEVEL == "DEBUG"
    use_colors = sys.stderr.isatty() and os.environ.get("NO_COLOR") is None
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter(use_colors=use_colors, verbose=verbose))

    logging.basicConfig(
        level=level,
        handlers=[handler],
        force=True,
    )

    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)


def create_bot() -> Bot:
    return Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    db_middleware = DbSessionMiddleware()
    dispatcher.update.middleware(db_middleware)
    dispatcher.include_router(join_request.router)
    dispatcher.include_router(web_app_data.router)
    dispatcher.include_router(commands.router)
    dispatcher.include_router(admin_commands.router)
    return dispatcher
