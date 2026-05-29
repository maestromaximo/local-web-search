from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _int_from_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _searxng_base_url_from_env() -> str:
    explicit_base_url = os.getenv("SEARXNG_BASE_URL")
    if explicit_base_url:
        return explicit_base_url.rstrip("/")

    host = os.getenv("LOCAL_WEB_SEARCH_SEARXNG_HOST", "127.0.0.1")
    port = _int_from_env("LOCAL_WEB_SEARCH_SEARXNG_PORT", 8888)
    return f"http://{host}:{port}"


@dataclass(frozen=True)
class LocalSearchConfig:
    searxng_base_url: str = "http://127.0.0.1:8888"
    cache_path: Path = Path(".cache/local_agentic_search.sqlite3")
    results_ttl_seconds: int = 86_400
    pages_ttl_seconds: int = 604_800
    default_fetch_chars: int = 4_000
    max_fetch_chars: int = 20_000
    request_timeout_seconds: float = 30.0
    crawl_timeout_ms: int = 45_000

    @classmethod
    def from_env(cls) -> LocalSearchConfig:
        return cls(
            searxng_base_url=_searxng_base_url_from_env(),
            cache_path=Path(
                os.getenv("LOCAL_WEB_SEARCH_CACHE", str(cls.cache_path))
            ),
            results_ttl_seconds=_int_from_env(
                "LOCAL_WEB_SEARCH_RESULTS_TTL_SECONDS", cls.results_ttl_seconds
            ),
            pages_ttl_seconds=_int_from_env(
                "LOCAL_WEB_SEARCH_PAGES_TTL_SECONDS", cls.pages_ttl_seconds
            ),
            default_fetch_chars=_int_from_env(
                "LOCAL_WEB_SEARCH_FETCH_CHARS", cls.default_fetch_chars
            ),
            max_fetch_chars=_int_from_env(
                "LOCAL_WEB_SEARCH_MAX_FETCH_CHARS", cls.max_fetch_chars
            ),
            crawl_timeout_ms=_int_from_env(
                "LOCAL_WEB_SEARCH_CRAWL_TIMEOUT_MS", cls.crawl_timeout_ms
            ),
        )
