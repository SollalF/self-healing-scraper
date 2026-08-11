"""Unit tests for HTML sampling helpers."""

from __future__ import annotations

from self_healing_scraper.agent.html_sample import html_sample, html_sample_for_repair
from self_healing_scraper.models import FieldExtractor, ParserDefinition


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


def test_html_sample_for_repair_skips_nav_prefix() -> None:
    html = _nav_then_listing_html()
    sample = html_sample_for_repair(html, limit=12_000)
    assert "Hello" in sample
    assert 'href="/e/1"' in sample
    assert sample != html[:12_000]


def test_html_sample_for_repair_uses_item_selector_markers() -> None:
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
    sample = html_sample_for_repair(html, limit=12_000, definition=definition)
    assert "Event" in sample
    assert "discover-search-desktop-card" in sample
    assert sample != html[:12_000]
