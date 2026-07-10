import json
from functools import lru_cache
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from bot.config import settings
from bot.database import SessionFactory, expire_old_verifications, get_verification_by_token
from bot.services.verification import complete_verification
from webapp.api.validate import extract_init_data_user_id, validate_init_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "webapp" / "static"
INDEX_PATH = STATIC_DIR / "index.html"
STYLE_PATH = STATIC_DIR / "style.css"
APP_PATH = STATIC_DIR / "app.js"
AVATAR_PATH = STATIC_DIR / "avatar.jpg"


class VerifyRequest(BaseModel):
    token: str
    action: str
    initData: str


@lru_cache(maxsize=1)
def read_index_template() -> str:
    return INDEX_PATH.read_text(encoding="utf-8")


def asset_version() -> str:
    paths = [INDEX_PATH, STYLE_PATH, APP_PATH]
    if AVATAR_PATH.exists():
        paths.append(AVATAR_PATH)

    latest_mtime = max(
        path.stat().st_mtime_ns for path in paths
    )
    return str(latest_mtime)


def render_webapp(state: dict[str, Any]) -> HTMLResponse:
    html_content = read_index_template()
    version = asset_version()

    html_content = html_content.replace(
        '<link rel="stylesheet" href="/static/style.css">',
        f'<link rel="stylesheet" href="/static/style.css?v={version}">',
    ).replace(
        '<script src="/static/app.js"></script>',
        f'<script src="/static/app.js?v={version}"></script>',
    ).replace(
        "</head>",
        (
            f"<script>"
            f"window.__HYPERAUTH_STATE__ = "
            f"{json.dumps(state)};"
            f"</script></head>"
        ),
    )

    return HTMLResponse(
        content=html_content,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


def create_app(bot: Bot, dispatcher: Dispatcher) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with SessionFactory() as session:
            await expire_old_verifications(session)
        yield

    app = FastAPI(title="HyperAuth Guardian Bot", lifespan=lifespan)

    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static",
    )

    @app.post("/webhook")
    async def webhook(request: Request) -> Response:
        if settings.WEBHOOK_SECRET:
            secret = request.headers.get(
                "X-Telegram-Bot-Api-Secret-Token",
                "",
            )

            if secret != settings.WEBHOOK_SECRET:
                return Response(status_code=403)

        update_data = await request.json()
        update = Update.model_validate(update_data)

        await dispatcher.feed_update(
            bot=bot,
            update=update,
        )

        return Response(status_code=200)

    @app.post("/api/verify")
    async def verify(payload: VerifyRequest):
        if not payload.initData:
            return JSONResponse({"ok": False, "message": "Missing Telegram initData."}, status_code=400)

        if not validate_init_data(payload.initData, settings.BOT_TOKEN):
            return JSONResponse({"ok": False, "message": "Invalid Telegram signature."}, status_code=403)

        actor_user_id = extract_init_data_user_id(payload.initData)
        if actor_user_id is None:
            return JSONResponse({"ok": False, "message": "Unable to read Telegram user identity."}, status_code=400)

        async with SessionFactory() as session:
            result = await complete_verification(
                session=session,
                bot=bot,
                token=payload.token,
                action=payload.action,
                actor_user_id=actor_user_id,
            )

        status = 200 if result.ok else 400
        return JSONResponse({"ok": result.ok, "message": result.message}, status_code=status)

    @app.get("/webapp", response_class=HTMLResponse)
    async def mini_app(
        token: str = Query(..., min_length=8)
    ) -> HTMLResponse:

        async with SessionFactory() as session:
            verification = await get_verification_by_token(
                session,
                token,
                include_group=True,
            )

            if (
                verification is None
                or verification.status != "pending"
                or verification.group is None
            ):
                return render_webapp(
                    {
                        "token": "",
                        "captchaEnabled": False,
                        "hasRules": False,
                        "rules": "",
                        "groupTitle": "",
                        "avatarUrl": "",
                        "errorMessage": "Invalid or expired session.",
                    }
                )

            group = verification.group

            state: dict[str, Any] = {
                "token": token,
                "captchaEnabled": group.captcha_enabled,
                "hasRules": bool(group.rules),
                "rules": group.rules or "",
                "groupTitle": group.title,
                "avatarUrl": f"/static/avatar.jpg?v={asset_version()}" if AVATAR_PATH.exists() else "",
                "errorMessage": "",
            }

        return render_webapp(state)

    return app
