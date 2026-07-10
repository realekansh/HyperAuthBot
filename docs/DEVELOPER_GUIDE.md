# HyperAuth Developer Guide

## Overview

HyperAuth has two runtime entrypoints:

- `python -m bot.main` for polling or webhook startup.
- `python -m webapp.run` for the web app only.

The production path is the Telegram join-request flow plus the Mini App verification flow. The Mini App now expects Telegram `initData`, and `/api/verify` rejects missing or invalid session data.

## Local setup

```bash
cd /home/notrealekansh/Projects/Workflows/HyperAuth
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Populate `.env` with:

- `BOT_TOKEN`
- `OWNER_ID`
- `MINI_APP_URL`
- `WEBHOOK_URL` if you are using webhook mode
- `WEBHOOK_SECRET` if you want webhook verification

## Running locally

Polling mode:

```bash
WEBHOOK_URL= python -m bot.main
```

Webhook mode:

```bash
python -m bot.main
```

Web app only:

```bash
python -m webapp.run
```

## Debugging workflow

1. Watch the bot logs for `chat_join_request` handling.
2. Confirm the Mini App response includes a fresh `token`.
3. Confirm the client posts `{ token, action, initData }` to `/api/verify`.
4. If verification fails with `422`, the frontend is stale or not sending Telegram `initData`.
5. If verification fails with `403`, the Telegram signature or `auth_date` is invalid.
6. If verification fails with `400`, the token or user mismatch is usually the cause.

## Cache and asset handling

- The HTML shell is returned with `Cache-Control: no-store`.
- The Mini App uses versioned `/static/app.js?v=...` and `/static/style.css?v=...` URLs.
- If you change frontend assets, restart the server and reopen the Mini App from Telegram.
- To override the Mini App avatar, place `webapp/static/avatar.jpg` in the repo. If it is missing, the default `HA` fallback stays visible.

## Testing

Run the full suite:

```bash
python -m pytest -q
```

Run the static Mini App checks only:

```bash
python -m pytest tests/test_webapp_static.py -q
```

Run the JS syntax check:

```bash
node --check webapp/static/app.js
```

## Production checklist

For full VPS and cloud deployment instructions, see [Production Deployment Guide](DEPLOYMENT.md).

- Bot is added as an admin in each protected group.
- Invite Users permission is enabled.
- `MINI_APP_URL` is HTTPS in production.
- `WEBHOOK_URL` is HTTPS in production when webhook mode is used.
- The bot token and owner ID are correct.
- `/addgroup` has been run for each protected group.
- The verification Mini App has been reopened after any frontend deploy.
- Logging is running at the intended level and the terminal supports ANSI colors, or `NO_COLOR` is set if you want plain logs.

## Troubleshooting

- **`422 Unprocessable Content` from `/api/verify`**
  - The frontend is not sending Telegram `initData`.
  - Reopen the Mini App from Telegram and verify the served `app.js` is current.

- **`403 Invalid Telegram signature`**
  - The Mini App session is stale or the signed payload is wrong.
  - Reopen the Mini App from Telegram.

- **Join request stays pending**
  - Check that the bot still has permission to approve join requests.
  - Check the bot logs for `TelegramBadRequest` or `TelegramForbiddenError`.

- **Rules screen does not enable the button**
  - Scroll to the bottom of the rules box.
  - If the rules are short, the button should enable automatically.
