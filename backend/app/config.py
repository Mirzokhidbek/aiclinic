from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

EMBEDDING_DIM = 768  # must match chunks.embedding vector(N) in migrations


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # Telegram
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_webhook_secret: SecretStr = SecretStr("")
    public_base_url: str = ""
    miniapp_url: str = ""

    # Anthropic
    anthropic_api_key: SecretStr = SecretStr("")
    llm_model_main: str = "claude-sonnet-5-5"
    llm_model_fast: str = "claude-haiku-5-5"
    llm_timeout_s: float = 30.0
    llm_max_retries: int = 3

    # Data
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint: str = "http://localhost:8333"
    s3_bucket: str = "documents"
    s3_access_key: str = ""
    s3_secret_key: SecretStr = SecretStr("")

    # Security
    jwt_secret: SecretStr = SecretStr("")
    encryption_key: SecretStr = SecretStr("")

    # Retrieval
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    retrieval_top_k: int = Field(default=5, ge=1, le=20)

    # Observability
    langfuse_host: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: SecretStr = SecretStr("")
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
