"""Minimal SpacetimeDB HTTP client for admin-api write operations."""

from __future__ import annotations

import json

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class ReducerError(RuntimeError):
    def __init__(self, reducer: str, status: int, body: str) -> None:
        super().__init__(body or f"{reducer} failed (HTTP {status})")
        self.reducer = reducer
        self.status = status
        self.body = body


class TransientError(RuntimeError):
    """Network/5xx errors worth retrying."""


_RETRY = dict(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=0.5, max=4),
    retry=retry_if_exception_type(TransientError),
    reraise=True,
)


class SpacetimeClient:
    def __init__(self, base_url: str, database: str, owner_token: str, timeout: float = 10.0) -> None:
        self._base = base_url.rstrip("/")
        self._database = database
        self._client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SpacetimeClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _call_reducer(self, name: str, args: list) -> None:
        url = f"{self._base}/v1/database/{self._database}/call/{name}"
        try:
            r = self._client.post(url, content=json.dumps(args), headers={"Content-Type": "application/json"})
        except httpx.RequestError as exc:
            raise TransientError(f"network error calling {name}: {exc}") from exc

        if r.status_code < 400:
            return

        body = (r.text or "").strip()
        if r.status_code in (400, 401, 403, 404, 530) and body:
            raise ReducerError(name, r.status_code, body)
        raise TransientError(f"{name} failed: HTTP {r.status_code} {body or '<empty>'}")

    @retry(**_RETRY)
    def set_comment_status(self, comment_id: int, status: str) -> None:
        self._call_reducer("set_comment_status", [comment_id, status])

    @retry(**_RETRY)
    def delete_comment(self, comment_id: int) -> None:
        self._call_reducer("delete_comment", [comment_id])
