from self_healing_scraper.agent.normalize import normalize_generated_payload
from self_healing_scraper.scrape import normalize_url


def test_normalize_url_lowercases_host_and_strips_fragment() -> None:
    assert (
        normalize_url("https://TechCrunch.COM/latest/#top")
        == "https://techcrunch.com/latest/"
    )


def test_normalize_generated_payload_drops_null_extractors() -> None:
    payload = {
        "name": "x",
        "url_pattern": ".*",
        "page_kind": "listing",
        "definition": {
            "fields": {
                "title": {"selector": "h1", "attr": "text"},
                "bad": None,
                "empty": {},
            }
        },
        "validations": {"checks": [{"type": "unknown_check"}]},
    }
    cleaned = normalize_generated_payload(payload)
    assert "title" in cleaned["definition"]["fields"]
    assert "bad" not in cleaned["definition"]["fields"]
    assert "empty" not in cleaned["definition"]["fields"]
    types = {c["type"] for c in cleaned["validations"]["checks"]}
    assert "min_count" in types
    assert "required_fields" in types
    assert "unknown_check" not in types
