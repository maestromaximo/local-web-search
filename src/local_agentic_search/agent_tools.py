from __future__ import annotations

from typing import Any

from local_agentic_search.service import LocalSearchService


def build_agent_tools(service: LocalSearchService | None = None) -> tuple[Any, Any]:
    """Build OpenAI Agents SDK tools named web_search and web_fetch."""
    try:
        from agents import function_tool
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI Agents SDK is not installed. Install with "
            "`pip install local-agentic-search[agents]`."
        ) from exc

    search_service = service or LocalSearchService.from_env()

    @function_tool
    async def web_search(
        query: str,
        max_results: int = 5,
        page: int = 1,
        language: str | None = None,
        categories: str | None = None,
        engines: str | None = None,
        time_range: str | None = None,
        safesearch: int = 0,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Search the web and return compact snippets plus result_ids for web_fetch."""
        response = await search_service.search(
            query,
            max_results=max_results,
            page=page,
            language=language,
            categories=categories,
            engines=engines,
            time_range=time_range,
            safesearch=safesearch,
            refresh=refresh,
        )
        return response.model_dump()

    @function_tool
    async def web_fetch(
        result_id: str | None = None,
        url: str | None = None,
        start: int = 0,
        max_chars: int | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Fetch full page text for a web_search result_id, optionally as a bounded slice."""
        response = await search_service.fetch(
            result_id=result_id,
            url=url,
            start=start,
            max_chars=max_chars,
            refresh=refresh,
        )
        return response.model_dump()

    return web_search, web_fetch
