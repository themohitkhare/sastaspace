# sastaspace/config.py
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    claude_code_api_url: str = "http://localhost:8000/v1"
    claude_code_api_key: str = "claude-code"
    sites_dir: Path = Path("./sites")

    @field_validator("sites_dir", mode="before")
    @classmethod
    def resolve_sites_dir(cls, v):
        import os

        # SASTASPACE_SITES_DIR takes precedence (used by Docker/server.py)
        env_val = os.environ.get("SASTASPACE_SITES_DIR")
        if env_val:
            return Path(env_val)
        return v

    server_port: int = 8080
    claude_model: str = "claude-sonnet-4-6-20250514"

    # Agno pipeline
    use_agno_pipeline: bool = True
    crawl_analyst_model: str = "claude-haiku-4-5-20251001"
    design_strategist_model: str = "claude-sonnet-4-6-20250514"
    html_generator_model: str = "claude-sonnet-4-6-20250514"
    quality_reviewer_model: str = "claude-haiku-4-5-20251001"

    cors_origins: str | list[str] = ["http://localhost:3000"]
    rate_limit_max: int = 3
    rate_limit_window_seconds: int = 3600

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "sastaspace"

    # Redis
    redis_url: str = "redis://localhost:6379"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
