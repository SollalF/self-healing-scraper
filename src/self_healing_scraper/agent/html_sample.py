"""Backward-compatible re-exports for HTML sampling helpers."""

from self_healing_scraper.agent.page_sample import (
    html_sample,
)
from self_healing_scraper.agent.page_sample import (
    html_sample_for_llm as html_sample_for_repair,
)

__all__ = ["html_sample", "html_sample_for_repair"]
