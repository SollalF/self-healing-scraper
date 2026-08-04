"""Crawl4AI-backed page fetcher (SSR + SPA)."""

from __future__ import annotations

import logging

from self_healing_scraper.models import PageContent, ParserDefinition
from self_healing_scraper.settings import Settings

logger = logging.getLogger(__name__)


async def fetch_page(
    url: str,
    definition: ParserDefinition | None = None,
    settings: Settings | None = None,
) -> PageContent:
    """Fetch a URL with JS rendering when needed."""
    cfg = settings or Settings()
    js_enabled = True if definition is None else definition.js_enabled
    wait_for = None if definition is None else definition.wait_for

    logger.info("Fetching %s (js_enabled=%s, wait_for=%s)", url, js_enabled, wait_for)
    return await _crawl(url, js_enabled=js_enabled, wait_for=wait_for, settings=cfg)


async def _crawl(
    url: str,
    *,
    js_enabled: bool,
    wait_for: str | None,
    settings: Settings,
) -> PageContent:
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "crawl4ai is required. Install dependencies and run "
            "`crawl4ai-setup` / install Playwright browsers."
        ) from exc

    browser_config = BrowserConfig(headless=True, verbose=False)
    if js_enabled and wait_for is not None:
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=settings.crawl_timeout_ms,
            wait_for=wait_for,
        )
    else:
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=settings.crawl_timeout_ms,
        )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)

    if not result.success:
        return PageContent(
            url=url,
            html="",
            markdown=None,
            success=False,
            error_message=result.error_message or "Unknown crawl failure",
        )

    html = result.cleaned_html or result.html or ""
    markdown = None
    if result.markdown:
        markdown = (
            result.markdown.raw_markdown
            if hasattr(result.markdown, "raw_markdown")
            else str(result.markdown)
        )

    return PageContent(
        url=url,
        html=html,
        markdown=markdown,
        success=True,
    )
