# Contributing

Thanks for helping improve Local Web Search. This project is intended to stay
small, reliable, and easy to embed in agent workflows.

## Development Setup

```powershell
docker compose up -d searxng
uv venv
.\.venv\Scripts\python -m pip install -e ".[server,agents,dev]"
.\.venv\Scripts\crawl4ai-setup
.\.venv\Scripts\python -m pytest
```

If you do not use `uv`, a regular Python virtual environment works too:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[server,agents,dev]"
```

## Pull Requests

- Keep changes focused and describe user-visible behavior in the PR.
- Add or update tests for behavior changes.
- Run `python -m pytest` and `python -m ruff check .` before requesting review.
- Do not commit local secrets, browser profiles, caches, build output, or
  downloaded page content.

## Release Process

PyPI versions are immutable. Before merging a release change to `main`, update
`version` in `pyproject.toml`. The GitHub Actions publish workflow runs on
every push to `main` and publishes only when that version does not already
exist on PyPI.

Maintainers may push directly to `main` for urgent fixes. Normal contributions
should use pull requests.
