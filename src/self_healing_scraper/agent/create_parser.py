"""AI-assisted parser creation."""

from __future__ import annotations

from urllib.parse import urlparse

from self_healing_scraper.agent.llm import complete_json
from self_healing_scraper.agent.schema import generated_parser_json_schema
from self_healing_scraper.domain import ScrapeDomain
from self_healing_scraper.models import (
    GeneratedParser,
    PageContent,
    PageKind,
    ValidationCheck,
    ValidationSuite,
)
from self_healing_scraper.settings import Settings


def _page_kind_hint(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    # Heuristic only — the model may override.
    articleish = (
        any(part.isdigit() and len(part) >= 4 for part in path.split("/") if part)
        or path.count("/") >= 3
    )
    return PageKind.ARTICLE.value if articleish else PageKind.LISTING.value


def _html_sample(html: str, limit: int) -> str:
    """Prefer the main content region so chrome/nav does not eat the sample budget."""
    lowered = html.lower()
    for marker in ("<main", 'role="main"', 'id="content"', 'class="content"'):
        idx = lowered.find(marker)
        if idx != -1:
            start = max(0, idx - 200)
            return html[start : start + limit]
    # Fall back to the middle/end of the document where listings often live.
    if len(html) > limit:
        return html[-(limit):]
    return html


def ensure_minimal_validations(
    parser: GeneratedParser,
    *,
    required_fields: list[str],
) -> GeneratedParser:
    """JSON Schema cannot require specific check types inside an array."""
    types = {check.type for check in parser.validations.checks}
    checks = list(parser.validations.checks)
    if "min_count" not in types:
        checks.insert(0, ValidationCheck(type="min_count", value=1))
    if "required_fields" not in types:
        checks.append(
            ValidationCheck(type="required_fields", fields=list(required_fields))
        )
    if checks == list(parser.validations.checks):
        return parser
    return parser.model_copy(
        update={"validations": ValidationSuite(checks=checks)},
    )


async def create_parser(
    page: PageContent,
    domain: ScrapeDomain,
    settings: Settings | None = None,
) -> GeneratedParser:
    cfg = settings or Settings()
    # Markdown from Crawl4AI is usually denser for listings than truncated HTML.
    markdown = (page.markdown or "")[: cfg.page_sample_chars]
    sample = _html_sample(page.html, min(cfg.page_sample_chars, 8000))
    known_checks = known_checks_for_domain(domain)
    payload = await complete_json(
        system=domain.prompts.create_system,
        user=domain.prompts.create_user_template.format(
            url=page.url,
            page_kind_hint=_page_kind_hint(page.url),
            html_sample=sample,
            markdown_sample=markdown,
        ),
        settings=cfg,
        json_schema=generated_parser_json_schema(known_checks),
        schema_name="generated_parser",
    )
    return ensure_minimal_validations(
        GeneratedParser.model_validate(payload),
        required_fields=domain.default_required_fields,
    )


def known_checks_for_domain(domain: ScrapeDomain) -> frozenset[str]:
    from self_healing_scraper.runtime.validators import CORE_KNOWN_CHECKS

    return CORE_KNOWN_CHECKS | domain.known_checks | frozenset(domain.extra_validators)
