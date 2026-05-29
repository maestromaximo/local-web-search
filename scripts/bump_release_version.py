from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

PACKAGE_NAME = "local-web-search"
PYPROJECT = Path("pyproject.toml")
VERSION_RE = re.compile(r'^version = "(\d+)\.(\d+)\.(\d+)"$', re.MULTILINE)


def _published_versions() -> set[tuple[int, int, int]]:
    url = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return set()
        raise

    versions: set[tuple[int, int, int]] = set()
    for raw_version in payload.get("releases", {}):
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", raw_version)
        if match:
            versions.add(tuple(int(part) for part in match.groups()))
    return versions


def _next_patch_version(current: tuple[int, int, int], published: set[tuple[int, int, int]]) -> str:
    major, minor, patch = current
    candidate = (major, minor, patch)
    while candidate in published:
        candidate = (major, minor, candidate[2] + 1)
    return ".".join(str(part) for part in candidate)


def main() -> int:
    content = PYPROJECT.read_text(encoding="utf-8")
    match = VERSION_RE.search(content)
    if not match:
        raise RuntimeError("Could not find a simple MAJOR.MINOR.PATCH project version.")

    current = tuple(int(part) for part in match.groups())
    new_version = _next_patch_version(current, _published_versions())
    current_version = ".".join(match.groups())
    if new_version == current_version:
        print(f"Version {current_version} is not published yet; keeping it.")
        return 0

    updated = VERSION_RE.sub(f'version = "{new_version}"', content, count=1)
    PYPROJECT.write_text(updated, encoding="utf-8")
    print(f"Bumped version from {current_version} to {new_version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
