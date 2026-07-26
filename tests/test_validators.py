from self_healing_scraper.models import (
    PageContent,
    ValidationCheck,
    ValidationSuite,
)
from self_healing_scraper.runtime.validators import run_validations


def test_validations_pass(
    sample_items: list[dict], listing_validations: ValidationSuite
) -> None:
    page = PageContent(url="https://techcrunch.com/latest/", html="<html></html>")
    result = run_validations(sample_items, listing_validations, page)
    assert result.passed


def test_min_count_fails(sample_items: list[dict]) -> None:
    suite = ValidationSuite(checks=[ValidationCheck(type="min_count", value=10)])
    result = run_validations(sample_items, suite, None)
    assert not result.passed
    assert result.failures[0].check_type == "min_count"


def test_url_same_host_fails(sample_items: list[dict]) -> None:
    bad = list(sample_items)
    bad[0] = {**bad[0], "url": "https://evil.example/x"}
    suite = ValidationSuite(checks=[ValidationCheck(type="url_same_host")])
    page = PageContent(url="https://techcrunch.com/latest/", html="")
    result = run_validations(bad, suite, page)
    assert not result.passed


def test_not_equals_banned_title(sample_items: list[dict]) -> None:
    items = list(sample_items)
    items[0] = {**items[0], "title": "Home"}
    suite = ValidationSuite(
        checks=[
            ValidationCheck(type="not_equals", field="title", values=["Home", "Latest"])
        ]
    )
    result = run_validations(items, suite, None)
    assert not result.passed
