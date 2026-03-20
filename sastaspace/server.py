# sastaspace/server.py
from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import time as time_mod
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import uuid4

import nh3
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.sse import EventSourceResponse, format_sse_event
from pydantic import BaseModel
from starlette.responses import Response

from sastaspace.config import Settings
from sastaspace.crawler import crawl
from sastaspace.deployer import deploy
from sastaspace.redesigner import redesign


class RedesignRequest(BaseModel):
    url: str


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

    _rate_limit_store: dict[str, list[float]] = {}
    _redesign_semaphore = asyncio.Semaphore(1)

    def get_client_ip(request: Request) -> str:
        """Extract client IP, preferring Cloudflare/proxy headers."""
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _is_localhost(ip: str) -> bool:
        return ip in ("127.0.0.1", "::1", "::ffff:127.0.0.1")

    def is_rate_limited(ip: str) -> tuple[bool, int]:
        now = time_mod.time()
        timestamps = _rate_limit_store.get(ip, [])
        timestamps = [t for t in timestamps if t > now - settings.rate_limit_window_seconds]
        _rate_limit_store[ip] = timestamps
        if len(timestamps) >= settings.rate_limit_max:
            retry_after = int(timestamps[0] - (now - settings.rate_limit_window_seconds)) + 1
            return (True, retry_after)
        return (False, 0)

    def record_request(ip: str) -> None:
        _rate_limit_store.setdefault(ip, []).append(time_mod.time())

    def _sse_event(data_str: str, event: str) -> bytes:
        """Format a single SSE event as bytes."""
        return format_sse_event(data_str=data_str, event=event)

    async def redesign_stream(url: str) -> AsyncGenerator[bytes, None]:
        job_id = str(uuid4())
        async with _redesign_semaphore:
            try:
                # Step 1: Crawl
                crawling_data = {
                    "job_id": job_id,
                    "message": "Crawling your site...",
                    "progress": 10,
                }
                yield _sse_event(json.dumps(crawling_data), "crawling")
                crawl_result = await crawl(url)
                if crawl_result.error:
                    err_msg = "Could not reach that website. Check the URL and try again."
                    yield _sse_event(
                        json.dumps({"job_id": job_id, "error": err_msg}),
                        "error",
                    )
                    return

                # Step 2: Redesign (sync -- use to_thread)
                redesigning_data = {
                    "job_id": job_id,
                    "message": "Claude is redesigning...",
                    "progress": 40,
                }
                yield _sse_event(json.dumps(redesigning_data), "redesigning")
                html = await asyncio.to_thread(
                    redesign,
                    crawl_result,
                    settings.claude_code_api_url,
                    settings.claude_model,
                )

                # Sanitize with nh3
                html = nh3.clean(html)

                # Step 3: Deploy (sync -- use to_thread)
                deploying_data = {
                    "job_id": job_id,
                    "message": "Deploying your redesign...",
                    "progress": 80,
                }
                yield _sse_event(json.dumps(deploying_data), "deploying")
                result = await asyncio.to_thread(deploy, url, html, settings.sites_dir)

                # Step 4: Done
                done_data = {
                    "job_id": job_id,
                    "message": "Done!",
                    "progress": 100,
                    "url": f"/{result.subdomain}/",
                    "subdomain": result.subdomain,
                }
                yield _sse_event(json.dumps(done_data), "done")
            except Exception:
                err_data = {
                    "job_id": job_id,
                    "error": ("Redesign service unavailable. Please try again later."),
                }
                yield _sse_event(json.dumps(err_data), "error")
                return

    @app.post("/redesign")
    async def redesign_endpoint(body: RedesignRequest, request: Request):
        ip = get_client_ip(request)

        # Rate limit check (localhost exempt)
        if not _is_localhost(ip):
            limited, retry_after = is_rate_limited(ip)
            if limited:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": (
                            f"Rate limit exceeded. Try again in {retry_after // 60 + 1} minutes."
                        ),
                        "retry_after": retry_after,
                    },
                )

        # Record attempt (localhost exempt)
        if not _is_localhost(ip):
            record_request(ip)

        # Concurrency check
        if _redesign_semaphore.locked():
            return JSONResponse(
                status_code=429,
                content={"error": "A redesign is already in progress. Please wait and try again."},
            )

        return EventSourceResponse(redesign_stream(body.url))

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
