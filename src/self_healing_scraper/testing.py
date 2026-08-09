"""Test / smoke helpers — not part of the production scrape surface."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from self_healing_scraper.models import (
    CachedRun,
    GeneratedParser,
    ParserDefinition,
    ParserStatus,
    ValidationSuite,
)
from self_healing_scraper.store import ParserRecordLike, best_parser_match


class _MemoryRecord:
    def __init__(
        self,
        *,
        name: str,
        url_pattern: str,
        page_kind: str,
        definition: dict[str, Any],
        validations: dict[str, Any],
        status: str,
    ) -> None:
        self.id = uuid.uuid4()
        self.name = name
        self.url_pattern = url_pattern
        self.page_kind = page_kind
        self.definition = definition
        self.validations = validations
        self.version = 1
        self.status = status
        self.last_error: str | None = None
        self.last_success_at: datetime | None = None
        self.updated_at = datetime.now(UTC)


class InMemoryParserStore:
    """Simple store for tests and smoke scripts."""

    def __init__(self, *, reuse_cached_runs: bool = True) -> None:
        self.parsers: list[_MemoryRecord] = []
        self.runs: list[dict[str, Any]] = []
        self.reuse_cached_runs = reuse_cached_runs

    async def list_candidates(
        self, statuses: list[str] | None = None
    ) -> list[_MemoryRecord]:
        if statuses is None:
            return list(self.parsers)
        allowed = set(statuses)
        return [p for p in self.parsers if p.status in allowed]

    async def find_by_url(self, url: str) -> _MemoryRecord | None:
        active = await self.list_candidates([ParserStatus.ACTIVE.value])
        match = best_parser_match(url, active)
        if match:
            return match
        drafts = await self.list_candidates([ParserStatus.DRAFT.value])
        return best_parser_match(url, drafts)

    def definition_of(self, record: ParserRecordLike) -> ParserDefinition:
        assert isinstance(record, _MemoryRecord)
        return ParserDefinition.model_validate(record.definition)

    def validations_of(self, record: ParserRecordLike) -> ValidationSuite:
        assert isinstance(record, _MemoryRecord)
        return ValidationSuite.model_validate(record.validations)

    async def create_from_generated(
        self,
        generated: GeneratedParser,
        *,
        status: ParserStatus = ParserStatus.DRAFT,
    ) -> _MemoryRecord:
        record = _MemoryRecord(
            name=generated.name,
            url_pattern=generated.url_pattern,
            page_kind=generated.page_kind,
            definition=generated.definition.model_dump(),
            validations=generated.validations.model_dump(),
            status=status.value,
        )
        self.parsers.append(record)
        return record

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
    ) -> _MemoryRecord:
        assert isinstance(record, _MemoryRecord)
        if name is not None:
            record.name = name
        if url_pattern is not None:
            record.url_pattern = url_pattern
        if page_kind is not None:
            record.page_kind = page_kind
        if definition is not None:
            record.definition = definition.model_dump()
        if validations is not None:
            record.validations = validations.model_dump()
        if status is not None:
            record.status = status.value
        if bump_version:
            record.version += 1
        if last_error is not None:
            record.last_error = last_error
        if mark_success:
            record.last_success_at = datetime.now(UTC)
            record.last_error = None
            record.status = ParserStatus.ACTIVE.value
        record.updated_at = datetime.now(UTC)
        return record

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
    ) -> dict[str, Any]:
        run = {
            "url": url,
            "parser_id": parser_id,
            "parser_version": parser_version,
            "success": success,
            "items": list(items) if items else None,
            "validation_errors": validation_errors,
            "page_sample": page_sample,
            "error_message": error_message,
        }
        self.runs.append(run)
        return run

    async def find_cached_run(self, url: str, *, page_kind: str) -> CachedRun | None:
        """Reuse the newest successful run that produced items, with no expiry."""
        if not self.reuse_cached_runs:
            return None
        for run in reversed(self.runs):
            if run["url"] == url and run["success"] and run["items"]:
                parser_id = run["parser_id"]
                return CachedRun(
                    items=list(run["items"]),
                    parser_id=str(parser_id) if parser_id else None,
                    parser_version=run["parser_version"],
                )
        return None
