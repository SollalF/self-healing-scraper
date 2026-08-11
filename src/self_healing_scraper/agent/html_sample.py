"""HTML sampling for LLM prompts."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from self_healing_scraper.models import ParserDefinition

_MAIN_MARKERS = ("<main", 'role="main"', 'id="content"', 'class="content"')

_COMMON_LISTING_MARKERS = (
    "<article",
    'href="/e/"',
    "href='/e/'",
    'data-testid="search-event"',
    'data-testid="event-card"',
)

_CLASS_RE = re.compile(r"\.([a-zA-Z0-9_-]+)")
_ID_RE = re.compile(r"#([a-zA-Z0-9_-]+)")
_ATTR_RE = re.compile(r"\[([a-zA-Z0-9_-]+)(?:=(?:['\"])([^'\"]*)(?:['\"]))?\]")


def html_sample(html: str, limit: int) -> str:
    """Prefer the main content region so chrome/nav does not eat the sample budget."""
    window = _window_around_marker(html, limit, _MAIN_MARKERS)
    if window is not None:
        return window
    if len(html) > limit:
        return html[-limit:]
    return html


def html_sample_for_repair(
    html: str,
    limit: int,
    *,
    definition: ParserDefinition | None = None,
) -> str:
    """Sample HTML for repair prompts, biased toward listing/item content."""
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
