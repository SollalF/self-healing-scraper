"""Shared fixtures."""

from __future__ import annotations

import pytest

from self_healing_scraper.domain import DomainPrompts, ScrapeDomain
from self_healing_scraper.models import (
    FieldExtractor,
    PageContent,
    ParserDefinition,
    ValidationCheck,
    ValidationSuite,
)


@pytest.fixture
def listing_html() -> str:
    return """
    <html><body>
      <ul class="posts">
        <li class="post">
          <h2 class="title"><a href="/2026/07/25/alpha/">Alpha Story</a></h2>
          <p class="dek">Alpha description here.</p>
          <time datetime="2026-07-25">July 25, 2026</time>
        </li>
        <li class="post">
          <h2 class="title"><a href="/2026/07/24/beta/">Beta Story</a></h2>
          <p class="dek">Beta description here.</p>
          <time datetime="2026-07-24">July 24, 2026</time>
        </li>
        <li class="post">
          <h2 class="title"><a href="/2026/07/23/gamma/">Gamma Story</a></h2>
          <p class="dek">Gamma description here.</p>
          <time datetime="2026-07-23">July 23, 2026</time>
        </li>
      </ul>
    </body></html>
    """


@pytest.fixture
def listing_page(listing_html: str) -> PageContent:
    return PageContent(
        url="https://techcrunch.com/latest/",
        html=listing_html,
        markdown=None,
        success=True,
    )


@pytest.fixture
def listing_definition() -> ParserDefinition:
    return ParserDefinition(
        js_enabled=False,
        item_selector="li.post",
        source_name="TechCrunch",
        fields={
            "title": FieldExtractor(selector="h2.title a", attr="text"),
            "url": FieldExtractor(selector="h2.title a", attr="href"),
            "description": FieldExtractor(selector="p.dek", attr="text"),
            "published_date": FieldExtractor(selector="time", attr="datetime"),
        },
    )


@pytest.fixture
def listing_validations() -> ValidationSuite:
    return ValidationSuite(
        checks=[
            ValidationCheck(type="min_count", value=3),
            ValidationCheck(type="required_fields", fields=["title", "url"]),
            ValidationCheck(type="field_min_length", field="title", value=5),
            ValidationCheck(type="url_same_host"),
        ]
    )


@pytest.fixture
def sample_items() -> list[dict]:
    return [
        {
            "title": "Alpha Story",
            "url": "https://techcrunch.com/2026/07/25/alpha/",
            "description": "Alpha description here.",
            "source": "TechCrunch",
            "published_date": "2026-07-25",
        },
        {
            "title": "Beta Story",
            "url": "https://techcrunch.com/2026/07/24/beta/",
            "description": "Beta description here.",
            "source": "TechCrunch",
            "published_date": "2026-07-24",
        },
        {
            "title": "Gamma Story",
            "url": "https://techcrunch.com/2026/07/23/gamma/",
            "description": "Gamma description here.",
            "source": "TechCrunch",
            "published_date": "2026-07-23",
        },
    ]


@pytest.fixture
def sample_domain() -> ScrapeDomain:
    return ScrapeDomain(
        prompts=DomainPrompts(
            create_system="create",
            create_user_template="{url} {page_kind_hint} {html_sample} {markdown_sample}",
            repair_system="repair",
            repair_user_template="{url} {current_parser} {failures} {html_sample} {markdown_sample}",
        ),
        default_required_fields=["title", "url"],
    )
