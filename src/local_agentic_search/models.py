from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FullTextCommand(BaseModel):
    tool: str = "web_fetch"
    arguments: dict[str, Any]


class SiteLink(BaseModel):
    title: str
    url: str


class SearchResult(BaseModel):
    result_id: str
    search_id: str
    position: int
    title: str
    url: str
    snippet: str = ""
    site_links: list[SiteLink] = Field(default_factory=list)
    source: str | None = None
    engines: list[str] = Field(default_factory=list)
    score: float | None = None
    full_text_available: bool = False
    full_text_command: FullTextCommand | None = None
    full_text_command_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    search_id: str
    count: int
    results: list[SearchResult]
    suggestions: list[str] = Field(default_factory=list)
    answers: list[str] = Field(default_factory=list)
    cache_hit: bool = False
    warnings: list[str] = Field(default_factory=list)


class FetchResponse(BaseModel):
    success: bool
    result_id: str | None = None
    url: str
    title: str | None = None
    content: str = ""
    start: int = 0
    end: int = 0
    total_chars: int = 0
    has_more: bool = False
    next_fetch_command: FullTextCommand | None = None
    next_fetch_command_text: str | None = None
    cache_hit: bool = False
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5
    page: int = 1
    language: str | None = None
    categories: str | None = None
    engines: str | None = None
    time_range: str | None = None
    safesearch: int = 0
    refresh: bool = False


class FetchRequest(BaseModel):
    result_id: str | None = None
    url: str | None = None
    start: int = 0
    max_chars: int | None = None
    refresh: bool = False
