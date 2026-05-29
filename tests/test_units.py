from __future__ import annotations

import asyncio
from pathlib import Path

from local_agentic_search.cache import SQLiteSearchCache
from local_agentic_search.config import LocalSearchConfig
from local_agentic_search.crawler import CrawledPage
from local_agentic_search.service import LocalSearchService
from local_agentic_search.tool_schemas import responses_tool_schemas


class FakeSearxngClient:
    async def health(self) -> bool:
        return True

    async def search(self, query: str, **_: object) -> dict[str, object]:
        return {
            "query": query,
            "results": [
                {
                    "title": "Example Domain",
                    "url": "https://example.com/",
                    "content": "This domain is for use in illustrative examples.",
                    "engine": "fake",
                    "score": 1.0,
                }
            ],
            "suggestions": [],
            "answers": [],
        }


class FakeFetcher:
    async def fetch(self, url: str) -> CrawledPage:
        return CrawledPage(
            url=url,
            title="Example Domain",
            content="Example Domain\n\nThis domain is for use in illustrative examples.",
            metadata={"status_code": 200},
        )


def _service(tmp_path: Path) -> LocalSearchService:
    config = LocalSearchConfig(
        searxng_base_url="http://127.0.0.1:8888",
        cache_path=tmp_path / "cache.sqlite3",
    )
    return LocalSearchService(
        config,
        cache=SQLiteSearchCache(config.cache_path),
        searxng_client=FakeSearxngClient(),  # type: ignore[arg-type]
        fetcher=FakeFetcher(),  # type: ignore[arg-type]
    )


def test_search_returns_fetch_command(tmp_path: Path) -> None:
    service = _service(tmp_path)
    response = asyncio.run(service.search("example", max_results=1))

    assert response.count == 1
    result = response.results[0]
    assert result.result_id.startswith("res_")
    assert result.full_text_available is True
    assert result.full_text_command is not None
    assert result.full_text_command.arguments["result_id"] == result.result_id
    assert "web_fetch" in (result.full_text_command_text or "")


def test_fetch_returns_bounded_page_slice(tmp_path: Path) -> None:
    service = _service(tmp_path)
    search = asyncio.run(service.search("example", max_results=1))
    result_id = search.results[0].result_id

    fetched = asyncio.run(service.fetch(result_id=result_id, max_chars=20))

    assert fetched.success is True
    assert fetched.result_id == result_id
    assert fetched.content == "Example Domain\n\nThis"
    assert fetched.has_more is True
    assert fetched.next_fetch_command is not None


def test_responses_tool_schemas_are_named_for_web_tools() -> None:
    schemas = responses_tool_schemas()
    assert [schema["name"] for schema in schemas] == ["web_search", "web_fetch"]
    assert all(schema["type"] == "function" for schema in schemas)
