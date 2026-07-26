"""Domain plug-in surface for prompts and extra validators."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from self_healing_scraper.models import (
    PageContent,
    ValidationCheck,
    ValidationFailure,
)

CheckFn = Callable[
    [ValidationCheck, list[dict[str, Any]], PageContent | None],
    ValidationFailure | None,
]


@dataclass(frozen=True)
class DomainPrompts:
    create_system: str
    create_user_template: str
    repair_system: str
    repair_user_template: str


@dataclass(frozen=True)
class ScrapeDomain:
    """Specialization knobs for a scraping product (news, jobs, etc.)."""

    prompts: DomainPrompts
    default_required_fields: list[str] = field(default_factory=lambda: ["title", "url"])
    known_checks: frozenset[str] = field(default_factory=frozenset)
    extra_validators: dict[str, CheckFn] = field(default_factory=dict)
    item_builder: Callable[[dict[str, Any]], Any] | None = None
