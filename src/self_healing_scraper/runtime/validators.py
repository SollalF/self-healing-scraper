"""Runtime validation suite for scrape outputs (core checks + plugins)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from self_healing_scraper.domain import CheckFn, ScrapeDomain
from self_healing_scraper.models import (
    PageContent,
    ValidationCheck,
    ValidationFailure,
    ValidationResult,
    ValidationSuite,
)

COOKIE_WALL_SNIPPETS = (
    "accept all cookies",
    "we use cookies",
    "enable javascript",
    "please enable cookies",
    "subscribe to continue",
    "sign in to continue reading",
)

CORE_KNOWN_CHECKS = frozenset(
    {
        "min_count",
        "max_count",
        "required_fields",
        "url_same_host",
        "field_min_length",
        "not_equals",
        "field_not_in",
        "url_matches",
        "field_matches",
        "no_cookie_wall",
    }
)


def run_validations(
    items: list[dict[str, Any]],
    suite: ValidationSuite,
    page: PageContent | None = None,
    *,
    domain: ScrapeDomain | None = None,
) -> ValidationResult:
    failures: list[ValidationFailure] = []
    for check in suite.checks:
        failure = _run_check(check, items, page, domain=domain)
        if failure:
            failures.append(failure)
    return ValidationResult(passed=not failures, failures=failures)


def _core_handlers() -> dict[str, CheckFn]:
    return {
        "min_count": _check_min_count,
        "max_count": _check_max_count,
        "required_fields": _check_required_fields,
        "url_same_host": _check_url_same_host,
        "field_min_length": _check_field_min_length,
        "not_equals": _check_not_equals,
        "field_not_in": _check_not_equals,
        "url_matches": _check_url_matches,
        "field_matches": _check_field_matches,
        "no_cookie_wall": _check_no_cookie_wall,
    }


def _run_check(
    check: ValidationCheck,
    items: list[dict[str, Any]],
    page: PageContent | None,
    *,
    domain: ScrapeDomain | None,
) -> ValidationFailure | None:
    handlers = _core_handlers()
    if domain is not None:
        handlers = {**handlers, **domain.extra_validators}
    handler = handlers.get(check.type)
    if handler is None:
        # Ignore invented check types so AI creativity does not hard-fail a scrape.
        return None
    return handler(check, items, page)


def _check_min_count(
    check: ValidationCheck,
    items: list[dict[str, Any]],
    page: PageContent | None,
) -> ValidationFailure | None:
    minimum = int(check.value if check.value is not None else 1)
    if len(items) < minimum:
        return ValidationFailure(
            check_type=check.type,
            message=check.message
            or f"Expected at least {minimum} items, got {len(items)}",
            details={"count": len(items), "minimum": minimum},
        )
    return None


def _check_max_count(
    check: ValidationCheck,
    items: list[dict[str, Any]],
    page: PageContent | None,
) -> ValidationFailure | None:
    maximum = int(check.value if check.value is not None else 500)
    if len(items) > maximum:
        return ValidationFailure(
            check_type=check.type,
            message=check.message
            or f"Expected at most {maximum} items, got {len(items)}",
            details={"count": len(items), "maximum": maximum},
        )
    return None


def _check_required_fields(
    check: ValidationCheck,
    items: list[dict[str, Any]],
    page: PageContent | None,
) -> ValidationFailure | None:
    fields = check.fields or ["title", "url"]
    missing: list[dict[str, str]] = []
    for index, item in enumerate(items):
        for field in fields:
            value = item.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append({"index": str(index), "field": field})
    if missing:
        return ValidationFailure(
            check_type=check.type,
            message=check.message or "Required fields missing on one or more items",
            details={"missing": missing[:20]},
        )
    return None


def _check_url_same_host(
    check: ValidationCheck,
    items: list[dict[str, Any]],
    page: PageContent | None,
) -> ValidationFailure | None:
    if page is None:
        return None
    host = _normalize_host(urlparse(page.url).netloc)
    bad = [
        str(item.get("url", ""))
        for item in items
        if _normalize_host(urlparse(str(item.get("url", ""))).netloc) != host
    ]
    if bad:
        return ValidationFailure(
            check_type=check.type,
            message=check.message or "Item URLs must share the page host",
            details={"bad_urls": bad[:10], "host": host},
        )
    return None


def _check_field_min_length(
    check: ValidationCheck,
    items: list[dict[str, Any]],
    page: PageContent | None,
) -> ValidationFailure | None:
    field = check.field or "title"
    minimum = int(check.value if check.value is not None else 1)
    short = []
    for item in items:
        value = item.get(field)
        text = value if isinstance(value, str) else ""
        if len(text.strip()) < minimum:
            short.append(str(item.get("url", "")))
    if short:
        return ValidationFailure(
            check_type=check.type,
            message=check.message or f"Field '{field}' shorter than {minimum}",
            details={"field": field, "urls": short[:10]},
        )
    return None


def _check_not_equals(
    check: ValidationCheck,
    items: list[dict[str, Any]],
    page: PageContent | None,
) -> ValidationFailure | None:
    field = check.field or "title"
    banned = {v.strip().lower() for v in (check.values or []) if v}
    if not banned:
        return None
    hits = []
    for item in items:
        value = item.get(field)
        if isinstance(value, str) and value.strip().lower() in banned:
            hits.append(value)
    if hits:
        return ValidationFailure(
            check_type=check.type,
            message=check.message or f"Field '{field}' matched banned values",
            details={"hits": hits[:10]},
        )
    return None


def _check_url_matches(
    check: ValidationCheck,
    items: list[dict[str, Any]],
    page: PageContent | None,
) -> ValidationFailure | None:
    # Force field=url so models cannot accidentally pattern-match image URLs here.
    scoped = check.model_copy(update={"field": "url"})
    return _check_field_matches(scoped, items, page)


def _check_field_matches(
    check: ValidationCheck,
    items: list[dict[str, Any]],
    page: PageContent | None,
) -> ValidationFailure | None:
    pattern = check.pattern
    if not pattern:
        return None
    field = check.field or "url"
    compiled = re.compile(pattern)
    bad = []
    for item in items:
        value = item.get(field)
        text = value if isinstance(value, str) else ""
        if text and not compiled.search(text):
            bad.append(text)
    if bad:
        return ValidationFailure(
            check_type=check.type,
            message=check.message or f"Field '{field}' did not match expected pattern",
            details={"values": bad[:10], "pattern": pattern, "field": field},
        )
    return None


def _check_no_cookie_wall(
    check: ValidationCheck,
    items: list[dict[str, Any]],
    page: PageContent | None,
) -> ValidationFailure | None:
    texts: list[str] = []
    if page and page.html:
        texts.append(page.html.lower()[:5000])
    for item in items:
        texts.append(str(item.get("content") or "").lower())
        texts.append(str(item.get("description") or "").lower())
    blob = "\n".join(texts)
    for snippet in COOKIE_WALL_SNIPPETS:
        if snippet in blob and not items:
            return ValidationFailure(
                check_type=check.type,
                message=check.message or f"Possible cookie/paywall text: {snippet}",
            )
    # If we have items but every content looks like a wall, fail.
    if items:
        wall_hits = 0
        for item in items:
            content = str(item.get("content") or item.get("description") or "").lower()
            if any(snippet in content for snippet in COOKIE_WALL_SNIPPETS):
                wall_hits += 1
        if wall_hits and wall_hits == len(items):
            return ValidationFailure(
                check_type=check.type,
                message=check.message or "All items look like cookie/paywall content",
            )
    return None


def _normalize_host(host: str) -> str:
    host = host.lower()
    return host[4:] if host.startswith("www.") else host
