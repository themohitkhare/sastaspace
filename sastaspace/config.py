# sastaspace/config.py
import os
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
        # SASTASPACE_SITES_DIR takes precedence (used by Docker/server.py)
        env_val = os.environ.get("SASTASPACE_SITES_DIR")
        if env_val:
            return Path(env_val)
        return v

    server_port: int = 8080
    claude_model: str = "claude-sonnet-4-6-20250514"

    # Agno pipeline (premium tier — Claude)
    use_agno_pipeline: bool = True
    crawl_analyst_model: str = "claude-sonnet-4-6-20250514"
    design_strategist_model: str = "claude-sonnet-4-6-20250514"
    html_generator_model: str = "claude-sonnet-4-6-20250514"
    quality_reviewer_model: str = "claude-sonnet-4-6-20250514"

    # Per-step model routing (override the global model_provider per step)
    # Empty string = use the global model_provider passed to the pipeline
    planner_model_provider: str = ""  # e.g. "gemini" for fast/cheap JSON planning
    builder_model_provider: str = ""  # e.g. "claude" for highest quality HTML
    composer_model_provider: str = ""  # e.g. "claude" for highest quality React composition

    # Gemini (alternative provider)
    gemini_api_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_api_key: str = ""  # Set via GEMINI_API_KEY env var
    gemini_model: str = "gemini-2.5-flash"

    # Ollama (free tier)
    ollama_url: str = "http://localhost:11434/v1"
    ollama_api_key: str = "ollama"

    # Free tier model assignments (Ollama)
    free_crawl_analyst_model: str = "glm-4.7-flash:latest"
    free_design_strategist_model: str = "glm-4.7-flash:latest"
    free_copywriter_model: str = "glm-4.7-flash:latest"
    free_component_selector_model: str = "glm-4.7-flash:latest"
    free_html_generator_model: str = "glm-4.7-flash:latest"
    free_quality_reviewer_model: str = "glm-4.7-flash:latest"

    # Logging
    log_format: str = "text"  # "text" (human-readable) or "json" (structured)

    cors_origins: str | list[str] = ["http://localhost:3000"]
    rate_limit_max: int = 3
    rate_limit_window_seconds: int = 3600

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "sastaspace"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Twenty CRM (empty = integration disabled)
    twenty_url: str = ""
    twenty_api_key: str = ""
    twenty_webhook_secret: str = ""
    twenty_admin_key: str = ""

    # Badge injection on generated sites
    include_badge: bool = True

    # Post-generation HTML validation (accessibility + responsiveness via Playwright/axe-core)
    enable_post_gen_validation: bool = True

    # Asset download concurrency (number of parallel downloads)
    asset_download_concurrency: int = 10

    # Browserless (remote Chromium via CDP)
    browserless_url: str = "ws://localhost:3100"

    # Plan cache (skip Planner for common site_type + archetype combos)
    enable_plan_cache: bool = True

    # Parallel builder (experimental — split HTML generation into concurrent section calls)
    enable_parallel_builder: bool = False  # ENABLE_PARALLEL_BUILDER=true to opt in

    # Component-based React pipeline
    use_component_pipeline: bool = True
    components_dir: Path = Path("./components")
    redesign_template_dir: Path = Path("./redesign-template")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
