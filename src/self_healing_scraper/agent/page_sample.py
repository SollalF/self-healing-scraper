"""Shared page sampling for LLM create/repair prompts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from self_healing_scraper.models import PageContent, ParserDefinition
    from self_healing_scraper.settings import Settings

_MAIN_MARKERS = ("<main", 'role="main"', 'id="content"', 'class="content"')

_COMMON_LISTING_MARKERS = (
    "<article",
    'href="/e/"',
    "href='/e/'",
    'data-testid="search-event"',
    'data-testid="event-card"',
)

_MARKDOWN_LISTING_MARKERS = (
    "/e/",
    "Events in",
    "## ",
    "discover-search",
)

_LLM_HTML_ATTRS = frozenset(
    {"class", "id", "href", "datetime", "data-testid", "role", "itemprop"}
)

_CLASS_RE = re.compile(r"\.([a-zA-Z0-9_-]+)")
_ID_RE = re.compile(r"#([a-zA-Z0-9_-]+)")
_ATTR_RE = re.compile(r"\[([a-zA-Z0-9_-]+)(?:=(?:['\"])([^'\"]*)(?:['\"]))?\]")
_IMAGE_MD_RE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")


@dataclass(frozen=True)
class PageSamples:
    html_sample: str
    markdown_sample: str


def sample_page_for_llm(
    page: PageContent,
    settings: Settings,
    *,
    definition: ParserDefinition | None = None,
) -> PageSamples:
    """Build HTML and markdown samples under a shared token budget."""
    budget = settings.page_sample_chars
    markdown_raw = page.markdown or ""
    has_markdown = bool(markdown_raw.strip())
    html_limit, markdown_limit = _split_budget(budget, has_markdown=has_markdown)

    html = compact_html_for_llm(
        html_sample_for_llm(page.html, html_limit, definition=definition),
    )
    markdown = markdown_sample_for_llm(markdown_raw, markdown_limit)
    return PageSamples(html_sample=html, markdown_sample=markdown)


def html_sample(html: str, limit: int) -> str:
    """Prefer the main content region so chrome/nav does not eat the sample budget."""
    window = _window_around_marker(html, limit, _MAIN_MARKERS)
    if window is not None:
        return window
    if len(html) > limit:
        return html[-limit:]
    return html


def html_sample_for_llm(
    html: str,
    limit: int,
    *,
    definition: ParserDefinition | None = None,
) -> str:
    """Sample HTML for LLM prompts, biased toward listing/item content."""
    markers: list[str] = []
    if definition is not None:
        if definition.item_selector:
            markers.extend(_markers_from_css_selector(definition.item_selector))
        for extractor in definition.fields.values():
            markers.extend(_markers_from_css_selector(extractor.selector))
    markers.extend(_COMMON_LISTING_MARKERS)
    markers.extend(_MAIN_MARKERS)
    window = _window_around_marker(html, limit, markers)
    if window is not None:
        return window
    return html_sample(html, limit)


def markdown_sample_for_llm(markdown: str, limit: int) -> str:
    """Trim leading chrome and drop image URLs before capping length."""
    if not markdown:
        return ""
    trimmed = _trim_markdown_to_content(markdown)
    compact = _IMAGE_MD_RE.sub(r"![\1]", trimmed)
    return compact[:limit]


def compact_html_for_llm(html: str) -> str:
    """Drop non-semantic attrs/tags unlikely to help selector inference."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "svg", "noscript", "iframe"]):
        tag.decompose()
    for element in soup.find_all(True):
        if element.get("aria-hidden") == "true" or element.has_attr("hidden"):
            element.decompose()
            continue
        element.attrs = {
            key: value for key, value in element.attrs.items() if key in _LLM_HTML_ATTRS
        }
    return str(soup)


def _split_budget(total: int, *, has_markdown: bool) -> tuple[int, int]:
    if not has_markdown:
        return total, 0
    # Markdown is denser for listing titles/links; bias budget slightly that way.
    html_limit = max(1, int(total * 0.4))
    markdown_limit = max(1, total - html_limit)
    return html_limit, markdown_limit


def _trim_markdown_to_content(markdown: str) -> str:
    lowered = markdown.lower()
    start = 0
    for marker in _MARKDOWN_LISTING_MARKERS:
        idx = lowered.find(marker.lower())
        if idx != -1:
            start = idx if start == 0 else min(start, idx)
    if start:
        start = max(0, start - 200)
    return markdown[start:]


def _window_around_marker(
    html: str,
    limit: int,
    markers: tuple[str, ...] | list[str],
) -> str | None:
    lowered = html.lower()
    for marker in markers:
        if not marker:
            continue
        idx = lowered.find(marker.lower())
        if idx != -1:
            start = max(0, idx - 200)
            return html[start : start + limit]
    return None


def _markers_from_css_selector(selector: str) -> list[str]:
    markers: list[str] = []
    for part in selector.split(","):
        part = part.strip()
        for match in _CLASS_RE.finditer(part):
            cls = match.group(1)
            markers.append(cls)
            markers.append(f'class="{cls}"')
            markers.append(f"class='{cls}'")
        for match in _ID_RE.finditer(part):
            id_ = match.group(1)
            markers.append(f'id="{id_}"')
        for match in _ATTR_RE.finditer(part):
            attr, val = match.group(1), match.group(2)
            if val:
                markers.append(f'{attr}="{val}"')
                markers.append(f"{attr}='{val}'")
            else:
                markers.append(attr)
    return markers
