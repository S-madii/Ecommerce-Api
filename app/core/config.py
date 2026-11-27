from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str | None = None
    DB_ECHO: bool = False
    DEFAULT_CURRENCY: str = "USD"
    SECRET_KEY: SecretStr
    STRIPE_SECRET_KEY: SecretStr
    STRIPE_WEBHOOK_SECRET: SecretStr | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10
    ADMIN_EMAIL: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
