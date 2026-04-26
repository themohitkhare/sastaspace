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
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class ReducerError(RuntimeError):
    """Terminal failure from a SpacetimeDB reducer (Result::Err string).

    Distinct from TransientError so tenacity can refuse to retry these —
    a token that's expired stays expired no matter how many times we ask.
    """

    def __init__(self, reducer: str, status: int, body: str) -> None:
        super().__init__(body or f"{reducer} failed (HTTP {status})")
        self.reducer = reducer
        self.status = status
        self.body = body


class TransientError(RuntimeError):
    """Network/5xx-without-body errors. Worth retrying."""


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

    def _call_reducer(self, name: str, args: list, database: str | None = None) -> None:
        db = database or self._database
        url = f"{self._base}/v1/database/{db}/call/{name}"
        try:
            r = self._client.post(
                url,
                content=json.dumps(args),
                headers={"Content-Type": "application/json"},
            )
        except httpx.RequestError as exc:
            # Connection refused, timeout, DNS failure — worth retrying.
            raise TransientError(f"network error calling {name}: {exc}") from exc

        if r.status_code < 400:
            return

        # SpacetimeDB returns reducer Result::Err strings as the response body.
        # 530 with a non-empty body is a terminal "the reducer said no" — no
        # amount of retrying changes the answer. Surface the body verbatim.
        body = (r.text or "").strip()
        if r.status_code in (400, 401, 403, 404, 530) and body:
            raise ReducerError(name, r.status_code, body)
        # 5xx without a body, 502/503/504 etc — transient.
        raise TransientError(f"{name} failed: HTTP {r.status_code} {body or '<empty>'}")

    # Retry only on TransientError. ReducerError fails fast.
    _RETRY = dict(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=0.5, max=4),
        retry=retry_if_exception_type(TransientError),
        reraise=True,
    )

    @retry(**_RETRY)
    def issue_auth_token(self, token: str, email: str) -> None:
        self._call_reducer("issue_auth_token", [token, email])

    @retry(**_RETRY)
    def consume_auth_token(self, token: str) -> None:
        self._call_reducer("consume_auth_token", [token])

    @retry(**_RETRY)
    def register_user(self, identity_hex: str, email: str, display_name: str) -> None:
        # SpacetimeDB REST encodes Identity args as {"__identity__": "0x<hex>"}.
        # Verified by probing the live reducer; plain strings get rejected.
        ident = identity_hex if identity_hex.startswith("0x") else f"0x{identity_hex}"
        self._call_reducer("register_user", [{"__identity__": ident}, email, display_name])

    @retry(**_RETRY)
    def claim_progress_typewars(
        self,
        prev_identity_hex: str,
        new_identity_hex: str,
        email: str,
        typewars_module: str,
    ) -> None:
        """Owner-only call to typewars's claim_progress reducer.

        Identity hex strings are wrapped in 1-element arrays per stdb wire format
        (verified via test invocations: spacetime call typewars claim_progress '["0x..."]' ...).
        """
        self._call_reducer(
            "claim_progress",
            [[prev_identity_hex], [new_identity_hex], email],
            database=typewars_module,
        )

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
