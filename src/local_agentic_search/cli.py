from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from local_agentic_search.service import LocalSearchService
from local_agentic_search.skill_loader import load_skill


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
            "uvicorn is not installed. Install with `pip install local-web-search[server]`."
        ) from exc
    uvicorn.run(
        "local_agentic_search.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


async def _doctor(args: argparse.Namespace) -> int:
    service = LocalSearchService.from_env()
    health = await service.health()
    _print_json(health)
    if health["ok"]:
        return 0
    print(
        (
            "SearXNG is not reachable. Start it with `docker compose up -d searxng` "
            "or set SEARXNG_BASE_URL to a running instance."
        ),
        file=sys.stderr,
    )
    return 1


def _skill_load(args: argparse.Namespace) -> int:
    try:
        result = load_skill(
            project_dir=None if args.target_dir else args.project_dir,
            target_dir=args.target_dir,
            force=args.force,
        )
    except (FileExistsError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _print_json(result.model_dump())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-web-search",
        description=(
            "Agent-friendly local web search using SearXNG for snippets and Crawl4AI "
            "for full-text retrieval."
        ),
        epilog=(
            "Examples:\n"
            "  local-web-search doctor\n"
            "  local-web-search search \"OpenAI Agents SDK tools\" --max-results 5\n"
            "  local-web-search fetch res_abc123 --max-chars 4000\n"
            "  local-web-search fetch https://example.com --max-chars 4000\n"
            "  local-web-search serve --host 127.0.0.1 --port 8099\n"
            "  local-web-search skill load"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    search = subcommands.add_parser(
        "search",
        help="Search the web through SearXNG and return result IDs.",
        description=(
            "Search through the configured SearXNG instance. Results include snippets "
            "and stable result_id values that can be passed to `fetch`."
        ),
    )
    search.add_argument("query", help="Search query.")
    search.add_argument("--max-results", type=int, default=5, help="Number of results, 1-20.")
    search.add_argument("--page", type=int, default=1, help="SearXNG result page number.")
    search.add_argument("--language", help="Optional SearXNG language code, such as en.")
    search.add_argument("--categories", help="Optional comma-separated SearXNG categories.")
    search.add_argument("--engines", help="Optional comma-separated SearXNG engine names.")
    search.add_argument(
        "--time-range",
        choices=["day", "month", "year"],
        help="Optional recency filter.",
    )
    search.add_argument(
        "--safesearch",
        type=int,
        choices=[0, 1, 2],
        default=0,
        help="SearXNG safesearch level: 0 off, 1 moderate, 2 strict.",
    )
    search.add_argument("--refresh", action="store_true", help="Bypass cached search results.")
    search.set_defaults(func=lambda args: asyncio.run(_search(args)))

    fetch = subcommands.add_parser(
        "fetch",
        help="Fetch full page text by result_id or URL.",
        description=(
            "Fetch extracted page text with Crawl4AI. Prefer a result_id returned by "
            "`search`; direct http(s) URLs are also accepted."
        ),
    )
    fetch.add_argument("result_id_or_url", help="Result ID from search output, or a URL.")
    fetch.add_argument("--start", type=int, default=0, help="Character offset to start at.")
    fetch.add_argument("--max-chars", type=int, help="Maximum characters to return.")
    fetch.add_argument("--refresh", action="store_true", help="Bypass cached page text.")
    fetch.set_defaults(func=lambda args: asyncio.run(_fetch(args)))

    serve = subcommands.add_parser(
        "serve",
        help="Run the optional HTTP API.",
        description="Run a FastAPI server exposing health, search, fetch, and tool-schema routes.",
    )
    serve.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    serve.add_argument("--port", type=int, default=8099, help="Port to bind.")
    serve.add_argument("--reload", action="store_true", help="Enable uvicorn reload.")
    serve.set_defaults(func=_serve)

    doctor = subcommands.add_parser(
        "doctor",
        help="Check configuration and SearXNG connectivity.",
        description="Print the active configuration and whether the SearXNG endpoint is reachable.",
    )
    doctor.set_defaults(func=lambda args: asyncio.run(_doctor(args)))

    skill = subcommands.add_parser(
        "skill",
        help="Install the Local Web Search development skill.",
        description="Install project-local skill assets for agentic coding tools.",
    )
    skill_subcommands = skill.add_subparsers(dest="skill_command", required=True)
    skill_load = skill_subcommands.add_parser(
        "load",
        help="Copy the packaged skill into .agents/skills/local-web-search.",
        description=(
            "Copy the packaged Local Web Search skill into a repo-local "
            ".agents/skills/local-web-search directory."
        ),
    )
    skill_load.add_argument(
        "--project-dir",
        default=".",
        help="Project root where .agents/skills/local-web-search will be created.",
    )
    skill_load.add_argument(
        "--target-dir",
        help="Exact destination skill directory. Cannot be combined with --project-dir.",
    )
    skill_load.add_argument(
        "--force",
        action="store_true",
        help="Overwrite packaged skill files when the destination already exists.",
    )
    skill_load.set_defaults(func=_skill_load)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
