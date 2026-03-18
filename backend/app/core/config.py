"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "SastaSpace API"
    app_version: str = "0.1.0"
    debug: bool = False

    mongodb_url: str = "mongodb://mongodb:27017"
    mongodb_database: str = "sastaspace"

    redis_url: str = "redis://redis:6379/0"
    app_mode: str = "SERVER"  # SERVER, CONSUMER, COORDINATOR, JOB, CRONJOB

    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
