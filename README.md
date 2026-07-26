# self-healing-scraper

[![PyPI](https://img.shields.io/pypi/v/self-healing-scraper.svg)](https://pypi.org/project/self-healing-scraper/)
[![CI](https://github.com/SollalF/self-healing-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/SollalF/self-healing-scraper/actions/workflows/ci.yml)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)

Generic self-healing declarative web scraper. Pass a URL and a domain config; the engine looks up a stored parser by URL regex, creates one with AI if missing, executes CSS extractors, validates items, and repairs the parser when checks fail.

Persistence is **not** included — inject a [`ParserStore`](src/self_healing_scraper/store.py) implementation (SQL, memory, etc.).

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
from self_healing_scraper.store import InMemoryParserStore

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

## Configuration

| Env | Default | Purpose |
|-----|---------|---------|
| `LLM_API_KEY` | — | Required to create/repair parsers |
| `LLM_MODEL` | `gpt-4o` | Model for parser agent |
| `LLM_BASE_URL` | — | OpenAI-compatible API base |
| `MAX_REPAIR_ATTEMPTS` | `3` | Self-heal loop limit |
| `CRAWL_TIMEOUT_MS` | `30000` | Page load timeout |
| `PAGE_SAMPLE_CHARS` | `12000` | HTML sample size sent to the AI |

## Layout

```
src/self_healing_scraper/
  scrape.py       # heal loop
  store.py        # ParserStore Protocol + helpers
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
