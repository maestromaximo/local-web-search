from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CrawledPage:
    url: str
    title: str | None
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _markdown_to_text(markdown: Any) -> str:
    if markdown is None:
        return ""
    if isinstance(markdown, str):
        return markdown
    for attr in ("fit_markdown", "markdown", "raw_markdown"):
        value = getattr(markdown, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    return str(markdown)


class Crawl4AIFetcher:
    def __init__(self, timeout_ms: int = 45_000) -> None:
        self.timeout_ms = timeout_ms

    async def fetch(self, url: str) -> CrawledPage:
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
        except ImportError as exc:
            raise RuntimeError(
                "Crawl4AI is not installed. Install with `pip install Crawl4AI` and run "
                "`crawl4ai-setup`."
            ) from exc

        browser_config = BrowserConfig(headless=True)
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=self.timeout_ms,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url, config=run_config)

        if not getattr(result, "success", False):
            error = getattr(result, "error_message", None) or "Crawl4AI crawl failed"
            raise RuntimeError(error)

        metadata = dict(getattr(result, "metadata", None) or {})
        title = metadata.get("title")
        content = _markdown_to_text(getattr(result, "markdown", None)).strip()
        status_code = getattr(result, "status_code", None)
        if status_code is not None:
            metadata["status_code"] = status_code

        return CrawledPage(
            url=getattr(result, "url", None) or url,
            title=title,
            content=content,
            metadata=metadata,
        )
