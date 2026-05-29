from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import local_agentic_search.docker as docker_helpers
from local_agentic_search.agent_tools import _compact_search_payload
from local_agentic_search.cache import SQLiteSearchCache
from local_agentic_search.config import LocalSearchConfig
from local_agentic_search.crawler import CrawledPage
from local_agentic_search.service import LocalSearchService
from local_agentic_search.tool_schemas import responses_tool_schemas


class FakeSearxngClient:
    def __init__(self) -> None:
        self.last_kwargs: dict[str, object] = {}

    async def health(self) -> bool:
        return True

    async def search(self, query: str, **kwargs: object) -> dict[str, object]:
        self.last_kwargs = kwargs
        return {
            "query": query,
            "results": [
                {
                    "title": "Example Domain",
                    "url": "https://example.com/",
                    "content": "This domain is for use in illustrative examples.",
                    "engine": "fake",
                    "score": 1.0,
                }
            ],
            "suggestions": [],
            "answers": [],
            "unresponsive_engines": [["brave", "too many requests"]],
        }


class FakeFetcher:
    async def fetch(self, url: str) -> CrawledPage:
        return CrawledPage(
            url=url,
            title="Example Domain",
            content="Example Domain\n\nThis domain is for use in illustrative examples.",
            metadata={"status_code": 200},
        )


def _service(tmp_path: Path) -> LocalSearchService:
    fake_searxng = FakeSearxngClient()
    config = LocalSearchConfig(
        searxng_base_url="http://127.0.0.1:8888",
        cache_path=tmp_path / "cache.sqlite3",
    )
    return LocalSearchService(
        config,
        cache=SQLiteSearchCache(config.cache_path),
        searxng_client=fake_searxng,  # type: ignore[arg-type]
        fetcher=FakeFetcher(),  # type: ignore[arg-type]
    )


def test_search_returns_fetch_command(tmp_path: Path) -> None:
    service = _service(tmp_path)
    response = asyncio.run(service.search("example", max_results=1))

    assert response.count == 1
    result = response.results[0]
    assert result.result_id.startswith("res_")
    assert result.full_text_available is True
    assert result.full_text_command is not None
    assert result.full_text_command.arguments["result_id"] == result.result_id
    assert "web_fetch" in (result.full_text_command_text or "")


def test_fetch_returns_bounded_page_slice(tmp_path: Path) -> None:
    service = _service(tmp_path)
    search = asyncio.run(service.search("example", max_results=1))
    result_id = search.results[0].result_id

    fetched = asyncio.run(service.fetch(result_id=result_id, max_chars=20))

    assert fetched.success is True
    assert fetched.result_id == result_id
    assert fetched.content == "Example Domain\n\nThis"
    assert fetched.has_more is True
    assert fetched.next_fetch_command is not None


def test_responses_tool_schemas_are_named_for_web_tools() -> None:
    schemas = responses_tool_schemas()
    assert [schema["name"] for schema in schemas] == ["web_search", "web_fetch"]
    assert all(schema["type"] == "function" for schema in schemas)


def test_cli_help_includes_examples(capsys) -> None:
    from local_agentic_search.cli import build_parser

    parser = build_parser()

    try:
        parser.parse_args(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "Examples:" in captured.out
    assert "local-web-search doctor" in captured.out
    assert "local-web-search search" in captured.out


def test_search_normalizes_time_range_shorthand(tmp_path: Path) -> None:
    service = _service(tmp_path)
    asyncio.run(service.search("example", time_range="y", refresh=True))

    assert service.searxng.last_kwargs["time_range"] == "year"  # type: ignore[attr-defined]


def test_agent_search_payload_is_compact(tmp_path: Path) -> None:
    service = _service(tmp_path)
    response = asyncio.run(service.search("example", max_results=1))
    payload = _compact_search_payload(response)
    result = payload["results"][0]

    assert result["title"] == "Example Domain"
    assert result["full_text_command"]["tool"] == "web_fetch"
    assert "warnings" not in payload
    assert "metadata" not in result
    assert "engines" not in result
    assert "score" not in result


def test_agent_search_payload_shows_warnings_when_results_empty(tmp_path: Path) -> None:
    service = _service(tmp_path)
    response = asyncio.run(service.search("example", max_results=1))
    response.results = []
    response.count = 0

    payload = _compact_search_payload(response)

    assert payload["warnings"] == ["brave: too many requests"]


def test_docker_ensure_uses_fast_inspect_and_skips_compose(monkeypatch) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="true false\n", stderr="")

    monkeypatch.setattr(docker_helpers.shutil, "which", lambda name: "docker")
    monkeypatch.setattr(docker_helpers.subprocess, "run", fake_run)

    started = docker_helpers.ensure_search_container_running()

    assert started is False
    assert len(calls) == 1
    assert calls[0][0] == [
        "docker",
        "container",
        "inspect",
        "--format",
        "{{.State.Running}} {{.State.Paused}}",
        "local-agentic-search-searxng",
    ]
    assert calls[0][1]["timeout"] == 1.0


def test_docker_paused_container_is_treated_as_not_running(
    monkeypatch,
    capsys,
) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:3] == ["docker", "container", "inspect"]:
            return subprocess.CompletedProcess(args, 0, stdout="true true\n", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(docker_helpers.shutil, "which", lambda name: "docker")
    monkeypatch.setattr(docker_helpers.subprocess, "run", fake_run)

    started = docker_helpers.ensure_search_container_running()
    captured = capsys.readouterr()

    assert started is True
    assert "is paused" in captured.err
    assert calls[1] == [
        "docker",
        "container",
        "unpause",
        "local-agentic-search-searxng",
    ]


def test_docker_ensure_starts_compose_when_container_is_not_running(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("services:\n  searxng:\n    image: searxng/searxng\n")
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:3] == ["docker", "container", "inspect"]:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(docker_helpers.shutil, "which", lambda name: "docker")
    monkeypatch.setattr(docker_helpers.subprocess, "run", fake_run)

    started = docker_helpers.ensure_search_container_running(compose_file=compose_file)
    captured = capsys.readouterr()

    assert started is True
    assert "was not found or is stopped" in captured.err
    assert "Building and starting it with docker compose" in captured.err
    assert calls[1] == [
        "docker",
        "compose",
        "-f",
        str(compose_file.resolve()),
        "up",
        "-d",
        "--build",
        "searxng",
    ]


def test_docker_warning_is_yellow_and_suppressible(capsys) -> None:
    docker_helpers._DOCKER_WARNING_SHOWN = False

    docker_helpers.warn_docker_not_managed()
    docker_helpers.warn_docker_not_managed()
    first = capsys.readouterr()

    docker_helpers._DOCKER_WARNING_SHOWN = False
    docker_helpers.warn_docker_not_managed(suppress=True)
    second = capsys.readouterr()

    assert "\033[33m" in first.err
    assert "Make sure Docker is running" in first.err
    assert first.err.count("Local Web Search assumes SearXNG") == 1
    assert second.err == ""
