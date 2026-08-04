from self_healing_scraper.agent.create_parser import ensure_minimal_validations
from self_healing_scraper.agent.schema import generated_parser_json_schema
from self_healing_scraper.models import (
    GeneratedParser,
    ParserDefinition,
    ValidationCheck,
    ValidationSuite,
)
from self_healing_scraper.scrape import normalize_url


def test_normalize_url_lowercases_host_and_strips_fragment() -> None:
    assert (
        normalize_url("https://TechCrunch.COM/latest/#top")
        == "https://techcrunch.com/latest/"
    )


def test_ensure_minimal_validations_adds_defaults() -> None:
    parser = GeneratedParser(
        name="x",
        url_pattern=".*",
        page_kind="listing",
        definition=ParserDefinition(
            fields={"title": {"selector": "h1", "attr": "text", "many": False}},
        ),
        validations=ValidationSuite(checks=[]),
    )
    filled = ensure_minimal_validations(parser, required_fields=["title", "url"])
    types = {c.type for c in filled.validations.checks}
    assert types == {"min_count", "required_fields"}


def test_ensure_minimal_validations_preserves_existing() -> None:
    parser = GeneratedParser(
        name="x",
        url_pattern=".*",
        page_kind="listing",
        definition=ParserDefinition(),
        validations=ValidationSuite(
            checks=[
                ValidationCheck(type="min_count", value=3),
                ValidationCheck(type="required_fields", fields=["title"]),
            ]
        ),
    )
    filled = ensure_minimal_validations(parser, required_fields=["title", "url"])
    assert filled is parser
    assert filled.validations.checks[0].value == 3
    assert filled.validations.checks[1].fields == ["title"]


def test_generated_parser_schema_enums_known_checks() -> None:
    schema = generated_parser_json_schema(frozenset({"min_count", "required_fields"}))
    check_type = schema["properties"]["validations"]["properties"]["checks"]["items"][
        "properties"
    ]["type"]
    assert check_type["enum"] == ["min_count", "required_fields"]
    assert schema["additionalProperties"] is False
