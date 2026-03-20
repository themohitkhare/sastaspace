# sastaspace/config.py
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    claude_code_api_url: str = "http://localhost:8000/v1"
    sites_dir: Path = Path("./sites")
    server_port: int = 8080
    claude_model: str = "claude-sonnet-4-5-20250929"

    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit_max: int = 3
    rate_limit_window_seconds: int = 3600

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
