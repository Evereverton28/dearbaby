from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration. In production, load from environment / secrets manager."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DearBaby API"
    # Dev uses SQLite so the project runs with zero setup; prod points at Postgres.
    database_url: str = "sqlite:///./dearbaby_dev.db"

    # Auth
    secret_key: str = "CHANGE-ME-IN-PRODUCTION-use-a-64-char-random-string"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    algorithm: str = "HS256"


settings = Settings()
