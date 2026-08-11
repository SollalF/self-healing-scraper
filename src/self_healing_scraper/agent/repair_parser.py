"""AI-assisted parser repair."""

from __future__ import annotations

import json

from self_healing_scraper.agent.create_parser import (
    ensure_minimal_validations,
    known_checks_for_domain,
)
from self_healing_scraper.agent.llm import complete_json
from self_healing_scraper.agent.page_sample import sample_page_for_llm
from self_healing_scraper.agent.schema import generated_parser_json_schema
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
    known_checks = known_checks_for_domain(domain)
    samples = sample_page_for_llm(page, cfg, definition=definition)
    payload = await complete_json(
        system=domain.prompts.repair_system,
        user=domain.prompts.repair_user_template.format(
            url=page.url,
            current_parser=json.dumps(current, separators=(",", ":")),
            failures=validation_result.model_dump_json(),
            html_sample=samples.html_sample,
            markdown_sample=samples.markdown_sample,
        ),
        settings=cfg,
        json_schema=generated_parser_json_schema(known_checks),
        schema_name="generated_parser",
    )
    return ensure_minimal_validations(
        GeneratedParser.model_validate(payload),
        required_fields=domain.default_required_fields,
    )
