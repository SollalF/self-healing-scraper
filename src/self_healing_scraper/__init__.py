"""Generic self-healing declarative web scraper engine."""

from self_healing_scraper.domain import DomainPrompts, ScrapeDomain
from self_healing_scraper.models import ScrapeResult
from self_healing_scraper.scrape import normalize_url, scrape_url, scrape_urls
from self_healing_scraper.store import InMemoryParserStore, ParserStore, best_parser_match

__all__ = [
    "DomainPrompts",
    "InMemoryParserStore",
    "ParserStore",
    "ScrapeDomain",
    "ScrapeResult",
    "best_parser_match",
    "normalize_url",
    "scrape_url",
    "scrape_urls",
]
