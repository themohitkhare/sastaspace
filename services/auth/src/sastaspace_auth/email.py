"""Resend email sender for magic-link emails.

Brand-aligned plain-text + HTML body. Sender is hi@sastaspace.com (the
Resend domain `sastaspace.com` is verified for outbound — partial DNS
status is acceptable for sending).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import resend

log = logging.getLogger(__name__)

DEFAULT_FROM = "hi@sastaspace.com"
DEFAULT_SUBJECT = "Your sign-in link to sastaspace"


@dataclass(frozen=True)
class EmailResult:
    sent: bool
    detail: str


def render_html(magic_link: str) -> str:
    return f"""<!doctype html>
<html><body style="margin:0;padding:32px;background:#f5f1e8;color:#1a1917;font-family:-apple-system,system-ui,'Inter',sans-serif">
  <div style="max-width:520px;margin:0 auto;background:#fbf8f0;border:1px solid rgba(168,161,150,0.4);border-radius:16px;padding:28px 32px">
    <p style="font-family:ui-monospace,'JetBrains Mono',Menlo,monospace;font-size:12px;letter-spacing:0.04em;color:#6b6458;margin:0 0 18px">~/mohit · sastaspace.com</p>
    <h1 style="font-size:24px;font-weight:500;letter-spacing:-0.015em;margin:0 0 14px">Sign in to sastaspace.</h1>
    <p style="font-size:15px;line-height:1.55;margin:0 0 20px">Click the link below to sign in. It's good for 15 minutes and works exactly once.</p>
    <p style="margin:0 0 24px"><a href="{magic_link}" style="display:inline-block;background:#1a1917;color:#f5f1e8;padding:12px 22px;border-radius:10px;text-decoration:none;font-size:15px;font-weight:500">sign in &rarr;</a></p>
    <p style="font-size:13px;color:#6b6458;margin:0 0 8px">If the button doesn't work, paste this URL into your browser:</p>
    <p style="font-family:ui-monospace,Menlo,monospace;font-size:12px;color:#6b6458;word-break:break-all;margin:0 0 24px">{magic_link}</p>
    <p style="font-size:12px;color:#a8a196;margin:0">If you didn't ask for this, ignore the email — nothing happens until the link is clicked.</p>
  </div>
</body></html>"""


def render_text(magic_link: str) -> str:
    return f"""Sign in to sastaspace.

Click this link to sign in (good for 15 minutes, works once):

  {magic_link}

If you didn't ask for this, ignore the email — nothing happens until the
link is clicked.

—
sastaspace.com
"""


class Sender:
    """Thin wrapper so tests can mock the resend SDK call."""

    def __init__(self, api_key: str, from_address: str = DEFAULT_FROM) -> None:
        resend.api_key = api_key
        self._from = from_address

    def send_magic_link(self, to_email: str, magic_link: str) -> EmailResult:
        try:
            resp = resend.Emails.send(
                {
                    "from": self._from,
                    "to": [to_email],
                    "subject": DEFAULT_SUBJECT,
                    "html": render_html(magic_link),
                    "text": render_text(magic_link),
                }
            )
            return EmailResult(sent=True, detail=str(resp.get("id", "")))
        except Exception as exc:  # noqa: BLE001
            log.exception("resend send failed")
            return EmailResult(sent=False, detail=str(exc))
