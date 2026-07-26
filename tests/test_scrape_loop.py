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
    ScrapeResult,
    ValidationCheck,
    ValidationSuite,
)
from self_healing_scraper.scrape import scrape_url
from self_healing_scraper.settings import Settings
from self_healing_scraper.store import InMemoryParserStore


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
