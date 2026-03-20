# sastaspace/server.py
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from starlette.responses import Response

from sastaspace.config import Settings

_SITES_DIR: Path = Path("./sites")


def make_app(sites_dir: Path) -> FastAPI:
    """Create the FastAPI app bound to a specific sites directory."""
    app = FastAPI(title="SastaSpace Preview Server")

    settings = Settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        registry_path = sites_dir / "_registry.json"
        registry: list[dict] = []
        if registry_path.exists():
            try:
                registry = json.loads(registry_path.read_text())
            except (json.JSONDecodeError, OSError):
                registry = []

        rows = ""
        for entry in sorted(registry, key=lambda e: e.get("timestamp", ""), reverse=True):
            sub = entry["subdomain"]
            orig = entry.get("original_url", "")
            ts = entry.get("timestamp", "")[:19].replace("T", " ")
            rows += (
                f"<tr>"
                f"<td><a href='/{sub}/'>{sub}</a></td>"
                f"<td><a href='{orig}' target='_blank'>{orig}</a></td>"
                f"<td>{ts}</td>"
                f"</tr>"
            )

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

    @app.get("/{subdomain}/")
    async def serve_site(subdomain: str) -> Response:
        index_path = sites_dir / subdomain / "index.html"
        if not index_path.exists():
            return HTMLResponse(
                f"<h1>404</h1><p>No redesign found for <code>{subdomain}</code></p>",
                status_code=404,
            )
        return FileResponse(str(index_path), media_type="text/html")

    @app.get("/{subdomain}/{path:path}")
    async def serve_site_asset(subdomain: str, path: str) -> Response:
        asset_path = sites_dir / subdomain / path
        if asset_path.exists() and asset_path.is_file():
            return FileResponse(str(asset_path))
        index_path = sites_dir / subdomain / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")
        return HTMLResponse("<h1>404</h1>", status_code=404)

    return app


def _is_port_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def ensure_running(sites_dir: Path, preferred_port: int = 8080) -> int:
    """
    Ensure the preview server is running. Returns the resolved port.

    If not running, spawns a detached uvicorn subprocess.
    Saves the resolved port to sites_dir/.server_port.
    """
    sites_dir.mkdir(parents=True, exist_ok=True)

    port_file = sites_dir / ".server_port"
    if port_file.exists():
        try:
            existing_port = int(port_file.read_text().strip())
            if _is_port_listening(existing_port):
                return existing_port
        except (ValueError, OSError):
            pass

    port = preferred_port
    for candidate in [preferred_port, preferred_port + 1, preferred_port + 2]:
        if not _is_port_listening(candidate):
            port = candidate
            break

    log_file = sites_dir / ".server.log"
    full_env = {**os.environ, "SASTASPACE_SITES_DIR": str(sites_dir.resolve())}

    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "sastaspace.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=open(log_file, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=full_env,
    )

    deadline = time.time() + 5.0
    while time.time() < deadline:
        if _is_port_listening(port):
            break
        time.sleep(0.2)

    port_file.write_text(str(port))
    return port


# Default app instance used by uvicorn when spawned as subprocess
_default_sites_dir = Path(os.environ.get("SASTASPACE_SITES_DIR", "./sites"))
app = make_app(_default_sites_dir)
