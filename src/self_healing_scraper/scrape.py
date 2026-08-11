"""Public scrape orchestration with self-healing parsers."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from self_healing_scraper.agent.create_parser import create_parser
from self_healing_scraper.agent.page_sample import sample_page_for_llm
from self_healing_scraper.agent.repair_parser import repair_parser
from self_healing_scraper.domain import ScrapeDomain
from self_healing_scraper.fetch.crawler import fetch_page
from self_healing_scraper.models import (
    PageContent,
    ParserDefinition,
    ParserStatus,
    ScrapeResult,
    ValidationResult,
    ValidationSuite,
)
from self_healing_scraper.runtime.executor import execute_parser
from self_healing_scraper.runtime.validators import run_validations
from self_healing_scraper.settings import Settings
from self_healing_scraper.store import ParserRecordLike, ParserStore

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    path = parts.path or "/"
    return urlunsplit((parts.scheme, parts.netloc.lower(), path, parts.query, ""))


async def _fetch_or_raise(
    url: str,
    *,
    definition: ParserDefinition | None,
    settings: Settings,
) -> PageContent:
    page = await fetch_page(url, definition=definition, settings=settings)
    if not page.success:
        raise RuntimeError(page.error_message or f"Failed to fetch {url}")
    return page


async def _ensure_parser(
    url: str,
    *,
    record: ParserRecordLike | None,
    store: ParserStore,
    domain: ScrapeDomain,
    settings: Settings,
) -> tuple[ParserRecordLike, PageContent, bool]:
    """Return (record, page, created_parser), creating a parser when none exists."""
    definition = store.definition_of(record) if record else None
    page = await _fetch_or_raise(url, definition=definition, settings=settings)

    if record is not None:
        return record, page, False

    logger.info("No parser for %s — creating via AI", url)
    generated = await create_parser(page, domain=domain, settings=settings)
    record = await store.create_from_generated(generated, status=ParserStatus.DRAFT)
    # Re-fetch with wait_for / js hints from the new definition.
    page = await _fetch_or_raise(
        url, definition=store.definition_of(record), settings=settings
    )
    return record, page, True


def _build_result(
    *,
    url: str,
    items: list[dict[str, Any]],
    parser_id: str | None,
    parser_version: int | None,
    domain: ScrapeDomain,
    created_parser: bool = False,
    repaired: bool = False,
    attempts: int = 1,
    from_cache: bool = False,
) -> ScrapeResult:
    result_items = items
    if domain.item_builder is not None:
        result_items = [domain.item_builder(item) for item in items]
    return ScrapeResult(
        url=url,
        items=result_items,
        parser_id=parser_id,
        parser_version=parser_version,
        created_parser=created_parser,
        repaired=repaired,
        attempts=attempts,
        from_cache=from_cache,
    )


async def _cached_result(
    url: str,
    *,
    record: ParserRecordLike,
    store: ParserStore,
    domain: ScrapeDomain,
    settings: Settings,
) -> ScrapeResult | None:
    """Reuse a stored run for this URL when the store offers one."""
    if record.page_kind not in settings.cached_page_kinds:
        return None

    cached = await store.find_cached_run(url, page_kind=record.page_kind)
    if cached is None:
        return None

    logger.info("Reusing stored %s result for %s", record.page_kind, url)
    return _build_result(
        url=url,
        items=cached.items,
        parser_id=cached.parser_id if cached.parser_id is not None else str(record.id),
        parser_version=(
            cached.parser_version
            if cached.parser_version is not None
            else record.version
        ),
        domain=domain,
        attempts=0,
        from_cache=True,
    )


async def _persist_success(
    *,
    url: str,
    store: ParserStore,
    record: ParserRecordLike,
    items: list[dict[str, Any]],
    page: PageContent,
    domain: ScrapeDomain,
    settings: Settings,
    created_parser: bool,
    repaired: bool,
    attempts: int,
) -> ScrapeResult:
    await store.update_parser(record, mark_success=True)
    await store.save_run(
        url=url,
        parser_id=record.id,
        parser_version=record.version,
        success=True,
        items=items,
        page_sample=sample_page_for_llm(page, settings).html_sample,
    )
    return _build_result(
        url=url,
        items=items,
        parser_id=str(record.id),
        parser_version=record.version,
        domain=domain,
        created_parser=created_parser,
        repaired=repaired,
        attempts=attempts,
    )


async def _persist_failure(
    *,
    url: str,
    store: ParserStore,
    record: ParserRecordLike,
    items: list[dict[str, Any]],
    page: PageContent,
    last_errors: list[dict],
    settings: Settings,
) -> None:
    await store.update_parser(
        record,
        status=ParserStatus.FAILED,
        last_error=str(last_errors),
    )
    await store.save_run(
        url=url,
        parser_id=record.id,
        parser_version=record.version,
        success=False,
        items=items,
        validation_errors=last_errors,
        page_sample=sample_page_for_llm(page, settings).html_sample,
        error_message="Validation failed after max repair attempts",
    )


async def _apply_repair(
    *,
    page: PageContent,
    record: ParserRecordLike,
    definition: ParserDefinition,
    validations: ValidationSuite,
    validation: ValidationResult,
    last_errors: list[dict],
    store: ParserStore,
    domain: ScrapeDomain,
    settings: Settings,
) -> ParserRecordLike:
    generated = await repair_parser(
        page=page,
        name=record.name,
        url_pattern=record.url_pattern,
        page_kind=record.page_kind,
        definition=definition,
        validations=validations,
        validation_result=validation,
        domain=domain,
        settings=settings,
    )
    return await store.update_parser(
        record,
        name=generated.name,
        url_pattern=generated.url_pattern,
        page_kind=generated.page_kind,
        definition=generated.definition,
        validations=generated.validations,
        status=ParserStatus.DRAFT,
        bump_version=True,
        last_error=str(last_errors),
    )


async def scrape_url(
    url: str,
    *,
    store: ParserStore,
    domain: ScrapeDomain,
    settings: Settings | None = None,
    force_refresh: bool = False,
) -> ScrapeResult:
    """Scrape a URL using a stored or newly created self-healing parser.

    Pages whose kind is in ``settings.cached_page_kinds`` reuse a stored run
    when the store returns one, skipping the fetch. Pass ``force_refresh`` to
    always hit the network.
    """
    cfg = settings or Settings()
    url = normalize_url(url)

    record = await store.find_by_url(url)
    if record is not None and not force_refresh:
        cached = await _cached_result(
            url, record=record, store=store, domain=domain, settings=cfg
        )
        if cached is not None:
            return cached

    record, page, created_parser = await _ensure_parser(
        url, record=record, store=store, domain=domain, settings=cfg
    )
    repaired = False
    attempts = 0
    max_attempts = max(1, cfg.max_repair_attempts)
    last_errors: list[dict] = []

    while attempts < max_attempts:
        attempts += 1
        definition = store.definition_of(record)
        validations = store.validations_of(record)

        # Refresh page with current wait hints after repair.
        if attempts > 1:
            page = await fetch_page(url, definition=definition, settings=cfg)
            if not page.success:
                last_errors = [{"message": page.error_message or "fetch failed"}]
                await store.update_parser(
                    record,
                    status=ParserStatus.FAILED,
                    last_error=page.error_message,
                )
                break

        items = execute_parser(
            page,
            definition,
            record.page_kind,
            required_fields=domain.default_required_fields,
        )
        validation = run_validations(items, validations, page, domain=domain)

        if validation.passed:
            return await _persist_success(
                url=url,
                store=store,
                record=record,
                items=items,
                page=page,
                domain=domain,
                settings=cfg,
                created_parser=created_parser,
                repaired=repaired,
                attempts=attempts,
            )

        last_errors = [f.model_dump() for f in validation.failures]
        logger.warning(
            "Validation failed for %s (attempt %s/%s): %s",
            url,
            attempts,
            max_attempts,
            last_errors,
        )

        if attempts >= max_attempts:
            await _persist_failure(
                url=url,
                store=store,
                record=record,
                items=items,
                page=page,
                last_errors=last_errors,
                settings=cfg,
            )
            break

        record = await _apply_repair(
            page=page,
            record=record,
            definition=definition,
            validations=validations,
            validation=validation,
            last_errors=last_errors,
            store=store,
            domain=domain,
            settings=cfg,
        )
        repaired = True

    raise RuntimeError(
        f"Failed to scrape {url} after {attempts} attempt(s): {last_errors}"
    )


async def scrape_urls(
    urls: list[str],
    *,
    store: ParserStore,
    domain: ScrapeDomain,
    settings: Settings | None = None,
    force_refresh: bool = False,
) -> list[ScrapeResult]:
    cfg = settings or Settings()
    results: list[ScrapeResult] = []
    for url in urls:
        results.append(
            await scrape_url(
                url,
                store=store,
                domain=domain,
                settings=cfg,
                force_refresh=force_refresh,
            )
        )
    return results
