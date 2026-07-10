# HyperAuth Production Deployment Guide

This guide covers a full production setup for a VPS or cloud host. It is written so a person can follow it end to end without already knowing the codebase.

## Recommended deployment model

Use webhook mode on a public HTTPS server if you can. It is the cleanest setup for production.

- One process handles the Telegram bot, webhook endpoint, and Mini App API.
- One public HTTPS domain serves `/webapp`, `/static/*`, and `/webhook`.
- Telegram sends updates to your server instead of your server polling Telegram continuously.

Use polling mode only if you want the bot to run separately from the web app, or if you are developing locally.

- One process runs `python -m bot.main` with `WEBHOOK_URL=` empty.
- Another process runs `python -m webapp.run` for the Mini App and API.
- The bot still needs a reachable Mini App URL, but it does not need an inbound Telegram webhook.

## Required environment variables

Set these in `.env` or in your process manager.

| Variable | Required | Meaning |
| --- | --- | --- |
| `BOT_TOKEN` | yes | Telegram bot token from BotFather |
| `OWNER_ID` | yes | Numeric Telegram user ID of the owner |
| `MINI_APP_URL` | yes | Public HTTPS URL for the Mini App, for example `https://bot.example.com/webapp` |
| `WEBHOOK_URL` | no | Public HTTPS webhook URL, for example `https://bot.example.com/webhook` |
| `WEBHOOK_SECRET` | no | Secret token Telegram must send back to your webhook |
| `DATABASE_URL` | no | Defaults to SQLite, use PostgreSQL in production when possible |
| `PORT` | no | Server port. Default is `8000` |
| `LOG_LEVEL` | no | `INFO` is the default; `DEBUG` is useful during rollout |

Rules:

- `MINI_APP_URL` must be HTTPS in production.
- `WEBHOOK_URL` must be HTTPS if you set it.
- `OWNER_ID` must be an integer, not a username.
- If you use SQLite on a VPS, make sure the filesystem persists across restarts.
- If you use a managed cloud host, PostgreSQL is the safer database choice.

## What to choose

### Webhook mode

Choose this when:

- You have a VPS, container host, or cloud host that can expose a public HTTPS endpoint.
- You want the simplest production setup.
- You want one process instead of separate bot and web app workers.

### Polling mode

Choose this when:

- You want the bot worker separate from the web app.
- You are running locally.
- You do not want to configure Telegram webhooks yet.

## Quick local validation

Before deploying, run:

```bash
python -m pytest -q
node --check webapp/static/app.js
```

Then open the Mini App in Telegram and confirm:

- It renders the current UI, not a stale cached version.
- The join flow sends `initData`.
- The verification request reaches `/api/verify`.

## VPS deployment

The example below assumes Ubuntu 22.04 or 24.04.

### 1. Install system packages

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nginx
```

If you plan to use HTTPS on the VPS:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 2. Create a service user

Use a dedicated account instead of running the app as root.

```bash
sudo adduser --disabled-password --gecos "" hyperauth
sudo usermod -aG sudo hyperauth
```

You do not need sudo for the app itself, only for system setup.

### 3. Clone the repo

```bash
sudo -iu hyperauth
mkdir -p ~/apps
cd ~/apps
git clone <your-repo-url> HyperAuth
cd HyperAuth
```

### 4. Create the virtualenv and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Create `.env`

Use the example file as a template.

```bash
cp .env.example .env
```

Example production `.env`:

```bash
BOT_TOKEN=123456789:replace_me
OWNER_ID=123456789
MINI_APP_URL=https://bot.example.com/webapp
WEBHOOK_URL=https://bot.example.com/webhook
WEBHOOK_SECRET=replace_with_a_long_random_string
DATABASE_URL=sqlite+aiosqlite:///./hyperauth_guardian.db
PORT=8000
LOG_LEVEL=INFO
```

For a production VPS, SQLite is acceptable if the server has one instance and the disk is persistent. PostgreSQL is still better if you expect growth or want easier backups.

### 6. Choose your runtime mode

#### Option A: webhook mode on one VPS

Use this if the same server should host the bot and the Mini App.

Create a `systemd` service:

```ini
[Unit]
Description=HyperAuth Guardian Bot
After=network.target

[Service]
Type=simple
User=hyperauth
WorkingDirectory=/home/hyperauth/apps/HyperAuth
EnvironmentFile=/home/hyperauth/apps/HyperAuth/.env
ExecStart=/home/hyperauth/apps/HyperAuth/.venv/bin/python -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Save it as `/etc/systemd/system/hyperauth.service`, then enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hyperauth
```

#### Option B: polling mode with a separate web app

Use this if you want the bot and the web app split into two processes.

Bot worker service:

```ini
[Unit]
Description=HyperAuth Bot Worker
After=network.target

[Service]
Type=simple
User=hyperauth
WorkingDirectory=/home/hyperauth/apps/HyperAuth
EnvironmentFile=/home/hyperauth/apps/HyperAuth/.env
Environment=WEBHOOK_URL=
ExecStart=/home/hyperauth/apps/HyperAuth/.venv/bin/python -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Web app service:

```ini
[Unit]
Description=HyperAuth Web App
After=network.target

[Service]
Type=simple
User=hyperauth
WorkingDirectory=/home/hyperauth/apps/HyperAuth
EnvironmentFile=/home/hyperauth/apps/HyperAuth/.env
ExecStart=/home/hyperauth/apps/HyperAuth/.venv/bin/python -m webapp.run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Because `webapp.run` now reads `PORT`, you can change the port from `.env` if your reverse proxy or host needs a different one.

### 7. Put Nginx in front

Use Nginx to terminate TLS and forward traffic to the app.

Example single-service webhook setup:

```nginx
server {
    listen 80;
    server_name bot.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name bot.example.com;

    ssl_certificate /etc/letsencrypt/live/bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 300;
    }
}
```

For polling mode, point Nginx at the `webapp.run` port and keep the bot worker separate.

### 8. Issue TLS certificates

```bash
sudo certbot --nginx -d bot.example.com
```

After certbot finishes, confirm the site works over HTTPS.

### 9. Verify the bot

Check the service:

```bash
sudo systemctl status hyperauth
```

Watch logs:

```bash
journalctl -u hyperauth -f
```

If you used polling mode, check the bot worker and web app services separately.

## Cloud hosting

The deployment shape is the same even if the host is not a VPS. The main differences are port assignment, storage, and whether the platform supports incoming webhooks.

### Render, Railway, Fly.io, Heroku-like platforms

Use these when the platform gives you:

- A public HTTPS URL.
- Environment variables.
- Optional persistent disk or managed Postgres.

Recommended setup:

- Use webhook mode if the host can keep a long-running process alive.
- Use `python -m bot.main` as the start command.
- Set `MINI_APP_URL` to the public `/webapp` URL.
- Set `WEBHOOK_URL` to the public `/webhook` URL.
- Set `WEBHOOK_SECRET` to a random secret.
- Use PostgreSQL if the host supports it.

If the host assigns a dynamic port, set `PORT` to the platform value and let the service read it from `.env` or platform env vars.

### Docker-based hosts

Use a single container if possible.

Recommended image behavior:

- Install Python dependencies during build.
- Copy the repository into the image.
- Expose the runtime port.
- Read config only from environment variables.
- Keep the container stateless.

For containers, PostgreSQL is usually the right database. SQLite inside a container is fragile unless the host gives you a persistent mounted volume.

### Google Cloud Run, Azure Container Apps, similar autoscaling hosts

These platforms can work, but they are less forgiving if you expect a long-lived polling worker.

Use webhook mode.

- Expose the app on the platform port.
- Point Telegram to the public HTTPS webhook URL.
- Use managed PostgreSQL.
- Avoid relying on local disk for anything important.

### If the platform sleeps the service

Do not use polling mode on a service that sleeps or scales to zero unless you are certain it will wake instantly and reliably. Telegram updates should not depend on an asleep process.

## Database guidance

### SQLite

Use SQLite when:

- You are on a single VPS.
- You want the simplest setup.
- The database file will persist on disk.

The default database is:

```bash
sqlite+aiosqlite:///./hyperauth_guardian.db
```

### PostgreSQL

Use PostgreSQL when:

- You are on a managed cloud host.
- You want reliable backups.
- You may run more than one instance later.

Example URL:

```bash
postgresql+asyncpg://hyperauth:password@db.example.com:5432/hyperauth
```

Backups:

- SQLite: copy the database file while the app is stopped or use a safe backup procedure.
- PostgreSQL: use `pg_dump` or your cloud provider's backup tooling.

## Static assets and avatar override

- `webapp/static/style.css`, `webapp/static/app.js`, and `webapp/static/index.html` are versioned in the served HTML.
- The server returns `Cache-Control: no-store` for the Mini App shell.
- If you edit the frontend, restart the service and reopen the Mini App from Telegram.
- To override the bot avatar, place `webapp/static/avatar.jpg` in the repo.
- If `avatar.jpg` is missing, the default `HA` fallback remains visible.

## Logs and debugging in production

Logging is colorized when the terminal supports ANSI colors and `NO_COLOR` is not set.

Useful commands:

```bash
journalctl -u hyperauth -f
systemctl restart hyperauth
systemctl status hyperauth
```

If you are using separate bot and web app services, watch both logs.

Typical debugging flow:

1. Check whether the bot is receiving join requests.
2. Check whether `/webapp?token=...` renders.
3. Check whether `/api/verify` receives `token`, `action`, and `initData`.
4. Check whether the signature validation failed with `403`.
5. Check whether the session is stale or already handled.

## Upgrade and rollback

### Upgrade

1. Pull the latest code.
2. Reinstall dependencies if `requirements.txt` changed.
3. Run `python -m pytest -q` and `node --check webapp/static/app.js`.
4. Restart the service.
5. Reopen the Mini App in Telegram so the browser gets the latest assets.

### Rollback

1. Restore the previous release or git revision.
2. Restart the service.
3. Reopen the Mini App again so the old assets do not stay cached.

## Troubleshooting

### `422 Unprocessable Content` from `/api/verify`

The frontend is stale or did not send Telegram `initData`.

Fix:

- Reopen the Mini App from Telegram.
- Confirm the browser is using the current `app.js`.
- Confirm the request payload contains `token`, `action`, and `initData`.

### `403 Invalid Telegram signature`

The signed Telegram payload is invalid, expired, or was generated for a different session.

Fix:

- Reopen the Mini App from Telegram.
- Check the server clock.
- Confirm `BOT_TOKEN` is correct.

### `404 Invalid or expired session`

The join request is gone or the token does not exist anymore.

Fix:

- Request a fresh join attempt.
- Do not reuse old verification URLs.

### Nginx shows `502 Bad Gateway`

The upstream process is not running or is listening on the wrong port.

Fix:

- Check `systemctl status`.
- Check the port in `.env`.
- Check the service logs.

### Bot does not answer join requests

Common causes:

- The bot lost group admin rights.
- Invite Users permission is missing.
- You are in polling mode but the polling worker is not running.
- You are in webhook mode but the webhook URL is wrong or unreachable.

### Mini App looks stale after deployment

The browser or Telegram WebView is still using cached assets.

Fix:

- Restart the service.
- Reopen the Mini App from Telegram.
- Verify the HTML is serving `?v=` versioned asset URLs.

## Production checklist

- `python -m pytest -q` passes.
- `node --check webapp/static/app.js` passes.
- `BOT_TOKEN`, `OWNER_ID`, and `MINI_APP_URL` are correct.
- `WEBHOOK_URL` is HTTPS if webhook mode is used.
- `DATABASE_URL` points to persistent storage.
- The bot has admin rights and Invite Users permission.
- The Mini App opens from Telegram, not from an old browser tab.
- The deployment path has a rollback plan.

