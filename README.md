# self-healing-scraper

[![PyPI](https://img.shields.io/pypi/v/self-healing-scraper.svg)](https://pypi.org/project/self-healing-scraper/)
[![CI](https://github.com/SollalF/self-healing-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/SollalF/self-healing-scraper/actions/workflows/ci.yml)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)

Generic self-healing declarative web scraper. Pass a URL and a domain config; the engine looks up a stored parser by URL regex, creates one with AI if missing, executes CSS extractors, validates items, and repairs the parser when checks fail.

Persistence is **not** included — inject a [`ParserStore`](src/self_healing_scraper/store.py) implementation (SQL, memory, etc.). Stores also decide when a
previously scraped page can be served from storage instead of re-scraped; see
[Reusing stored results](#reusing-stored-results).

## Install

```bash
# From PyPI (after first publish)
uv add self-healing-scraper
# or: pip install self-healing-scraper

# From GitHub (pin a tag)
uv add "self-healing-scraper @ git+https://github.com/SollalF/self-healing-scraper@v0.1.0"

# Local path (development)
uv add --editable ../self-healing-scraper

# Browser deps used by Crawl4AI
uv run playwright install chromium
# or: uv run crawl4ai-setup
```

## Quick example

```python
import asyncio
from self_healing_scraper import scrape_url, ScrapeDomain, DomainPrompts
from self_healing_scraper.testing import InMemoryParserStore

domain = ScrapeDomain(
    prompts=DomainPrompts(
        create_system="...",  # your domain prompts
        create_user_template="...",
        repair_system="...",
        repair_user_template="...",
    ),
    default_required_fields=["title", "url"],
)


async def main() -> None:
    store = InMemoryParserStore()
    result = await scrape_url(
        "https://example.com/list",
        store=store,
        domain=domain,
    )
    print(result.items)


asyncio.run(main())
```

## Reusing stored results

Article pages are usually immutable, so re-scraping one wastes a fetch and an
LLM budget. Before fetching, the engine asks the store whether it already has a
usable run for the URL:

- Only page kinds listed in `settings.cached_page_kinds` are eligible — by
  default just `article`, since listings gain new items constantly.
- The store decides whether a stored run is still good. `find_cached_run`
  returning a [`CachedRun`](src/self_healing_scraper/models.py) skips the fetch,
  the parser execution, and the validation loop entirely; returning `None`
  scrapes as normal. Age limits and invalidation on parser upgrades are the
  store's policy, not the engine's.
- A reused result comes back with `from_cache=True` and `attempts=0`, and no new
  run is recorded.
- Pass `force_refresh=True` to `scrape_url` / `scrape_urls` to always hit the
  network.

```python
result = await scrape_url(url, store=store, domain=domain)
if result.from_cache:
    print("served from a stored run")

fresh = await scrape_url(url, store=store, domain=domain, force_refresh=True)
```

## Configuration

The engine does **not** load `.env` or process environment variables. Pass a
[`Settings`](src/self_healing_scraper/settings.py) instance (or rely on defaults):

```python
from self_healing_scraper.settings import Settings

settings = Settings(
    llm_api_key="...",
    llm_model="gpt-4o",
    max_repair_attempts=3,
)
```

| Field                 | Default  | Purpose                           |
| --------------------- | -------- | --------------------------------- |
| `llm_api_key`         | `""`     | Required to create/repair parsers |
| `llm_model`           | `gpt-4o` | Model for parser agent            |
| `llm_base_url`        | `""`     | OpenAI-compatible API base        |
| `max_repair_attempts` | `3`      | Self-heal loop limit              |
| `crawl_timeout_ms`    | `30000`  | Page load timeout                 |
| `page_sample_chars`   | `12000`  | HTML sample size sent to the AI   |
| `cached_page_kinds`   | `{"article"}` | Page kinds allowed to reuse a stored run |

Applications (e.g. news scrapers) typically load these from their own `.env` /
settings layer and pass them into `scrape_url`.

## Layout

```
src/self_healing_scraper/
  scrape.py       # heal loop
  store.py        # ParserStore Protocol + helpers
  testing.py      # InMemoryParserStore for tests / smoke scripts
  domain.py       # ScrapeDomain / DomainPrompts
  fetch/          # Crawl4AI wrapper
  runtime/        # executor + core validators
  agent/          # create / repair LLM
tests/
```

## Develop

```bash
uv sync
uv run pre-commit install   # pre-commit + commit-msg (conventional commits)
uv run pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit message conventions and the release flow.

## Releases & PyPI

- Commits on `main` use [Conventional Commits](https://www.conventionalcommits.org/)
- [release-please](https://github.com/googleapis/release-please) opens a Release PR; merging it tags a GitHub release
- The same workflow publishes to PyPI via [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC, no API token)

### One-time PyPI setup (pending publisher)

Until this is done, the publish job will fail authentication:

1. Sign in at https://pypi.org/manage/account/publishing/
2. Under **Add a new pending publisher**, set:
   - **PyPI Project Name:** `self-healing-scraper`
   - **Owner:** `SollalF`
   - **Repository name:** `self-healing-scraper`
   - **Workflow name:** `release-please.yml`
   - **Environment name:** `pypi`
3. Click **Add**
4. Publish `v0.1.0` once via **Actions → release-please → Run workflow** (manual dispatch), or merge the next Release PR
