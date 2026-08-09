"""Caller-provided settings for the scrape engine (no .env loading)."""

from pydantic import BaseModel, ConfigDict

from self_healing_scraper.models import PageKind


class Settings(BaseModel):
    """Runtime knobs passed into scrape/fetch/LLM helpers.

    The library does not load ``.env`` or process environment variables.
    Applications should construct this explicitly (or via their own settings).
    """

    model_config = ConfigDict(extra="ignore")

    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_base_url: str = ""
    max_repair_attempts: int = 3
    crawl_timeout_ms: int = 30_000
    page_sample_chars: int = 12_000

    # Listings gain new items constantly, so only article pages are reusable by
    # default. The store still has the final say on whether a run is fresh.
    cached_page_kinds: frozenset[str] = frozenset({PageKind.ARTICLE.value})
