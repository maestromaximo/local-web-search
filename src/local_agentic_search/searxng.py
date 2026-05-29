from __future__ import annotations

from typing import Any

import httpx


class SearxngError(RuntimeError):
    pass


class SearxngClient:
    def __init__(self, base_url: str, timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = await client.get(f"{self.base_url}/")
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    async def search(
        self,
        query: str,
        *,
        page: int = 1,
        language: str | None = None,
        categories: str | None = None,
        engines: str | None = None,
        time_range: str | None = None,
        safesearch: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "pageno": page,
            "safesearch": safesearch,
        }
        if language:
            params["language"] = language
        if categories:
            params["categories"] = categories
        if engines:
            params["engines"] = engines
        if time_range:
            params["time_range"] = time_range

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = await client.get(f"{self.base_url}/search", params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise SearxngError(
                f"SearXNG returned HTTP {exc.response.status_code}: {body}"
            ) from exc
        except httpx.HTTPError as exc:
            raise SearxngError(f"Could not reach SearXNG at {self.base_url}: {exc}") from exc
        except ValueError as exc:
            raise SearxngError("SearXNG did not return valid JSON. Is json enabled?") from exc
