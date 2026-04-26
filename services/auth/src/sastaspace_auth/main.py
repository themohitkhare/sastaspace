"""Auth FastAPI app — magic-link sign-in for sastaspace.

Two routes:
  POST /auth/request {email}      — issue token, send email
  GET  /auth/verify?t=<token>     — exchange token for stdb identity+JWT,
                                     redirect to notes with JWT in URL fragment

Health: GET /healthz
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import sys
from contextlib import asynccontextmanager
from html import escape
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr, Field

from .email import Sender
from .stdb import SpacetimeClient

log = logging.getLogger("sastaspace.auth")


def env(name: str, default: str | None = None, *, required: bool = True) -> str:
    val = os.environ.get(name, default)
    if required and not val:
        log.error("missing required env: %s", name)
        sys.exit(2)
    return val or ""


# ---------- config ----------
STDB_URL = env("STDB_HTTP_URL", "http://127.0.0.1:3100", required=False)
STDB_MODULE = env("STDB_MODULE", "sastaspace", required=False)
SPACETIME_TOKEN = env("SPACETIME_TOKEN")
RESEND_API_KEY = env("RESEND_API_KEY")
FROM_ADDRESS = env("AUTH_FROM_ADDRESS", "hi@sastaspace.com", required=False)
PUBLIC_BASE = env("PUBLIC_BASE", "https://auth.sastaspace.com", required=False)
NOTES_CALLBACK = env("NOTES_CALLBACK", "https://notes.sastaspace.com/auth/callback", required=False)
TYPEWARS_CALLBACK = env(
    "TYPEWARS_CALLBACK",
    "https://typewars.sastaspace.com/auth/callback",
    required=False,
)
TYPEWARS_MODULE = env("TYPEWARS_MODULE", "typewars", required=False)
# E2E_TEST_SECRET enables the test-mode side door on /auth/request: when a
# request arrives with `X-Test-Secret: <value>` matching this env var, the
# response includes the issued token instead of sending it via email. Lets
# Playwright drive the magic-link flow without a real inbox. Empty/unset
# disables the side door entirely.
E2E_TEST_SECRET = env("E2E_TEST_SECRET", "", required=False)
ALLOWED_ORIGINS = [o.strip() for o in env(
    "ALLOWED_ORIGINS",
    "https://sastaspace.com,https://notes.sastaspace.com",
    required=False,
).split(",") if o.strip()]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------- request/response shapes ----------
class RequestBody(BaseModel):
    email: EmailStr = Field(..., max_length=200)
    app: Literal["notes", "typewars"] = "notes"
    prev_identity: str | None = Field(None, pattern=r"^(0x)?[0-9a-fA-F]{64}$")


class RequestResponse(BaseModel):
    sent: bool
    detail: str = ""
    # Only populated in test mode (when X-Test-Secret matches). Lets E2E
    # tests skip the email roundtrip and drive /auth/verify directly.
    test_token: str | None = None


# ---------- app + lifecycle ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stdb = SpacetimeClient(STDB_URL, STDB_MODULE, SPACETIME_TOKEN)
    app.state.sender = Sender(api_key=RESEND_API_KEY, from_address=FROM_ADDRESS)
    log.info("auth ready: stdb=%s sender_from=%s", STDB_URL, FROM_ADDRESS)
    yield
    app.state.stdb.close()


app = FastAPI(title="sastaspace-auth", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/auth/request", response_model=RequestResponse)
def request_magic_link(
    body: RequestBody,
    x_test_secret: str | None = Header(default=None, alias="X-Test-Secret"),
) -> RequestResponse:
    """Generate a single-use token, store it, and email the magic link.

    When `X-Test-Secret` matches `E2E_TEST_SECRET`, the response includes
    the issued token directly so an E2E test can complete the auth flow
    without needing to retrieve the email. The token still goes through
    the same `issue_auth_token` reducer — we only skip the Resend send.
    """
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="invalid email")
    if len(email) > 200:
        raise HTTPException(status_code=400, detail="email too long")

    token = secrets.token_urlsafe(32)
    try:
        app.state.stdb.issue_auth_token(token, email)
    except Exception as exc:  # noqa: BLE001
        log.exception("issue_auth_token failed")
        raise HTTPException(status_code=502, detail=f"stdb error: {exc}") from exc

    # Test-mode side door: skip the email send and hand the token back.
    # Only triggers when the request header matches a non-empty server-side
    # secret — empty E2E_TEST_SECRET means the door is permanently shut.
    if E2E_TEST_SECRET and x_test_secret == E2E_TEST_SECRET:
        log.info("test-mode auth/request for %s — skipping email send", email)
        return RequestResponse(sent=True, detail="test mode", test_token=token)

    mlink_qs = [f"t={token}", f"app={body.app}"]
    if body.prev_identity:
        # Strip optional 0x prefix; downstream reducer expects plain hex.
        prev = body.prev_identity[2:] if body.prev_identity.startswith("0x") else body.prev_identity
        mlink_qs.append(f"prev={prev}")
    magic_link = f"{PUBLIC_BASE.rstrip('/')}/auth/verify?" + "&".join(mlink_qs)
    result = app.state.sender.send_magic_link(email, magic_link)
    if not result.sent:
        # Token's already stored; not a hard failure for the user — they can
        # retry. We do log it as a 502 though so monitoring picks it up.
        log.warning("resend send failed for %s: %s", email, result.detail)
        raise HTTPException(status_code=502, detail=f"email send failed: {result.detail}")

    return RequestResponse(sent=True, detail="check your inbox")


@app.get("/auth/verify")
def verify_magic_link(
    t: str = "",
    app_name: str = Query("notes", alias="app"),
    prev: str = "",
) -> HTMLResponse:
    """Exchange the magic-link token for an stdb identity+JWT and hand it
    back to the app via URL fragment.

    For app=notes: calls register_user on the sastaspace module (existing path).
    For app=typewars: calls claim_progress on the typewars module, using the
    prev_identity hex from the 'prev' query param to transfer guest progress.
    """
    if not t or len(t) < 32:
        return _html_error("Invalid sign-in link.", status=400)

    # Step 1: consume token (also validates expiry + already-used)
    try:
        app.state.stdb.consume_auth_token(t)
    except Exception as exc:  # noqa: BLE001
        # ReducerError: the reducer said no (token expired/used/unknown).
        # TransientError: network blip, retried already, still no luck.
        # Either way we surface a friendly version of the actual reason.
        msg = _friendly_token_error(exc)
        return _html_error(msg, status=400)

    # Step 2: figure out who this token was for
    # We need the email — the consume_auth_token reducer doesn't return it
    # in the current Result<()> shape, so we look it up via SQL.
    email = _email_for_token(app.state.stdb, t)
    if not email:
        return _html_error("Could not match this link to an email.", status=400)

    # Step 3: Mint a fresh identity for the user.
    issued = app.state.stdb.issue_identity()

    # Step 4: Dispatch on the app that initiated this sign-in flow.
    if app_name == "typewars":
        if not prev or not _is_hex_identity(prev):
            return _html_error("Missing or invalid prev_identity in callback URL.", status=400)
        try:
            app.state.stdb.claim_progress_typewars(
                prev, issued.identity_hex, email, TYPEWARS_MODULE
            )
        except Exception as exc:  # noqa: BLE001
            return _html_error(f"Could not claim progress: {exc}", status=502)
        redirect_url = TYPEWARS_CALLBACK
    else:
        # Existing notes flow: (re)register user with latest display_name so
        # public attribution stays in sync. Also handles returning users whose
        # identity changes between sign-ins (stdb anon issue always mints fresh).
        existing_identity = app.state.stdb.find_user_identity(email)
        if existing_identity:
            # We can't recover the original token without storing it (we don't),
            # so the user gets a fresh anon token bound to the same Identity is
            # NOT possible — stdb's anon issue gives a NEW identity each call.
            # So we mint a new identity anyway, and register_user replaces the
            # User row's identity with the new one (idempotent on email).
            pass
        display_name = email.split("@")[0]
        try:
            app.state.stdb.register_user(issued.identity_hex, email, display_name)
        except Exception as exc:  # noqa: BLE001
            return _html_error(f"Could not register: {exc}", status=502)
        redirect_url = NOTES_CALLBACK

    # Step 5: render an HTML page that puts the JWT in the URL fragment of
    # the callback URL (fragments don't traverse the network, so the
    # token never hits the app server).
    return HTMLResponse(_verify_success_html(redirect_url, issued.token, email))


# ---------- internals ----------
def _is_hex_identity(s: str) -> bool:
    """Return True iff s is exactly 64 lowercase/uppercase hex chars (no 0x prefix)."""
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", s))


def _email_for_token(stdb: SpacetimeClient, token: str) -> str | None:
    sql = f"SELECT email FROM auth_token WHERE token = '{token.replace(chr(39), '')}'"
    url = f"{stdb._base}/v1/database/{stdb._database}/sql"  # noqa: SLF001
    r = stdb._client.post(url, content=sql, headers={"Content-Type": "text/plain"})  # noqa: SLF001
    if r.status_code >= 400:
        return None
    payload = r.json()
    if not isinstance(payload, list) or not payload:
        return None
    rows = payload[0].get("rows", [])
    if not rows:
        return None
    v = rows[0][0]
    return v if isinstance(v, str) else None


def _verify_success_html(callback: str, jwt: str, email: str) -> str:
    safe_callback = escape(callback, quote=True)
    safe_email = escape(email, quote=True)
    safe_jwt = escape(jwt, quote=True)
    return f"""<!doctype html>
<html><head>
  <meta charset="utf-8">
  <title>signed in — sastaspace</title>
  <meta name="referrer" content="no-referrer">
  <style>
    body {{ margin:0; padding:64px 32px; background:#f5f1e8; color:#1a1917;
            font-family:-apple-system,system-ui,sans-serif; text-align:center; }}
    .box {{ max-width:480px; margin:0 auto; }}
    h1 {{ font-size:28px; font-weight:500; letter-spacing:-0.015em; margin:0 0 12px; }}
    p {{ font-size:15px; line-height:1.55; color:#3a3834; margin:0 0 16px; }}
    a.btn {{ display:inline-block; background:#1a1917; color:#f5f1e8;
             padding:12px 22px; border-radius:10px; text-decoration:none;
             font-size:15px; font-weight:500; margin-top:8px; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>You're signed in.</h1>
    <p>Welcome, <strong>{safe_email}</strong>. If you don't get redirected, click below.</p>
    <a class="btn" id="go" href="{safe_callback}">go to notes &rarr;</a>
  </div>
  <script>
    (function() {{
      var token = "{safe_jwt}";
      var email = "{safe_email}";
      var url = "{safe_callback}#token=" + encodeURIComponent(token) +
                "&email=" + encodeURIComponent(email);
      document.getElementById("go").href = url;
      window.location.replace(url);
    }})();
  </script>
</body></html>"""


_REDUCER_FRIENDLY = {
    "token expired": "This sign-in link has expired. Links are good for 15 minutes — request a new one.",
    "token already used": "This sign-in link has already been used. Request a fresh one to sign in again.",
    "unknown token": "This sign-in link doesn't match anything we issued. Request a new one.",
}


def _friendly_token_error(exc: BaseException) -> str:
    """Map raw reducer error strings to copy a human can act on."""
    raw = str(exc).strip().lower()
    for needle, friendly in _REDUCER_FRIENDLY.items():
        if needle in raw:
            return friendly
    return f"This sign-in link is no longer valid. ({exc})"


def _html_error(message: str, status: int = 400) -> HTMLResponse:
    safe = escape(message, quote=True)
    return HTMLResponse(
        status_code=status,
        content=f"""<!doctype html>
<html><body style="margin:0;padding:64px 32px;background:#f5f1e8;color:#1a1917;font-family:-apple-system,system-ui,sans-serif;text-align:center">
  <div style="max-width:480px;margin:0 auto">
    <h1 style="font-size:24px;font-weight:500;margin:0 0 12px">Sign-in failed.</h1>
    <p style="font-size:15px;color:#3a3834;line-height:1.55;margin:0 0 16px">{safe}</p>
    <p style="font-size:13px;color:#6b6458">Try again from <a href="https://notes.sastaspace.com" style="color:#8a3d14">notes.sastaspace.com</a>.</p>
  </div>
</body></html>""",
    )


# health check from compose
def main() -> None:
    import uvicorn

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))  # noqa: S104


if __name__ == "__main__":
    main()


# JSON 404 default
@app.exception_handler(404)
async def not_found(_request, _exc):
    return JSONResponse(status_code=404, content={"detail": "not found"})
