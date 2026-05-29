"""Agent-friendly local web search backed by SearXNG and Crawl4AI."""

from local_agentic_search.config import LocalSearchConfig
from local_agentic_search.service import LocalSearchService

__all__ = ["LocalSearchConfig", "LocalSearchService"]
