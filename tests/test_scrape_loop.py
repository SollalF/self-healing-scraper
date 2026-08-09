"""Orchestration tests with mocked fetch/AI side effects."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from self_healing_scraper.domain import ScrapeDomain
from self_healing_scraper.models import (
    FieldExtractor,
    GeneratedParser,
    PageContent,
    ParserDefinition,
    ParserStatus,
    ScrapeResult,
    ValidationCheck,
    ValidationSuite,
)
from self_healing_scraper.scrape import scrape_url
from self_healing_scraper.settings import Settings
from self_healing_scraper.testing import InMemoryParserStore

ARTICLE_URL = "https://techcrunch.com/2026/07/25/alpha/"

ARTICLE_HTML = """
<html><body>
  <h1>Alpha Story</h1>
  <div class="body"><p>Alpha body text.</p></div>
</body></html>
"""


def _generated() -> GeneratedParser:
    return GeneratedParser(
        name="techcrunch-latest",
        url_pattern=r"https://techcrunch\.com/latest/?",
        page_kind="listing",
        definition=ParserDefinition(
            js_enabled=False,
            item_selector="li.post",
            source_name="TechCrunch",
            fields={
                "title": FieldExtractor(selector="h2.title a", attr="text"),
                "url": FieldExtractor(selector="h2.title a", attr="href"),
            },
        ),
        validations=ValidationSuite(
            checks=[
                ValidationCheck(type="min_count", value=1),
                ValidationCheck(type="required_fields", fields=["title", "url"]),
            ]
        ),
    )


def _article_generated() -> GeneratedParser:
    return GeneratedParser(
        name="techcrunch-article",
        url_pattern=r"https://techcrunch\.com/\d{4}/\d{2}/\d{2}/[^/]+/?",
        page_kind="article",
        definition=ParserDefinition(
            js_enabled=False,
            source_name="TechCrunch",
            fields={
                "title": FieldExtractor(selector="h1", attr="text"),
                "content": FieldExtractor(
                    selector="div.body p", attr="text", many=True
                ),
            },
        ),
        validations=ValidationSuite(
            checks=[
                ValidationCheck(type="min_count", value=1),
                ValidationCheck(type="required_fields", fields=["title", "url"]),
            ]
        ),
    )


async def _seed_active_parser(
    store: InMemoryParserStore,
    generated: GeneratedParser,
    *,
    url: str,
    items: list[dict] | None = None,
):
    """Register an active parser and optionally a stored successful run."""
    record = await store.create_from_generated(generated, status=ParserStatus.ACTIVE)
    if items is not None:
        await store.save_run(
            url=url,
            parser_id=record.id,
            parser_version=record.version,
            success=True,
            items=items,
        )
    return record


@pytest.mark.asyncio
async def test_scrape_creates_parser_when_missing(
    listing_html: str, sample_domain: ScrapeDomain
) -> None:
    settings = Settings(
        llm_api_key="test",
        max_repair_attempts=2,
    )
    page = PageContent(
        url="https://techcrunch.com/latest/",
        html=listing_html,
        success=True,
    )
    generated = _generated()
    store = InMemoryParserStore()

    with (
        patch("self_healing_scraper.scrape.fetch_page", AsyncMock(return_value=page)),
        patch(
            "self_healing_scraper.scrape.create_parser",
            AsyncMock(return_value=generated),
        ),
    ):
        result = await scrape_url(
            "https://techcrunch.com/latest/",
            store=store,
            domain=sample_domain,
            settings=settings,
        )

    assert isinstance(result, ScrapeResult)
    assert result.created_parser is True
    assert len(result.items) == 3
    assert len(store.parsers) == 1
    assert store.parsers[0].status == "active"
    assert store.runs and store.runs[0]["success"] is True
    assert result.parser_id == str(store.parsers[0].id)
    assert result.from_cache is False


@pytest.mark.asyncio
async def test_article_reuses_stored_run_without_fetching(
    sample_domain: ScrapeDomain,
) -> None:
    store = InMemoryParserStore()
    stored_items = [
        {"title": "Alpha Story", "url": ARTICLE_URL, "content": "Alpha body text."}
    ]
    record = await _seed_active_parser(
        store, _article_generated(), url=ARTICLE_URL, items=stored_items
    )
    fetch = AsyncMock()

    with patch("self_healing_scraper.scrape.fetch_page", fetch):
        result = await scrape_url(
            ARTICLE_URL,
            store=store,
            domain=sample_domain,
            settings=Settings(),
        )

    fetch.assert_not_awaited()
    assert result.from_cache is True
    assert result.attempts == 0
    assert result.items == stored_items
    assert result.parser_id == str(record.id)
    assert len(store.runs) == 1


@pytest.mark.asyncio
async def test_force_refresh_rescrapes_cached_article(
    sample_domain: ScrapeDomain,
) -> None:
    store = InMemoryParserStore()
    await _seed_active_parser(
        store,
        _article_generated(),
        url=ARTICLE_URL,
        items=[{"title": "Stale Title", "url": ARTICLE_URL}],
    )
    page = PageContent(url=ARTICLE_URL, html=ARTICLE_HTML, success=True)
    fetch = AsyncMock(return_value=page)

    with patch("self_healing_scraper.scrape.fetch_page", fetch):
        result = await scrape_url(
            ARTICLE_URL,
            store=store,
            domain=sample_domain,
            settings=Settings(),
            force_refresh=True,
        )

    fetch.assert_awaited()
    assert result.from_cache is False
    assert result.items == [
        {
            "title": "Alpha Story",
            "content": "Alpha body text.",
            "url": ARTICLE_URL,
            "source": "TechCrunch",
        }
    ]
    assert len(store.runs) == 2


@pytest.mark.asyncio
async def test_listing_ignores_stored_run(
    listing_html: str, sample_domain: ScrapeDomain
) -> None:
    url = "https://techcrunch.com/latest/"
    store = InMemoryParserStore()
    await _seed_active_parser(
        store, _generated(), url=url, items=[{"title": "Stale", "url": url}]
    )
    page = PageContent(url=url, html=listing_html, success=True)
    fetch = AsyncMock(return_value=page)

    with patch("self_healing_scraper.scrape.fetch_page", fetch):
        result = await scrape_url(
            url, store=store, domain=sample_domain, settings=Settings()
        )

    fetch.assert_awaited()
    assert result.from_cache is False
    assert len(result.items) == 3


@pytest.mark.asyncio
async def test_listing_reuses_stored_run_when_configured(
    sample_domain: ScrapeDomain,
) -> None:
    url = "https://techcrunch.com/latest/"
    store = InMemoryParserStore()
    stored_items = [{"title": "Stale", "url": url}]
    await _seed_active_parser(store, _generated(), url=url, items=stored_items)
    fetch = AsyncMock()

    with patch("self_healing_scraper.scrape.fetch_page", fetch):
        result = await scrape_url(
            url,
            store=store,
            domain=sample_domain,
            settings=Settings(cached_page_kinds={"listing", "article"}),
        )

    fetch.assert_not_awaited()
    assert result.from_cache is True
    assert result.items == stored_items
