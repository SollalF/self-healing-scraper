# Contributing

## Setup

```bash
uv sync
uv run pre-commit install
```

This installs both `pre-commit` and `commit-msg` hooks.

## Conventional Commits

Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]
```

Common types:

While the package is below `1.0.0`, `bump-minor-pre-major` keeps breaking changes
off a `1.0.0` bump:

| Type | Effect on next release |
|------|------------------------|
| `fix:` | patch (`0.2.0` → `0.2.1`) |
| `feat:` | minor (`0.2.0` → `0.3.0`) |
| `feat!:` / `BREAKING CHANGE:` | minor while `< 1.0.0`; major once `>= 1.0.0` |
| `docs:`, `ci:`, `chore:`, `refactor:`, `test:` | no version bump alone |

Examples:

```
feat: add timeout option to fetch_page
fix: skip invalid regex in best_parser_match
ci: tighten release workflow permissions
```

## Releases

Land work through pull requests and squash-merge them, so the PR title becomes the single conventional commit release-please parses. Do not push directly to `main`.

[release-please](https://github.com/googleapis/release-please) opens a Release PR on `main` when releasable commits land. Merging that PR tags a GitHub release and publishes to PyPI via Trusted Publishing.
