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

| Type | Effect on next release |
|------|------------------------|
| `fix:` | patch (`0.1.0` → `0.1.1`) |
| `feat:` | minor (`0.1.0` → `0.2.0`) while `< 1.0.0` with current config |
| `feat!:` / `BREAKING CHANGE:` | major |
| `docs:`, `ci:`, `chore:`, `refactor:`, `test:` | no version bump alone |

Examples:

```
feat: add timeout option to fetch_page
fix: skip invalid regex in best_parser_match
ci: tighten release workflow permissions
```

## Releases

[release-please](https://github.com/googleapis/release-please) opens a Release PR on `main` when releasable commits land. Merging that PR tags a GitHub release and publishes to PyPI via Trusted Publishing.
