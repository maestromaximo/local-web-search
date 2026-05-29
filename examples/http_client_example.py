from __future__ import annotations

import asyncio

import httpx


async def main() -> None:
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8099", timeout=30) as client:
        search = await client.get(
            "/search",
            params={"q": "SearXNG JSON search results", "max_results": 3},
        )
        search.raise_for_status()
        payload = search.json()
        print(payload)

        if not payload["results"]:
            return

        result_id = payload["results"][0]["result_id"]
        fetch = await client.post(
            "/fetch",
            json={"result_id": result_id, "start": 0, "max_chars": 2000, "refresh": False},
        )
        fetch.raise_for_status()
        print(fetch.json())


if __name__ == "__main__":
    asyncio.run(main())
