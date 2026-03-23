# sastaspace/routes/sites.py
"""Static site serving and admin index routes."""

from __future__ import annotations

import html
import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from starlette.responses import Response


def create_sites_router(sites_dir: Path) -> APIRouter:
    """Create the site-serving router bound to a specific sites directory."""
    r = APIRouter()

    @r.get("/", response_class=HTMLResponse)
    async def index() -> str:
        registry_path = sites_dir / "_registry.json"
        registry: list[dict] = []
        if registry_path.exists():
            try:
                registry = json.loads(registry_path.read_text())
            except (json.JSONDecodeError, OSError):
                registry = []

        row_parts: list[str] = []
        for entry in sorted(registry, key=lambda e: e.get("timestamp", ""), reverse=True):
            sub = entry["subdomain"]
            orig = entry.get("original_url", "")
            orig_escaped = html.escape(orig, quote=True)
            ts = entry.get("timestamp", "")[:19].replace("T", " ")
            row_parts.append(
                f"<tr>"
                f"<td><a href='/{sub}/'>{sub}</a></td>"
                f"<td><a href='{orig_escaped}' target='_blank'>{orig_escaped}</a></td>"
                f"<td>{ts}</td>"
                f"</tr>"
            )
        rows = "".join(row_parts)

        if not rows:
            body = (
                "<p>No sites redesigned yet. Run <code>sastaspace redesign &lt;url&gt;</code></p>"
            )
        else:
            body = f"""
            <table>
              <thead><tr><th>Preview</th><th>Original URL</th><th>Created</th></tr></thead>
              <tbody>{rows}</tbody>
            </table>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SastaSpace — Redesigned Sites</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 900px;
            margin: 40px auto; padding: 0 20px; }}
    h1 {{ font-size: 1.8rem; margin-bottom: 4px; }}
    p.tagline {{ color: #666; margin-top: 0; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #eee; }}
    th {{ background: #f5f5f5; font-weight: 600; }}
    a {{ color: #0066cc; }}
    code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
  </style>
</head>
<body>
  <h1>SastaSpace</h1>
  <p class="tagline">AI Website Redesigner — local preview server</p>
  {body}
</body>
</html>"""

    @r.get("/{subdomain}/", response_class=HTMLResponse)
    async def serve_site(subdomain: str) -> Response:
        resolved_root = sites_dir.resolve()
        index_path = (sites_dir / subdomain / "index.html").resolve()
        if not index_path.is_relative_to(resolved_root):
            return HTMLResponse("<h1>404</h1>", status_code=404)
        if not index_path.exists():
            return HTMLResponse(
                f"<h1>404</h1><p>No redesign found for <code>{html.escape(subdomain)}</code></p>",
                status_code=404,
            )
        return FileResponse(str(index_path), media_type="text/html")

    @r.get("/{subdomain}/{path:path}", response_class=HTMLResponse)
    async def serve_site_asset(subdomain: str, path: str) -> Response:
        resolved_root = sites_dir.resolve()
        asset_path = (sites_dir / subdomain / path).resolve()
        if not asset_path.is_relative_to(resolved_root):
            return HTMLResponse("<h1>404</h1>", status_code=404)
        if asset_path.exists() and asset_path.is_file():
            return FileResponse(str(asset_path))
        index_path = (sites_dir / subdomain / "index.html").resolve()
        if index_path.is_relative_to(resolved_root) and index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")
        return HTMLResponse("<h1>404</h1>", status_code=404)

    return r
