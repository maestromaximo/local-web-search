from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from local_agentic_search.docker import ensure_search_container_running, warn_docker_not_managed
from local_agentic_search.models import FetchResponse, SearchResponse
from local_agentic_search.service import LocalSearchService


def _should_show_search_warnings(response: SearchResponse) -> bool:
    if not response.warnings:
        return False
    if response.count == 0:
        return True
    total_engines = {
        engine
        for result in response.results
        for engine in result.engines
        if engine
    }
    failed_engines = {
        warning.split(":", 1)[0].strip()
        for warning in response.warnings
        if warning.split(":", 1)[0].strip()
    }
    if not total_engines:
        return len(failed_engines) >= 3
    return len(failed_engines) >= max(2, len(total_engines))


def _compact_search_payload(response: SearchResponse) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": response.query,
        "search_id": response.search_id,
        "count": response.count,
        "results": [
            {
                "result_id": result.result_id,
                "position": result.position,
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
                "site_links": [link.model_dump() for link in result.site_links],
                "full_text_available": result.full_text_available,
                "full_text_command": result.full_text_command.model_dump()
                if result.full_text_command
                else None,
                "full_text_command_text": result.full_text_command_text,
            }
            for result in response.results
        ],
    }
    if response.answers:
        payload["answers"] = response.answers
    if response.suggestions:
        payload["suggestions"] = response.suggestions
    if _should_show_search_warnings(response):
        payload["warnings"] = response.warnings
    if response.cache_hit:
        payload["cache_hit"] = True
    return payload


def _compact_fetch_payload(response: FetchResponse) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": response.success,
        "result_id": response.result_id,
        "url": response.url,
        "title": response.title,
        "content": response.content,
        "start": response.start,
        "end": response.end,
        "total_chars": response.total_chars,
        "has_more": response.has_more,
        "next_fetch_command": response.next_fetch_command.model_dump()
        if response.next_fetch_command
        else None,
        "next_fetch_command_text": response.next_fetch_command_text,
    }
    if response.error:
        payload["error"] = response.error
    if response.cache_hit:
        payload["cache_hit"] = True
    return payload


def build_agent_tools(
    service: LocalSearchService | None = None,
    *,
    build_container_if_missing: bool = False,
    suppress_docker_warning: bool = False,
) -> tuple[Any, Any]:
    """Build OpenAI Agents SDK tools named web_search and web_fetch."""
    try:
        from agents import function_tool
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI Agents SDK is not installed. Install with "
            "`pip install local-agentic-search[agents]`."
        ) from exc

    if build_container_if_missing:
        ensure_search_container_running()
    elif service is None:
        warn_docker_not_managed(suppress=suppress_docker_warning)

    search_service = service or LocalSearchService.from_env()

    @function_tool
    async def web_search(
        query: Annotated[
            str,
            Field(description="Search query to send to SearXNG."),
        ],
        max_results: Annotated[
            int,
            Field(
                ge=1,
                le=20,
                description="Maximum number of search results to return; use 5 by default.",
            ),
        ] = 5,
        page: Annotated[
            int,
            Field(ge=1, description="SearXNG results page number; use 1 for the first page."),
        ] = 1,
        language: Annotated[
            str | None,
            Field(description="Optional SearXNG language code such as 'en'; use None if unsure."),
        ] = None,
        categories: Annotated[
            str | None,
            Field(
                description=(
                    "Optional comma-separated SearXNG categories such as 'general' or 'news'; "
                    "use None for the default."
                ),
            ),
        ] = None,
        engines: Annotated[
            str | None,
            Field(
                description=(
                    "Optional comma-separated SearXNG engine names; use None unless a specific "
                    "engine is required."
                ),
            ),
        ] = None,
        time_range: Annotated[
            Literal["day", "month", "year"] | None,
            Field(
                description="Optional recency filter; valid values are day, month, year, or None."
            ),
        ] = None,
        safesearch: Annotated[
            Literal[0, 1, 2],
            Field(description="SearXNG safesearch level: 0 off, 1 moderate, 2 strict."),
        ] = 0,
        refresh: Annotated[
            bool,
            Field(description="Bypass cached search results when true."),
        ] = False,
    ) -> dict[str, Any]:
        """Search the web and return compact snippets plus result_ids for web_fetch.

        Use web_search first for discovery. Call web_fetch only when a result's snippet is
        insufficient and full page text is needed.
        """
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
        return _compact_search_payload(response)

    @function_tool
    async def web_fetch(
        result_id: Annotated[
            str | None,
            Field(
                description=(
                    "Stable result_id returned by web_search; prefer this over url when available."
                ),
            ),
        ] = None,
        url: Annotated[
            str | None,
            Field(description="Direct http(s) URL to fetch only when no result_id is available."),
        ] = None,
        start: Annotated[
            int,
            Field(ge=0, description="Character offset into the fetched page text; start at 0."),
        ] = 0,
        max_chars: Annotated[
            int | None,
            Field(
                ge=1,
                le=20_000,
                description="Maximum characters to return; use None for the configured default.",
            ),
        ] = None,
        refresh: Annotated[
            bool,
            Field(description="Bypass cached page text and crawl again when true."),
        ] = False,
    ) -> dict[str, Any]:
        """Fetch full page text for a web_search result_id or URL as a bounded slice.

        Use start and max_chars to request only the needed portion. If has_more is true, use
        next_fetch_command to continue reading.
        """
        response = await search_service.fetch(
            result_id=result_id,
            url=url,
            start=start,
            max_chars=max_chars,
            refresh=refresh,
        )
        return _compact_fetch_payload(response)

    return web_search, web_fetch
