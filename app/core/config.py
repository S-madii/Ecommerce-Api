from pydantic import SecretStr  # Access the actual value via settings.SECRET_KEY.get_secret_value()
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str | None = None
    SECRET_KEY: SecretStr
    STRIPE_SECRET_KEY: SecretStr
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
