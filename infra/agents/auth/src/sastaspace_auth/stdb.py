"""HTTP client for the sastaspace SpacetimeDB module.

Wraps the three reducers the auth service needs:
- issue_auth_token  — owner-only: store a pending magic-link token
- consume_auth_token — owner-only: mark a token used (validates expiry)
- register_user      — owner-only: persist (identity, email, display_name)

Plus one stdb-native call:
- POST /v1/identity   — get a fresh anonymous identity for a new user
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass(frozen=True)
class IssuedIdentity:
    identity_hex: str
    token: str


class SpacetimeClient:
    def __init__(
        self,
        base_url: str,
        database: str,
        owner_token: str,
        timeout: float = 10.0,
    ) -> None:
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

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _call_reducer(self, name: str, args: list) -> None:
        url = f"{self._base}/v1/database/{self._database}/call/{name}"
        r = self._client.post(
            url,
            content=json.dumps(args),
            headers={"Content-Type": "application/json"},
        )
        # Reducers return text on error (the Result::Err string); raise so
        # callers see the actual reason.
        if r.status_code >= 400:
            raise RuntimeError(f"reducer {name} failed: {r.status_code} {r.text}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4))
    def issue_auth_token(self, token: str, email: str) -> None:
        self._call_reducer("issue_auth_token", [token, email])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4))
    def consume_auth_token(self, token: str) -> None:
        self._call_reducer("consume_auth_token", [token])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4))
    def register_user(self, identity_hex: str, email: str, display_name: str) -> None:
        # SpacetimeDB Identity is serialised as hex string in REST args.
        self._call_reducer("register_user", [identity_hex, email, display_name])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=4))
    def issue_identity(self) -> IssuedIdentity:
        """Mint a fresh anonymous identity (and its bearer token) from stdb.

        We do this once per signup. The token is what the client uses to
        sign in for subsequent stdb calls (subscribing to comments,
        calling submit_user_comment).
        """
        url = f"{self._base}/v1/identity"
        r = httpx.post(url, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        return IssuedIdentity(identity_hex=data["identity"], token=data["token"])

    def find_user_identity(self, email: str) -> str | None:
        """Look up an existing user's identity by email so re-signin keeps
        the same Identity (and therefore their existing User row).

        Returns the hex identity if a User row exists for this email,
        else None (caller should mint a fresh one).
        """
        sql = f"SELECT identity FROM \"user\" WHERE email = '{email.lower().replace(chr(39), '')}'"
        url = f"{self._base}/v1/database/{self._database}/sql"
        r = self._client.post(url, content=sql, headers={"Content-Type": "text/plain"})
        if r.status_code >= 400:
            return None
        payload = r.json()
        if not isinstance(payload, list) or not payload:
            return None
        rows = payload[0].get("rows", [])
        if not rows:
            return None
        v = rows[0][0]
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            x = v.get("__identity__")
            if isinstance(x, str):
                return x.removeprefix("0x")
        return None
