from __future__ import annotations

from typing import Any

from local_agentic_search.models import FetchRequest, SearchRequest
from local_agentic_search.service import LocalSearchService
from local_agentic_search.tool_schemas import responses_tool_schemas


def create_app() -> Any:
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError as exc:
        raise RuntimeError(
            "FastAPI is not installed. Install with `pip install local-agentic-search[server]`."
        ) from exc

    app = FastAPI(title="Local Agentic Search", version="0.1.0")
    service = LocalSearchService.from_env()

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return await service.health()

    @app.get("/openai/tools")
    async def openai_tools() -> dict[str, Any]:
        return {"tools": responses_tool_schemas()}

    @app.get("/search")
    async def search_get(
        q: str,
        max_results: int = 5,
        page: int = 1,
        language: str | None = None,
        categories: str | None = None,
        engines: str | None = None,
        time_range: str | None = None,
        safesearch: int = 0,
        refresh: bool = False,
    ) -> dict[str, Any]:
        response = await service.search(
            q,
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

    @app.post("/search")
    async def search_post(request: SearchRequest) -> dict[str, Any]:
        response = await service.search(
            request.query,
            max_results=request.max_results,
            page=request.page,
            language=request.language,
            categories=request.categories,
            engines=request.engines,
            time_range=request.time_range,
            safesearch=request.safesearch,
            refresh=request.refresh,
        )
        return response.model_dump()

    @app.post("/fetch")
    async def fetch_post(request: FetchRequest) -> dict[str, Any]:
        response = await service.fetch(
            result_id=request.result_id,
            url=request.url,
            start=request.start,
            max_chars=request.max_chars,
            refresh=request.refresh,
        )
        if not response.success and not response.error:
            raise HTTPException(status_code=500, detail="Fetch failed")
        return response.model_dump()

    return app


app = create_app()
