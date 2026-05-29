from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_CONTAINER_NAME = "local-agentic-search-searxng"
DEFAULT_COMPOSE_SERVICE = "searxng"
DEFAULT_INSPECT_TIMEOUT_SECONDS = 1.0

_COMPOSE_FILE_ENV = "LOCAL_WEB_SEARCH_DOCKER_COMPOSE_FILE"
_CONTAINER_NAME_ENV = "LOCAL_WEB_SEARCH_DOCKER_CONTAINER"
_SEARXNG_BIND_ENV = "LOCAL_WEB_SEARCH_SEARXNG_BIND"
_SEARXNG_PORT_ENV = "LOCAL_WEB_SEARCH_SEARXNG_PORT"
_DOCKER_WARNING_SHOWN = False
_CONTAINER_RUNNING = "running"
_CONTAINER_PAUSED = "paused"
_CONTAINER_NOT_RUNNING = "not_running"


def warn_docker_not_managed(*, suppress: bool = False) -> None:
    global _DOCKER_WARNING_SHOWN

    if suppress or _DOCKER_WARNING_SHOWN:
        return

    yellow = "\033[33m"
    reset = "\033[0m"
    print(
        (
            f"{yellow}Local Web Search assumes SearXNG is already running. "
            "Make sure Docker is running and start it with "
            "`docker compose up -d searxng`, or pass "
            f"`build_container_if_missing=True` to start it automatically.{reset}"
        ),
        file=sys.stderr,
    )
    _DOCKER_WARNING_SHOWN = True


def ensure_search_container_running(
    *,
    container_name: str | None = None,
    compose_file: str | Path | None = None,
    service: str = DEFAULT_COMPOSE_SERVICE,
    bind_host: str | None = None,
    host_port: int | None = None,
    inspect_timeout_seconds: float = DEFAULT_INSPECT_TIMEOUT_SECONDS,
) -> bool:
    """Ensure the local SearXNG container is running.

    Returns True when docker compose or docker unpause was invoked, False when the
    existing container was already running.
    """
    container_name = container_name or os.getenv(_CONTAINER_NAME_ENV, DEFAULT_CONTAINER_NAME)

    if shutil.which("docker") is None:
        raise RuntimeError("Docker CLI was not found on PATH. Install Docker and try again.")

    container_state = _get_container_state(
        container_name,
        timeout_seconds=inspect_timeout_seconds,
    )
    if container_state == _CONTAINER_RUNNING:
        return False
    if container_state == _CONTAINER_PAUSED:
        _warn_container_will_be_unpaused(container_name)
        _unpause_container(container_name)
        return True

    _warn_container_will_be_started(container_name)

    resolved_compose_file = _resolve_compose_file(compose_file)
    command = [
        "docker",
        "compose",
        "-f",
        str(resolved_compose_file),
        "up",
        "-d",
        "--build",
        service,
    ]
    try:
        subprocess.run(
            command,
            cwd=resolved_compose_file.parent,
            env=_compose_env(bind_host=bind_host, host_port=host_port),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        detail = f" Docker said: {stderr}" if stderr else ""
        raise RuntimeError(
            "Could not start the local SearXNG container. Make sure Docker is running "
            f"and try `docker compose up -d {service}` manually.{detail}"
        ) from exc

    return True


def _compose_env(*, bind_host: str | None, host_port: int | None) -> dict[str, str]:
    env = os.environ.copy()
    if bind_host is not None:
        env[_SEARXNG_BIND_ENV] = bind_host
    if host_port is not None:
        env[_SEARXNG_PORT_ENV] = str(host_port)
    return env


def _warn_container_will_be_started(container_name: str) -> None:
    yellow = "\033[33m"
    reset = "\033[0m"
    print(
        (
            f"{yellow}Local Web Search container {container_name!r} was not found "
            f"or is stopped. Building and starting it with docker compose...{reset}"
        ),
        file=sys.stderr,
    )


def _warn_container_will_be_unpaused(container_name: str) -> None:
    yellow = "\033[33m"
    reset = "\033[0m"
    print(
        (
            f"{yellow}Local Web Search container {container_name!r} is paused. "
            f"Unpausing it before using web search...{reset}"
        ),
        file=sys.stderr,
    )


def _unpause_container(container_name: str) -> None:
    try:
        subprocess.run(
            ["docker", "container", "unpause", container_name],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        detail = f" Docker said: {stderr}" if stderr else ""
        raise RuntimeError(
            "Could not unpause the local SearXNG container. Make sure Docker is running "
            f"and try `docker container unpause {container_name}` manually.{detail}"
        ) from exc


def _get_container_state(container_name: str, *, timeout_seconds: float) -> str:
    try:
        result = subprocess.run(
            [
                "docker",
                "container",
                "inspect",
                "--format",
                "{{.State.Running}} {{.State.Paused}}",
                container_name,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return _CONTAINER_NOT_RUNNING

    if result.returncode != 0:
        return _CONTAINER_NOT_RUNNING

    state = result.stdout.strip().lower().split()
    if state == ["true", "false"]:
        return _CONTAINER_RUNNING
    if state == ["true", "true"]:
        return _CONTAINER_PAUSED
    return _CONTAINER_NOT_RUNNING


def _resolve_compose_file(compose_file: str | Path | None) -> Path:
    if compose_file is not None:
        path = Path(compose_file).expanduser()
    elif os.getenv(_COMPOSE_FILE_ENV):
        path = Path(os.environ[_COMPOSE_FILE_ENV]).expanduser()
    else:
        cwd_compose_file = Path.cwd() / "docker-compose.yml"
        package_compose_file = Path(__file__).resolve().parent / "docker_assets" / "docker-compose.yml"
        repo_compose_file = Path(__file__).resolve().parents[2] / "docker-compose.yml"
        if cwd_compose_file.exists():
            path = cwd_compose_file
        elif package_compose_file.exists():
            path = package_compose_file
        else:
            path = repo_compose_file

    path = path.resolve()
    if not path.exists():
        raise RuntimeError(
            "Could not find docker-compose.yml for Local Web Search. "
            f"Set {_COMPOSE_FILE_ENV} to the compose file path."
        )
    return path
