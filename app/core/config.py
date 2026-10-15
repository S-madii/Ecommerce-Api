from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr #Access the actual value via settings.SECRET_KEY.get_secret_value()

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: SecretStr
    STRIPE_SECRET_KEY: SecretStr

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")   