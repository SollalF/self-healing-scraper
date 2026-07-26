"""Environment-driven settings for the scrape engine (no database)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_base_url: str = ""
    max_repair_attempts: int = 3
    crawl_timeout_ms: int = 30_000
    page_sample_chars: int = 12_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
