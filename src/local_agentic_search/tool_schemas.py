from __future__ import annotations

from typing import Any


def responses_tool_schemas() -> list[dict[str, Any]]:
    """Return OpenAI Responses API function schemas for local tool execution."""
    return [
        {
            "type": "function",
            "name": "web_search",
            "description": (
                "Search the web through SearXNG. Returns compact snippets, stable result_ids, "
                "and the exact web_fetch command to retrieve full text when needed."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Maximum number of results to return.",
                    },
                    "page": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "SearXNG result page number.",
                    },
                    "language": {
                        "type": ["string", "null"],
                        "description": "Optional SearXNG language code, or null.",
                    },
                    "categories": {
                        "type": ["string", "null"],
                        "description": "Optional comma-separated SearXNG categories, or null.",
                    },
                    "engines": {
                        "type": ["string", "null"],
                        "description": "Optional comma-separated SearXNG engines, or null.",
                    },
                    "time_range": {
                        "type": ["string", "null"],
                        "enum": ["day", "month", "year", None],
                        "description": "Optional recency filter.",
                    },
                    "safesearch": {
                        "type": "integer",
                        "enum": [0, 1, 2],
                        "description": "SearXNG safesearch level.",
                    },
                    "refresh": {
                        "type": "boolean",
                        "description": "Bypass cached search results when true.",
                    },
                },
                "required": [
                    "query",
                    "max_results",
                    "page",
                    "language",
                    "categories",
                    "engines",
                    "time_range",
                    "safesearch",
                    "refresh",
                ],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "web_fetch",
            "description": (
                "Fetch full text for a result returned by web_search. Prefer result_id from "
                "web_search. Use start and max_chars to request only the needed portion."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "result_id": {
                        "type": ["string", "null"],
                        "description": "Result ID returned by web_search, or null if using url.",
                    },
                    "url": {
                        "type": ["string", "null"],
                        "description": "Direct URL to fetch only when no result_id is available.",
                    },
                    "start": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Character offset into the fetched page text.",
                    },
                    "max_chars": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                        "maximum": 20000,
                        "description": "Maximum characters to return, or null for the default.",
                    },
                    "refresh": {
                        "type": "boolean",
                        "description": "Bypass cached page text when true.",
                    },
                },
                "required": ["result_id", "url", "start", "max_chars", "refresh"],
                "additionalProperties": False,
            },
        },
    ]
