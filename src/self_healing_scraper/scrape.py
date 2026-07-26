"""Public scrape orchestration with self-healing parsers."""

from __future__ import annotations

import logging
from urllib.parse import urlsplit, urlunsplit

from self_healing_scraper.agent.create_parser import create_parser
from self_healing_scraper.agent.repair_parser import repair_parser
from self_healing_scraper.domain import ScrapeDomain
from self_healing_scraper.fetch.crawler import fetch_page
from self_healing_scraper.models import ParserStatus, ScrapeResult
from self_healing_scraper.runtime.executor import execute_parser
from self_healing_scraper.runtime.validators import run_validations
from self_healing_scraper.settings import Settings
from self_healing_scraper.store import ParserStore

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    path = parts.path or "/"
    return urlunsplit((parts.scheme, parts.netloc.lower(), path, parts.query, ""))


async def scrape_url(
    url: str,
    *,
    store: ParserStore,
    domain: ScrapeDomain,
    settings: Settings | None = None,
) -> ScrapeResult:
    """Scrape a URL using a stored or newly created self-healing parser."""
    cfg = settings or Settings()
    url = normalize_url(url)

    record = await store.find_by_url(url)
    created_parser = False
    repaired = False

    # Initial fetch without parser hints (or with existing definition hints).
    definition = store.definition_of(record) if record else None
    page = await fetch_page(url, definition=definition, settings=cfg)
    if not page.success:
        raise RuntimeError(page.error_message or f"Failed to fetch {url}")

    if record is None:
        logger.info("No parser for %s — creating via AI", url)
        generated = await create_parser(page, domain=domain, settings=cfg)
        record = await store.create_from_generated(generated, status=ParserStatus.DRAFT)
        created_parser = True
        # Re-fetch with wait_for / js hints from the new definition.
        definition = store.definition_of(record)
        page = await fetch_page(url, definition=definition, settings=cfg)
        if not page.success:
            raise RuntimeError(page.error_message or f"Failed to fetch {url}")

    attempts = 0
    max_attempts = max(1, cfg.max_repair_attempts)
    last_errors: list[dict] = []

    while attempts < max_attempts:
        attempts += 1
        definition = store.definition_of(record)
        validations = store.validations_of(record)

        # Optionally refresh page with current wait hints after repair.
        if attempts > 1 or created_parser:
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
            await store.update_parser(record, mark_success=True)
            await store.save_run(
                url=url,
                parser_id=record.id,
                parser_version=record.version,
                success=True,
                items=items,
                page_sample=page.html[: cfg.page_sample_chars],
            )
            result_items = items
            if domain.item_builder is not None:
                result_items = [domain.item_builder(item) for item in items]
            return ScrapeResult(
                url=url,
                items=result_items,
                parser_id=str(record.id),
                parser_version=record.version,
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
                page_sample=page.html[: cfg.page_sample_chars],
                error_message="Validation failed after max repair attempts",
            )
            break

        generated = await repair_parser(
            page=page,
            name=record.name,
            url_pattern=record.url_pattern,
            page_kind=record.page_kind,
            definition=definition,
            validations=validations,
            validation_result=validation,
            domain=domain,
            settings=cfg,
        )
        record = await store.update_parser(
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
) -> list[ScrapeResult]:
    cfg = settings or Settings()
    results: list[ScrapeResult] = []
    for url in urls:
        results.append(await scrape_url(url, store=store, domain=domain, settings=cfg))
    return results
