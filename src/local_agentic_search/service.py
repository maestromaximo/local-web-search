from __future__ import annotations

from typing import Any

from local_agentic_search.cache import SQLiteSearchCache
from local_agentic_search.config import LocalSearchConfig
from local_agentic_search.crawler import Crawl4AIFetcher
from local_agentic_search.models import FetchResponse, SearchResponse, SearchResult, SiteLink
from local_agentic_search.searxng import SearxngClient
from local_agentic_search.utils import (
    clamp_slice,
    compact_text,
    is_fetchable_url,
    make_fetch_command,
    make_fetch_command_text,
    stable_hash,
    stable_json,
)

_TIME_RANGE_ALIASES = {
    "": None,
    "none": None,
    "null": None,
    "any": None,
    "all": None,
    "d": "day",
    "day": "day",
    "daily": "day",
    "m": "month",
    "mo": "month",
    "month": "month",
    "monthly": "month",
    "y": "year",
    "yr": "year",
    "year": "year",
    "yearly": "year",
}


class LocalSearchService:
    def __init__(
        self,
        config: LocalSearchConfig | None = None,
        *,
        cache: SQLiteSearchCache | None = None,
        searxng_client: SearxngClient | None = None,
        fetcher: Crawl4AIFetcher | None = None,
    ) -> None:
        self.config = config or LocalSearchConfig.from_env()
        self.cache = cache or SQLiteSearchCache(self.config.cache_path)
        self.searxng = searxng_client or SearxngClient(
            self.config.searxng_base_url,
            timeout_seconds=self.config.request_timeout_seconds,
        )
        self.fetcher = fetcher or Crawl4AIFetcher(timeout_ms=self.config.crawl_timeout_ms)

    @classmethod
    def from_env(cls) -> LocalSearchService:
        return cls(LocalSearchConfig.from_env())

    async def health(self) -> dict[str, Any]:
        searxng_ok = await self.searxng.health()
        return {
            "ok": searxng_ok,
            "searxng_base_url": self.config.searxng_base_url,
            "cache_path": str(self.config.cache_path),
        }

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        page: int = 1,
        language: str | None = None,
        categories: str | None = None,
        engines: str | None = None,
        time_range: str | None = None,
        safesearch: int = 0,
        refresh: bool = False,
    ) -> SearchResponse:
        max_results = max(1, min(max_results, 20))
        page = max(1, page)
        time_range = self._normalize_time_range(time_range)
        params = {
            "query": query,
            "max_results": max_results,
            "page": page,
            "language": language,
            "categories": categories,
            "engines": engines,
            "time_range": time_range,
            "safesearch": safesearch,
        }
        search_id = f"search_{stable_hash(stable_json(params))}"

        if not refresh:
            cached = self.cache.load_search(search_id, self.config.results_ttl_seconds)
            if cached:
                return cached

        raw = await self.searxng.search(
            query,
            page=page,
            language=language,
            categories=categories,
            engines=engines,
            time_range=time_range,
            safesearch=safesearch,
        )
        results = self._normalize_results(search_id, raw.get("results", []), max_results)
        response = SearchResponse(
            query=query,
            search_id=search_id,
            count=len(results),
            results=results,
            suggestions=[compact_text(item) for item in raw.get("suggestions", []) if item],
            answers=[compact_text(item) for item in raw.get("answers", []) if item],
            cache_hit=False,
            warnings=[
                self._format_engine_warning(item)
                for item in raw.get("unresponsive_engines", [])
                if item
            ],
        )
        self.cache.save_search(response, params)
        return response

    async def fetch(
        self,
        *,
        result_id: str | None = None,
        url: str | None = None,
        start: int = 0,
        max_chars: int | None = None,
        refresh: bool = False,
    ) -> FetchResponse:
        if result_id:
            cached_result = self.cache.load_result(result_id)
            if not cached_result:
                return FetchResponse(
                    success=False,
                    result_id=result_id,
                    url=url or "",
                    error=(
                        "Unknown result_id. Call web_search first, then use the result_id from "
                        "that response."
                    ),
                )
            url = url or cached_result["url"]
            title = cached_result.get("title")
        else:
            title = None

        if not url:
            return FetchResponse(
                success=False,
                result_id=result_id,
                url="",
                error="Provide either result_id or url.",
            )

        if not is_fetchable_url(url):
            return FetchResponse(
                success=False,
                result_id=result_id,
                url=url,
                title=title,
                error="Only http and https URLs can be fetched.",
            )

        max_chars = self._bounded_fetch_chars(max_chars)

        if not refresh:
            cached_page = self.cache.load_page(url, self.config.pages_ttl_seconds)
            if cached_page and cached_page.success:
                return self._slice_fetch_response(
                    cached_page,
                    result_id=result_id or cached_page.result_id,
                    start=start,
                    max_chars=max_chars,
                    cache_hit=True,
                )

        try:
            crawled = await self.fetcher.fetch(url)
            base_response = FetchResponse(
                success=True,
                result_id=result_id,
                url=crawled.url or url,
                title=crawled.title or title,
                content=crawled.content,
                start=0,
                end=len(crawled.content),
                total_chars=len(crawled.content),
                has_more=False,
                cache_hit=False,
                metadata=crawled.metadata,
            )
        except Exception as exc:
            base_response = FetchResponse(
                success=False,
                result_id=result_id,
                url=url,
                title=title,
                error=str(exc),
            )

        self.cache.save_page(base_response)
        if not base_response.success:
            return base_response
        return self._slice_fetch_response(
            base_response,
            result_id=result_id,
            start=start,
            max_chars=max_chars,
            cache_hit=False,
        )

    def _normalize_results(
        self,
        search_id: str,
        raw_results: list[dict[str, Any]],
        max_results: int,
    ) -> list[SearchResult]:
        normalized: list[SearchResult] = []
        for item in raw_results:
            url = compact_text(item.get("url"))
            if not url:
                continue
            position = len(normalized) + 1
            result_id = f"res_{stable_hash(f'{search_id}:{position}:{url}')}"
            title = compact_text(item.get("title")) or url
            snippet = compact_text(item.get("content") or item.get("snippet"))
            full_text_available = is_fetchable_url(url)
            command = (
                make_fetch_command(
                    result_id,
                    start=0,
                    max_chars=self.config.default_fetch_chars,
                )
                if full_text_available
                else None
            )
            command_text = (
                make_fetch_command_text(
                    result_id,
                    start=0,
                    max_chars=self.config.default_fetch_chars,
                )
                if full_text_available
                else None
            )
            normalized.append(
                SearchResult(
                    result_id=result_id,
                    search_id=search_id,
                    position=position,
                    title=title,
                    url=url,
                    snippet=snippet,
                    site_links=self._extract_site_links(item),
                    source=compact_text(item.get("engine")) or None,
                    engines=self._extract_engines(item),
                    score=self._extract_score(item),
                    full_text_available=full_text_available,
                    full_text_command=command,
                    full_text_command_text=command_text,
                    metadata=self._result_metadata(item),
                )
            )
            if len(normalized) >= max_results:
                break
        return normalized

    def _slice_fetch_response(
        self,
        response: FetchResponse,
        *,
        result_id: str | None,
        start: int,
        max_chars: int,
        cache_hit: bool,
    ) -> FetchResponse:
        content, safe_start, end, has_more = clamp_slice(response.content, start, max_chars)
        next_command = None
        next_command_text = None
        if has_more:
            next_command = make_fetch_command(
                result_id,
                start=end,
                max_chars=max_chars,
                url=response.url if not result_id else None,
            )
            next_command_text = make_fetch_command_text(
                result_id,
                start=end,
                max_chars=max_chars,
                url=response.url if not result_id else None,
            )
        return FetchResponse(
            success=True,
            result_id=result_id,
            url=response.url,
            title=response.title,
            content=content,
            start=safe_start,
            end=end,
            total_chars=len(response.content),
            has_more=has_more,
            next_fetch_command=next_command,
            next_fetch_command_text=next_command_text,
            cache_hit=cache_hit,
            metadata=response.metadata,
        )

    def _bounded_fetch_chars(self, max_chars: int | None) -> int:
        requested = max_chars or self.config.default_fetch_chars
        return max(1, min(requested, self.config.max_fetch_chars))

    @staticmethod
    def _normalize_time_range(time_range: str | None) -> str | None:
        if time_range is None:
            return None
        normalized = _TIME_RANGE_ALIASES.get(compact_text(time_range).lower())
        if normalized is not None or compact_text(time_range).lower() in _TIME_RANGE_ALIASES:
            return normalized
        return None

    @staticmethod
    def _format_engine_warning(item: Any) -> str:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            engine = compact_text(item[0])
            reason = compact_text(item[1])
            return f"{engine}: {reason}" if engine and reason else compact_text(item)
        if isinstance(item, dict):
            engine = compact_text(item.get("engine") or item.get("name"))
            reason = compact_text(item.get("error") or item.get("reason") or item.get("message"))
            return f"{engine}: {reason}" if engine and reason else compact_text(item)
        return compact_text(item)

    @staticmethod
    def _extract_site_links(item: dict[str, Any]) -> list[SiteLink]:
        raw_links = item.get("site_links") or item.get("sitelinks") or item.get("links") or []
        links: list[SiteLink] = []
        if isinstance(raw_links, list):
            for raw in raw_links:
                if not isinstance(raw, dict):
                    continue
                title = compact_text(raw.get("title") or raw.get("name"))
                url = compact_text(raw.get("url") or raw.get("href"))
                if title and url:
                    links.append(SiteLink(title=title, url=url))
        return links

    @staticmethod
    def _extract_engines(item: dict[str, Any]) -> list[str]:
        engines = item.get("engines")
        if isinstance(engines, list):
            return [compact_text(engine) for engine in engines if compact_text(engine)]
        engine = compact_text(item.get("engine"))
        return [engine] if engine else []

    @staticmethod
    def _extract_score(item: dict[str, Any]) -> float | None:
        score = item.get("score")
        if isinstance(score, (int, float)):
            return float(score)
        return None

    @staticmethod
    def _result_metadata(item: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "category",
            "publishedDate",
            "thumbnail",
            "img_src",
            "template",
            "parsed_url",
        )
        return {key: item[key] for key in keys if key in item and item[key] is not None}
