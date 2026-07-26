"""AI-assisted parser repair."""

from __future__ import annotations

import json

from self_healing_scraper.agent.create_parser import known_checks_for_domain
from self_healing_scraper.agent.llm import complete_json
from self_healing_scraper.agent.normalize import normalize_generated_payload
from self_healing_scraper.domain import ScrapeDomain
from self_healing_scraper.models import (
    GeneratedParser,
    PageContent,
    ParserDefinition,
    ValidationResult,
    ValidationSuite,
)
from self_healing_scraper.settings import Settings


async def repair_parser(
    *,
    page: PageContent,
    name: str,
    url_pattern: str,
    page_kind: str,
    definition: ParserDefinition,
    validations: ValidationSuite,
    validation_result: ValidationResult,
    domain: ScrapeDomain,
    settings: Settings | None = None,
) -> GeneratedParser:
    cfg = settings or Settings()
    current = {
        "name": name,
        "url_pattern": url_pattern,
        "page_kind": page_kind,
        "definition": definition.model_dump(),
        "validations": validations.model_dump(),
    }
    payload = await complete_json(
        system=domain.prompts.repair_system,
        user=domain.prompts.repair_user_template.format(
            url=page.url,
            current_parser=json.dumps(current, indent=2),
            failures=validation_result.model_dump_json(indent=2),
            html_sample=page.html[: cfg.page_sample_chars],
        ),
        settings=cfg,
    )
    # Preserve identity fields if the model omits them.
    payload.setdefault("name", name)
    payload.setdefault("url_pattern", url_pattern)
    payload.setdefault("page_kind", page_kind)
    return GeneratedParser.model_validate(
        normalize_generated_payload(
            payload,
            known_checks=known_checks_for_domain(domain),
            default_required_fields=domain.default_required_fields,
        )
    )
