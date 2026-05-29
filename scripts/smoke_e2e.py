from __future__ import annotations

import argparse
import asyncio
import json

from local_agentic_search.service import LocalSearchService


async def run(query: str, max_results: int, max_chars: int, refresh: bool) -> int:
    service = LocalSearchService.from_env()
    health = await service.health()
    print(json.dumps({"health": health}, indent=2))
    if not health["ok"]:
        print("SearXNG is not reachable. Start it with `docker compose up -d searxng`.")
        return 2

    search = await service.search(
        query,
        max_results=max_results,
        refresh=refresh,
    )
    print(
        json.dumps(
            {
                "search_id": search.search_id,
                "count": search.count,
                "first_results": [
                    {
                        "result_id": result.result_id,
                        "title": result.title,
                        "url": result.url,
                        "snippet": result.snippet[:180],
                    }
                    for result in search.results[:3]
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    for result in search.results:
        if not result.full_text_available:
            continue
        fetched = await service.fetch(
            result_id=result.result_id,
            max_chars=max_chars,
            refresh=refresh,
        )
        if fetched.success and fetched.content.strip():
            print(
                json.dumps(
                    {
                        "fetched": {
                            "result_id": fetched.result_id,
                            "title": fetched.title,
                            "url": fetched.url,
                            "chars": len(fetched.content),
                            "total_chars": fetched.total_chars,
                            "has_more": fetched.has_more,
                            "preview": fetched.content[:500],
                        }
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0
        print(
            json.dumps(
                {
                    "fetch_failed": {
                        "result_id": result.result_id,
                        "url": result.url,
                        "error": fetched.error,
                    }
                },
                indent=2,
            )
        )
    print("Search worked, but no result could be fetched by Crawl4AI.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="OpenAI Agents SDK function tools")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--max-chars", type=int, default=2000)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    return asyncio.run(run(args.query, args.max_results, args.max_chars, args.refresh))


if __name__ == "__main__":
    raise SystemExit(main())
