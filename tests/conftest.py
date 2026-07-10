import os

os.environ.setdefault("BOT_TOKEN", "123456789:TEST_TOKEN")
os.environ.setdefault("OWNER_ID", "123456789")
os.environ.setdefault("MINI_APP_URL", "https://example.com/webapp")
os.environ.setdefault("WEBHOOK_URL", "")
os.environ.setdefault("WEBHOOK_SECRET", "secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("PORT", "8000")
os.environ.setdefault("LOG_LEVEL", "INFO")
