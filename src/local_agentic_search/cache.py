from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from local_agentic_search.models import FetchResponse, SearchResponse
from local_agentic_search.utils import stable_hash


class SQLiteSearchCache:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS searches (
                    search_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS results (
                    result_id TEXT PRIMARY KEY,
                    search_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    snippet TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pages (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL UNIQUE,
                    response_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    def load_search(self, search_id: str, ttl_seconds: int) -> SearchResponse | None:
        cutoff = time.time() - ttl_seconds
        with self._connect() as conn:
            row = conn.execute(
                "SELECT response_json FROM searches WHERE search_id = ? AND created_at >= ?",
                (search_id, cutoff),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row["response_json"])
        payload["cache_hit"] = True
        return SearchResponse.model_validate(payload)

    def save_search(self, response: SearchResponse, params: dict[str, Any]) -> None:
        now = time.time()
        response_json = response.model_dump_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO searches
                    (search_id, query, params_json, response_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    response.search_id,
                    response.query,
                    json.dumps(params, sort_keys=True),
                    response_json,
                    now,
                ),
            )
            for result in response.results:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO results
                        (
                            result_id, search_id, position, url, title, snippet,
                            result_json, created_at
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.result_id,
                        result.search_id,
                        result.position,
                        result.url,
                        result.title,
                        result.snippet,
                        result.model_dump_json(),
                        now,
                    ),
                )

    def load_result(self, result_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT result_json FROM results WHERE result_id = ?",
                (result_id,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["result_json"])

    def load_page(self, url: str, ttl_seconds: int) -> FetchResponse | None:
        cutoff = time.time() - ttl_seconds
        with self._connect() as conn:
            row = conn.execute(
                "SELECT response_json FROM pages WHERE url = ? AND created_at >= ?",
                (url, cutoff),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row["response_json"])
        payload["cache_hit"] = True
        return FetchResponse.model_validate(payload)

    def save_page(self, response: FetchResponse) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO pages (url_hash, url, response_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (stable_hash(response.url, 32), response.url, response.model_dump_json(), now),
            )
