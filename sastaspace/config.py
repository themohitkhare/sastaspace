# sastaspace/config.py
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    claude_code_api_url: str = "http://localhost:8000/v1"
    sites_dir: Path = Path("./sites")
    server_port: int = 8080
    claude_model: str = "claude-sonnet-4-5-20250929"
