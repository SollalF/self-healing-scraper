"""Smoke test for InMemoryParserStore matching + persistence."""

from __future__ import annotations

import pytest

from self_healing_scraper.models import (
    GeneratedParser,
    ParserDefinition,
    ParserStatus,
    ValidationSuite,
)
from self_healing_scraper.store import InMemoryParserStore


@pytest.mark.asyncio
async def test_memory_store_roundtrip() -> None:
    store = InMemoryParserStore()
    generated = GeneratedParser(
        name="example",
        url_pattern=r"https://example\.com/.*",
        page_kind="listing",
        definition=ParserDefinition(fields={}),
        validations=ValidationSuite(checks=[]),
    )
    record = await store.create_from_generated(
        generated, status=ParserStatus.DRAFT
    )
    found = await store.find_by_url("https://example.com/a")
    assert found is not None
    assert found.id == record.id

    await store.update_parser(record, mark_success=True)
    active = await store.find_by_url("https://example.com/a")
    assert active is not None
    assert active.status == "active"

    await store.save_run(
        url="https://example.com/a",
        parser_id=record.id,
        parser_version=1,
        success=True,
        items=[{"title": "x", "url": "https://example.com/a"}],
    )
    assert len(store.runs) == 1
