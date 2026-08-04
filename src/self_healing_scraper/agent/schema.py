"""JSON Schema for LLM structured output (OpenAI + Kimi MFJS-compatible)."""

from __future__ import annotations

from typing import Any


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [schema, {"type": "null"}]}


def _field_extractor_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector relative to the item or page root",
            },
            "attr": {
                "type": "string",
                "description": "DOM attribute name, or 'text' for text content",
            },
            "many": {
                "type": "boolean",
                "description": "If true, collect all matches as a list",
            },
        },
        "required": ["selector", "attr", "many"],
        "additionalProperties": False,
    }


def _validation_check_schema(known_checks: frozenset[str] | None) -> dict[str, Any]:
    type_schema: dict[str, Any] = {
        "type": "string",
        "description": "Validation check type",
    }
    if known_checks:
        type_schema = {
            "type": "string",
            "enum": sorted(known_checks),
            "description": "Validation check type",
        }
    return {
        "type": "object",
        "properties": {
            "type": type_schema,
            "value": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "number"},
                    {"type": "boolean"},
                    {"type": "null"},
                ],
                "description": "Primary scalar parameter for the check",
            },
            "field": _nullable({"type": "string"}),
            "fields": _nullable(
                {"type": "array", "items": {"type": "string"}},
            ),
            "values": _nullable(
                {"type": "array", "items": {"type": "string"}},
            ),
            "pattern": _nullable({"type": "string"}),
            "message": _nullable({"type": "string"}),
        },
        "required": [
            "type",
            "value",
            "field",
            "fields",
            "values",
            "pattern",
            "message",
        ],
        "additionalProperties": False,
    }


def generated_parser_json_schema(
    known_checks: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Return a flat, MFJS-friendly schema for GeneratedParser.

    Avoids ``$ref`` / ``title`` and uses ``anyOf`` for nullables so Kimi
    strict structured output accepts the schema.
    """
    return {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Short human-readable parser name",
            },
            "url_pattern": {
                "type": "string",
                "description": "Regex matching URLs this parser applies to",
            },
            "page_kind": {
                "type": "string",
                "enum": ["listing", "article"],
            },
            "definition": {
                "type": "object",
                "properties": {
                    "js_enabled": {"type": "boolean"},
                    "wait_for": _nullable(
                        {
                            "type": "string",
                            "description": "Optional CSS selector to wait for",
                        }
                    ),
                    "item_selector": _nullable(
                        {
                            "type": "string",
                            "description": "CSS selector for each listing item",
                        }
                    ),
                    "fields": {
                        "type": "object",
                        "additionalProperties": _field_extractor_schema(),
                        "description": "Map of field name to extractor",
                    },
                    "source_name": _nullable({"type": "string"}),
                },
                "required": [
                    "js_enabled",
                    "wait_for",
                    "item_selector",
                    "fields",
                    "source_name",
                ],
                "additionalProperties": False,
            },
            "validations": {
                "type": "object",
                "properties": {
                    "checks": {
                        "type": "array",
                        "items": _validation_check_schema(known_checks),
                    }
                },
                "required": ["checks"],
                "additionalProperties": False,
            },
        },
        "required": [
            "name",
            "url_pattern",
            "page_kind",
            "definition",
            "validations",
        ],
        "additionalProperties": False,
    }
