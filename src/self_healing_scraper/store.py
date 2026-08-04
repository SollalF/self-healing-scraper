"""Parser persistence Protocol and matching helpers."""

from __future__ import annotations

import re
import uuid
from typing import Any, Protocol, runtime_checkable

from self_healing_scraper.models import (
    GeneratedParser,
    ParserDefinition,
    ParserStatus,
    ValidationSuite,
)


@runtime_checkable
class ParserRecordLike(Protocol):
    id: uuid.UUID
    name: str
    url_pattern: str
    page_kind: str
    version: int


def best_parser_match[T: ParserRecordLike](url: str, parsers: list[T]) -> T | None:
    """Return the longest regex match, breaking ties by highest version."""
    matches: list[tuple[int, T]] = []
    for parser in parsers:
        try:
            compiled = re.compile(parser.url_pattern)
        except re.error:
            continue
        if compiled.search(url):
            matches.append((len(parser.url_pattern), parser))
    if not matches:
        return None
    matches.sort(key=lambda item: (-item[0], -item[1].version))
    return matches[0][1]


class ParserStore(Protocol):
    """Application-owned persistence for parsers and scrape runs."""

    async def find_by_url(self, url: str) -> ParserRecordLike | None: ...

    async def create_from_generated(
        self,
        generated: GeneratedParser,
        *,
        status: ParserStatus = ParserStatus.DRAFT,
    ) -> ParserRecordLike: ...

    async def update_parser(
        self,
        record: ParserRecordLike,
        *,
        name: str | None = None,
        url_pattern: str | None = None,
        page_kind: str | None = None,
        definition: ParserDefinition | None = None,
        validations: ValidationSuite | None = None,
        status: ParserStatus | None = None,
        bump_version: bool = False,
        last_error: str | None = None,
        mark_success: bool = False,
    ) -> ParserRecordLike: ...

    async def save_run(
        self,
        *,
        url: str,
        parser_id: uuid.UUID | None,
        parser_version: int | None,
        success: bool,
        items: list[dict[str, Any]] | None = None,
        validation_errors: list[dict[str, Any]] | None = None,
        page_sample: str | None = None,
        error_message: str | None = None,
    ) -> Any: ...

    def definition_of(self, record: ParserRecordLike) -> ParserDefinition: ...

    def validations_of(self, record: ParserRecordLike) -> ValidationSuite: ...
