import os

from cryptography.fernet import Fernet

# Deterministic, isolated settings for every test (env vars beat the .env file).
os.environ.update(
    {
        "TELEGRAM_BOT_TOKEN": "123456:test-token",
        "TELEGRAM_WEBHOOK_SECRET": "test-secret",
        "ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "ANTHROPIC_API_KEY": "test-key",
        "PUBLIC_BASE_URL": "",
    }
)
