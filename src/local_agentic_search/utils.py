from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from local_agentic_search.models import FullTextCommand

_SPACE_RE = re.compile(r"\s+")


def stable_hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def stable_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compact_text(value: Any) -> str:
    if value is None:
        return ""
    return _SPACE_RE.sub(" ", str(value)).strip()


def is_fetchable_url(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def make_fetch_command(
    result_id: str | None,
    *,
    start: int = 0,
    max_chars: int = 4_000,
    url: str | None = None,
) -> FullTextCommand:
    arguments: dict[str, Any] = {"start": start, "max_chars": max_chars}
    if result_id:
        arguments["result_id"] = result_id
    if url and not result_id:
        arguments["url"] = url
    return FullTextCommand(arguments=arguments)


def make_fetch_command_text(
    result_id: str | None,
    *,
    start: int = 0,
    max_chars: int = 4_000,
    url: str | None = None,
) -> str:
    if result_id:
        return f"web_fetch(result_id='{result_id}', start={start}, max_chars={max_chars})"
    return f"web_fetch(url='{url}', start={start}, max_chars={max_chars})"


def clamp_slice(content: str, start: int, max_chars: int) -> tuple[str, int, int, bool]:
    safe_start = max(0, min(start, len(content)))
    safe_max = max(1, max_chars)
    end = min(len(content), safe_start + safe_max)
    return content[safe_start:end], safe_start, end, end < len(content)
