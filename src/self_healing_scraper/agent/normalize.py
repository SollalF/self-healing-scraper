"""Normalize LLM parser payloads before Pydantic validation."""

from __future__ import annotations

from typing import Any

from self_healing_scraper.runtime.validators import CORE_KNOWN_CHECKS


def normalize_generated_payload(
    payload: dict[str, Any],
    *,
    known_checks: frozenset[str] | None = None,
    default_required_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Drop null/invalid field extractors and coerce loose shapes from the LLM."""
    allowed = known_checks if known_checks is not None else CORE_KNOWN_CHECKS
    required = default_required_fields or ["title", "url"]
    data = dict(payload)
    definition = data.get("definition")
    if isinstance(definition, dict):
        fields = definition.get("fields")
        if isinstance(fields, dict):
            cleaned: dict[str, Any] = {}
            for name, extractor in fields.items():
                if extractor is None:
                    continue
                if isinstance(extractor, dict) and extractor.get("selector"):
                    cleaned[name] = {
                        "selector": extractor["selector"],
                        "attr": extractor.get("attr") or "text",
                        "many": bool(extractor.get("many", False)),
                    }
            definition = {**definition, "fields": cleaned}
            data["definition"] = definition

    validations = data.get("validations")
    if isinstance(validations, dict):
        checks = validations.get("checks")
        if isinstance(checks, list):
            kept = [
                c
                for c in checks
                if isinstance(c, dict) and c.get("type") in allowed
            ]
            # Ensure a minimal useful suite remains.
            types = {c["type"] for c in kept}
            if "min_count" not in types:
                kept.insert(0, {"type": "min_count", "value": 1})
            if "required_fields" not in types:
                kept.append(
                    {"type": "required_fields", "fields": list(required)}
                )
            data["validations"] = {**validations, "checks": kept}
    elif validations is None:
        data["validations"] = {
            "checks": [
                {"type": "min_count", "value": 1},
                {"type": "required_fields", "fields": list(required)},
            ]
        }

    return data
