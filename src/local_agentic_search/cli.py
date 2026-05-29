from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from local_agentic_search.service import LocalSearchService


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


async def _search(args: argparse.Namespace) -> int:
    service = LocalSearchService.from_env()
    response = await service.search(
        args.query,
        max_results=args.max_results,
        page=args.page,
        language=args.language,
        categories=args.categories,
        engines=args.engines,
        time_range=args.time_range,
        safesearch=args.safesearch,
        refresh=args.refresh,
    )
    _print_json(response.model_dump())
    return 0


async def _fetch(args: argparse.Namespace) -> int:
    service = LocalSearchService.from_env()
    target = args.result_id_or_url
    is_url = target.startswith(("http://", "https://"))
    response = await service.fetch(
        result_id=None if is_url else target,
        url=target if is_url else None,
        start=args.start,
        max_chars=args.max_chars,
        refresh=args.refresh,
    )
    _print_json(response.model_dump())
    return 0 if response.success else 1


def _serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "uvicorn is not installed. Install with `pip install local-agentic-search[server]`."
        ) from exc
    uvicorn.run(
        "local_agentic_search.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="local-web-search")
    subcommands = parser.add_subparsers(dest="command", required=True)

    search = subcommands.add_parser("search", help="Search the web through SearXNG.")
    search.add_argument("query")
    search.add_argument("--max-results", type=int, default=5)
    search.add_argument("--page", type=int, default=1)
    search.add_argument("--language")
    search.add_argument("--categories")
    search.add_argument("--engines")
    search.add_argument("--time-range", choices=["day", "month", "year"])
    search.add_argument("--safesearch", type=int, choices=[0, 1, 2], default=0)
    search.add_argument("--refresh", action="store_true")
    search.set_defaults(func=lambda args: asyncio.run(_search(args)))

    fetch = subcommands.add_parser("fetch", help="Fetch page text by result_id or URL.")
    fetch.add_argument("result_id_or_url")
    fetch.add_argument("--start", type=int, default=0)
    fetch.add_argument("--max-chars", type=int)
    fetch.add_argument("--refresh", action="store_true")
    fetch.set_defaults(func=lambda args: asyncio.run(_fetch(args)))

    serve = subcommands.add_parser("serve", help="Run the HTTP API.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8099)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=_serve)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
