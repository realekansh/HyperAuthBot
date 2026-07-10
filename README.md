# HyperAuth Guardian Bot

HyperAuth Guardian Bot is a Telegram supergroup gatekeeper built for the Bot API 10.1 join request query flow. It receives `chat_join_request` updates, opens a Telegram Mini App with `sendChatJoinRequestWebApp`, and approves verified users with `answerChatJoinRequestQuery`.

## Quick Start

```bash
cd /home/notrealekansh/Projects/Workflows/HyperAuth
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with a real bot token, numeric owner ID, and HTTPS Mini App/webhook URLs for production.

## Documentation

- [User Guide](docs/USER_GUIDE.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)
- [Production Deployment Guide](docs/DEPLOYMENT.md)

## What it does

- Allowlisted group protection.
- Bot API 10.1 custom method wrappers for join request queries.
- Token-based Mini App verification URLs, never raw `query_id`.
- Click confirmation and rules acceptance Mini App.
- Owner-only `/addgroup`, `/removegroup`, `/captcha`, `/setrules`, and `/help`.
- User `/start` and `/verify`.
- Silent handling for non-owner admin command attempts and unallowlisted groups.
- FastAPI webhook endpoint plus local polling mode.
- SQLite by default, PostgreSQL-compatible through `DATABASE_URL`.

## Run

Development polling mode:

```bash
WEBHOOK_URL= python -m bot.main
```

Production webhook mode:

```bash
python -m bot.main
```

When `WEBHOOK_URL` is set, the app starts FastAPI and registers the Telegram webhook. When `WEBHOOK_URL` is empty, it uses long polling for development.

## Test

```bash
python -m pytest -q
```

```bash
node --check webapp/static/app.js
```

## Live Requirements

Live Telegram delivery still requires:

- `BOT_TOKEN`
- `OWNER_ID`
- HTTPS `MINI_APP_URL`
- HTTPS `WEBHOOK_URL` for production
- Bot added as group admin with Invite Users permission
- Group join approval enabled
- `/addgroup` run for each protected group

## Notes

The project includes wrappers for `sendChatJoinRequestWebApp` and `answerChatJoinRequestQuery` so it can target Bot API 10.1 even if the installed aiogram release has not exposed the methods as first-class helpers.

If you want to replace the default Mini App avatar, drop an `avatar.jpg` file into [webapp/static/](webapp/static). If that file is absent, the current `HA` fallback mark is shown instead.
