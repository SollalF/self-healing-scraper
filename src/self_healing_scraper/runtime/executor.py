"""Apply declarative parser definitions to fetched HTML."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from self_healing_scraper.models import (
    FieldExtractor,
    PageContent,
    PageKind,
    ParserDefinition,
)


def execute_parser(
    page: PageContent,
    definition: ParserDefinition,
    page_kind: str,
    *,
    required_fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(page.html or "", "html.parser")
    source = definition.source_name or _guess_source(page.url)
    required = required_fields or ["title", "url"]

    if page_kind == PageKind.ARTICLE.value or not definition.item_selector:
        item = _extract_from_root(soup, page.url, definition, source)
        return [item] if item and _has_required(item, required) else []

    nodes = soup.select(definition.item_selector)
    items: list[dict[str, Any]] = []
    for node in nodes:
        item = _extract_from_element(node, page.url, definition, source)
        if item and _has_required(item, required):
            items.append(item)
    return items


def _extract_from_root(
    soup: BeautifulSoup,
    page_url: str,
    definition: ParserDefinition,
    source: str,
) -> dict[str, Any] | None:
    return _build_item(soup, page_url, definition, source, default_url=page_url)


def _extract_from_element(
    element: Tag,
    page_url: str,
    definition: ParserDefinition,
    source: str,
) -> dict[str, Any] | None:
    return _build_item(element, page_url, definition, source, default_url=None)


def _build_item(
    root: BeautifulSoup | Tag,
    page_url: str,
    definition: ParserDefinition,
    source: str,
    default_url: str | None,
) -> dict[str, Any] | None:
    data: dict[str, Any] = {}
    for field_name, extractor in definition.fields.items():
        data[field_name] = _extract_field(root, extractor, page_url)

    if data.get("url") in (None, "") and default_url:
        data["url"] = default_url
    if "source" not in data or not data.get("source"):
        data["source"] = source

    # Normalize string fields: strip whitespace; drop empty strings to None.
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            stripped = value.strip()
            cleaned[key] = stripped or None
        else:
            cleaned[key] = value
    return cleaned


def _has_required(item: dict[str, Any], required: list[str]) -> bool:
    for field in required:
        value = item.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return False
    return True


def _extract_field(
    root: BeautifulSoup | Tag, extractor: FieldExtractor, page_url: str
) -> str | None:
    nodes = root.select(extractor.selector)
    if not nodes:
        return None

    if extractor.many:
        values = [_node_value(node, extractor.attr, page_url) for node in nodes]
        cleaned = [v for v in values if v]
        return ", ".join(cleaned) if cleaned else None

    return _node_value(nodes[0], extractor.attr, page_url)


def _node_value(node: Tag, attr: str, page_url: str) -> str | None:
    if attr in {"text", "string"}:
        text = node.get_text(" ", strip=True)
        return text or None
    raw = node.get(attr)
    if raw is None:
        return None
    if isinstance(raw, list):
        raw = " ".join(str(part) for part in raw)
    value = str(raw).strip()
    if not value:
        return None
    if attr in {"href", "src"}:
        return urljoin(page_url, value)
    return value


def _guess_source(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "unknown"
