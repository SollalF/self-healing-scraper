"""Unit tests for shared page sampling helpers."""

from __future__ import annotations

from self_healing_scraper.agent.page_sample import (
    compact_html_for_llm,
    html_sample,
    html_sample_for_llm,
    markdown_sample_for_llm,
    sample_page_for_llm,
)
from self_healing_scraper.models import FieldExtractor, PageContent, ParserDefinition
from self_healing_scraper.settings import Settings


def _nav_then_listing_html(*, card_class: str = "card") -> str:
    return (
        "<nav>"
        + ("x" * 20_000)
        + "</nav>"
        + f'<main><div class="{card_class}"><h3>Hello</h3>'
        + '<a href="/e/1">x</a></div></main>'
    )


def test_html_sample_skips_nav_prefix() -> None:
    html = _nav_then_listing_html()
    sample = html_sample(html, limit=12_000)
    assert "Hello" in sample
    assert 'href="/e/1"' in sample
    assert sample != html[:12_000]


def test_html_sample_falls_back_to_tail_without_main() -> None:
    html = (
        "<header>"
        + ("y" * 20_000)
        + "</header>"
        + '<div class="listing"><h3>Tail Item</h3></div>'
    )
    sample = html_sample(html, limit=12_000)
    assert "Tail Item" in sample
    assert sample != html[:12_000]


def test_html_sample_for_llm_skips_nav_prefix() -> None:
    html = _nav_then_listing_html()
    sample = html_sample_for_llm(html, limit=12_000)
    assert "Hello" in sample
    assert 'href="/e/1"' in sample
    assert sample != html[:12_000]


def test_html_sample_for_llm_uses_item_selector_markers() -> None:
    html = (
        "<nav>"
        + ("x" * 20_000)
        + "</nav>"
        + '<div class="discover-search-desktop-card"><h3>Event</h3></div>'
    )
    definition = ParserDefinition(
        item_selector=".discover-search-desktop-card, [data-testid='event-card']",
        fields={
            "title": FieldExtractor(selector="h2, h3", attr="text"),
            "url": FieldExtractor(selector="a[href*='/e/']", attr="href"),
        },
    )
    sample = html_sample_for_llm(html, limit=12_000, definition=definition)
    assert "Event" in sample
    assert "discover-search-desktop-card" in sample
    assert sample != html[:12_000]


def test_markdown_sample_trims_nav_and_strips_image_urls() -> None:
    nav = "Log In\nSign Up\n" * 2000
    listing = "\n".join(
        [
            f"* [![Event {i}](https://cdn.example.com/{i}.jpg)](/e/{i})"
            for i in range(20)
        ]
    )
    markdown = nav + "Events in Hong Kong\n" + listing
    sample = markdown_sample_for_llm(markdown, limit=12_000)
    raw_head = markdown[:12_000]
    assert sample.count("/e/") > raw_head.count("/e/")
    assert "Events in Hong Kong" in sample
    assert "https://cdn.example.com/" not in sample


def test_compact_html_for_llm_keeps_selector_attrs() -> None:
    html = (
        '<div class="card" style="color:red" data-testid="event" aria-label="x">'
        '<img src="https://example.com/x.jpg" width="100" alt="y">'
        '<a href="/e/1">Title</a></div>'
    )
    compact = compact_html_for_llm(html)
    assert 'class="card"' in compact
    assert 'href="/e/1"' in compact
    assert "https://example.com" not in compact
    assert "style=" not in compact


def test_sample_page_for_llm_splits_budget() -> None:
    page = PageContent(
        url="https://example.com/list",
        html=_nav_then_listing_html(),
        markdown="nav\n" * 1000 + "Events in City\n" + "/e/1\n" * 500,
        success=True,
    )
    samples = sample_page_for_llm(page, Settings(page_sample_chars=10_000))
    assert len(samples.html_sample) <= 4_000 + 200  # compact may add wrapper bytes
    assert len(samples.markdown_sample) <= 6_000
    assert "/e/" in samples.markdown_sample
    assert "Hello" in samples.html_sample


def test_sample_page_for_llm_html_only_uses_full_budget() -> None:
    page = PageContent(
        url="https://example.com/list",
        html=_nav_then_listing_html(),
        markdown=None,
        success=True,
    )
    samples = sample_page_for_llm(page, Settings(page_sample_chars=8_000))
    assert samples.markdown_sample == ""
    assert "Hello" in samples.html_sample
