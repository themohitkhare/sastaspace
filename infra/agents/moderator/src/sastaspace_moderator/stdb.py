"""Tiny SpacetimeDB HTTP client for the moderator.

SpacetimeDB exposes:
- POST /v1/database/<name>/sql       — read-only SELECT (text/plain SQL body, JSON response)
- POST /v1/database/<name>/call/<r>  — call a reducer (JSON args body)

We do not use the WebSocket subscription protocol here — polling every few
seconds is simpler and the moderation latency budget tolerates it (we pay
~3s polling delay + ~1-2s classifier on the 7900 XTX = ~5s end-to-end).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass(frozen=True)
class PendingComment:
    id: int
    post_slug: str
    author_name: str
    body: str
    created_at_micros: int


class SpacetimeClient:
    """Minimal sync HTTP client for the sastaspace SpacetimeDB module."""

    def __init__(
        self,
        base_url: str,
        database: str,
        owner_token: str,
        timeout: float = 10.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._database = database
        self._token = owner_token
        self._client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SpacetimeClient:
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4))
    def fetch_pending(self, limit: int = 50) -> list[PendingComment]:
        """Return up to `limit` comments awaiting moderation."""
        sql = (
            "SELECT id, post_slug, author_name, body, created_at "
            f"FROM comment WHERE status = 'pending' LIMIT {int(limit)}"
        )
        url = f"{self._base}/v1/database/{self._database}/sql"
        r = self._client.post(url, content=sql, headers={"Content-Type": "text/plain"})
        r.raise_for_status()
        return _parse_pending(r.json())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4))
    def set_status(self, comment_id: int, status: str) -> None:
        """Call set_comment_status reducer as the owner."""
        url = f"{self._base}/v1/database/{self._database}/call/set_comment_status"
        r = self._client.post(
            url,
            content=json.dumps([comment_id, status]),
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()


def _parse_pending(payload: Any) -> list[PendingComment]:
    """SpacetimeDB SQL response: [{schema:..., rows:[[col1,col2,...], ...]}, ...].

    For SELECT we get a list with one statement result. Rows are arrays in
    column order matching the SELECT.
    """
    if not isinstance(payload, list) or not payload:
        return []
    first = payload[0]
    if not isinstance(first, dict):
        return []
    rows = first.get("rows", [])
    out: list[PendingComment] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 5:
            continue
        out.append(
            PendingComment(
                id=int(row[0]),
                post_slug=str(row[1]),
                author_name=str(row[2]),
                body=str(row[3]),
                created_at_micros=_micros(row[4]),
            )
        )
    return out


def _micros(ts: Any) -> int:
    """Stdb encodes Timestamp as either an int microseconds or a tagged dict."""
    if isinstance(ts, int):
        return ts
    if isinstance(ts, dict):
        v = ts.get("__timestamp_micros_since_unix_epoch__")
        if isinstance(v, int):
            return v
    return 0
