# sastaspace/server.py
from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import socket
import subprocess
import sys
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.sse import EventSourceResponse, format_sse_event
from prometheus_client import Counter, Gauge, make_asgi_app
from pydantic import BaseModel
from starlette.responses import Response

from sastaspace.config import Settings
from sastaspace.crawler import crawl
from sastaspace.database import (
    JobStatus,
    close_db,
    create_job,
    get_job,
    init_db,
    list_jobs,
    list_sites,
    set_mongo_url,
    update_job,
)
from sastaspace.deployer import deploy
from sastaspace.jobs import JobService
from sastaspace.redesigner import run_redesign

# Module-level job service reference — updated during lifespan, patchable in tests
svc: JobService | None = None

logger = logging.getLogger(__name__)

# Business metrics (module-level so they survive app reloads)
_sites_deployed_gauge = Gauge("sites_deployed_total", "Number of sites currently deployed")
_redesign_requests_total = Counter(
    "redesign_requests_total",
    "Total redesign requests received",
    ["status"],  # "started" | "rate_limited" | "concurrency_limited"
)


class RedesignRequest(BaseModel):
    url: str
    tier: str = "free"  # "free", "standard", or "premium"


_SITES_DIR: Path = Path("./sites")


def make_app(sites_dir: Path) -> FastAPI:
    """Create the FastAPI app bound to a specific sites directory."""
    settings = Settings()

    _rate_limit_store: dict[str, list[float]] = {}
    _redesign_semaphore = asyncio.Semaphore(1)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global svc
        # --- Startup ---
        set_mongo_url(settings.mongodb_url, settings.mongodb_db)
        try:
            await init_db()
            logger.info("MongoDB connected at %s / %s", settings.mongodb_url, settings.mongodb_db)
        except Exception:
            logger.warning("MongoDB unavailable — job persistence disabled", exc_info=True)

        # Seed sites_deployed_total from disk on startup
        try:
            count = sum(1 for d in sites_dir.iterdir() if d.is_dir() and not d.name.startswith("_"))
            _sites_deployed_gauge.set(count)
        except Exception:
            pass

        # Connect Redis job service (if Redis is available)
        if settings.redis_url:
            try:
                _svc = JobService(redis_url=settings.redis_url)
                await _svc.connect()
                svc = _svc
                logger.info("Redis job service connected at %s", settings.redis_url)
                # Job processing is handled by the dedicated worker pod — not here
            except Exception:
                logger.warning(
                    "Redis unavailable at %s — falling back to inline processing",
                    settings.redis_url,
                    exc_info=True,
                )

        yield

        # --- Shutdown ---
        if svc:
            await svc.close()
            svc = None
        await close_db()

    app = FastAPI(title="SastaSpace Preview Server", lifespan=lifespan)

    # Prometheus metrics endpoint (internal — not behind Cloudflare CDN path)
    app.mount("/metrics", make_asgi_app())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

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
        now = time.time()
        timestamps = _rate_limit_store.get(ip, [])
        timestamps = [t for t in timestamps if t > now - settings.rate_limit_window_seconds]
        _rate_limit_store[ip] = timestamps
        if len(timestamps) >= settings.rate_limit_max:
            retry_after = int(timestamps[0] - (now - settings.rate_limit_window_seconds)) + 1
            return (True, retry_after)
        return (False, 0)

    def record_request(ip: str) -> None:
        _rate_limit_store.setdefault(ip, []).append(time.time())

    # ---- SSE stream (inline fallback when Redis is unavailable) ----

    async def redesign_stream(url: str, tier: str = "standard") -> AsyncGenerator[bytes, None]:
        job_id = str(uuid4())

        # Record job in database
        ip = "inline"
        try:
            await create_job(job_id=job_id, url=url, client_ip=ip, tier=tier)
        except Exception:
            pass

        async with _redesign_semaphore:
            try:
                # Step 1: Crawl
                crawling_data = {
                    "job_id": job_id,
                    "message": "Crawling your site...",
                    "progress": 10,
                }
                yield format_sse_event(data_str=json.dumps(crawling_data), event="crawling")

                await update_job(
                    job_id, status=JobStatus.CRAWLING.value, progress=10, message="Crawling..."
                )
                crawl_result = await crawl(url)
                if crawl_result.error:
                    err_msg = "Could not reach that website. Check the URL and try again."
                    await update_job(job_id, status=JobStatus.FAILED.value, error=err_msg)
                    yield format_sse_event(
                        data_str=json.dumps({"job_id": job_id, "error": err_msg}),
                        event="error",
                    )
                    return

                # Step 2: Redesign (sync -- use to_thread)
                redesigning_data = {
                    "job_id": job_id,
                    "message": "Claude is redesigning...",
                    "progress": 40,
                }
                yield format_sse_event(data_str=json.dumps(redesigning_data), event="redesigning")

                await update_job(
                    job_id,
                    status=JobStatus.REDESIGNING.value,
                    progress=40,
                    message="Redesigning...",
                )

                html = await asyncio.to_thread(run_redesign, crawl_result, settings, tier)

                # AI-generated HTML is trusted output — do not sanitize with nh3
                # as it strips <script> tags and event handlers that are part
                # of the design.

                # Step 3: Deploy (sync -- use to_thread)
                deploying_data = {
                    "job_id": job_id,
                    "message": "Deploying your redesign...",
                    "progress": 80,
                }
                yield format_sse_event(data_str=json.dumps(deploying_data), event="deploying")

                await update_job(
                    job_id,
                    status=JobStatus.DEPLOYING.value,
                    progress=80,
                    message="Deploying...",
                )
                result = await asyncio.to_thread(deploy, url, html, settings.sites_dir)
                _sites_deployed_gauge.inc()

                # Step 4: Done
                done_data = {
                    "job_id": job_id,
                    "message": "Done!",
                    "progress": 100,
                    "url": f"/{result.subdomain}/",
                    "subdomain": result.subdomain,
                }
                await update_job(
                    job_id,
                    status=JobStatus.DONE.value,
                    progress=100,
                    message="Done!",
                    subdomain=result.subdomain,
                    html_path=str(result.index_path),
                )
                yield format_sse_event(data_str=json.dumps(done_data), event="done")
            except Exception:
                err_data = {
                    "job_id": job_id,
                    "error": ("Redesign service unavailable. Please try again later."),
                }
                await update_job(
                    job_id,
                    status=JobStatus.FAILED.value,
                    error="Redesign service unavailable",
                )
                yield format_sse_event(data_str=json.dumps(err_data), event="error")
                return

    # ---- SSE stream via Redis Pub/Sub ----

    async def redis_job_stream(job_id: str) -> AsyncGenerator[bytes, None]:
        """Stream job status updates from Redis Pub/Sub as SSE events."""
        if not svc:
            return

        async for update in svc.subscribe_job(job_id):
            event_name = update.get("event", "message")
            data = update.get("data", update)
            yield format_sse_event(data_str=json.dumps(data), event=event_name)

    # ---- API Endpoints ----

    @app.post("/redesign")
    async def redesign_endpoint(body: RedesignRequest, request: Request):
        from sastaspace.database import find_site_by_url_hash
        from sastaspace.urls import is_valid_url, url_hash

        ip = get_client_ip(request)

        # Validate and normalize URL
        valid, normalized_or_error = is_valid_url(body.url)
        if not valid:
            return JSONResponse(
                status_code=400,
                content={"error": normalized_or_error},
            )
        body.url = normalized_or_error

        # Check for existing redesign (dedup by URL hash)
        uhash = url_hash(body.url)
        try:
            existing = await find_site_by_url_hash(uhash)
            if existing and existing.get("subdomain") and existing.get("job_id"):
                logger.info(
                    "DEDUP HIT | url=%s hash=%s subdomain=%s",
                    body.url,
                    uhash,
                    existing["subdomain"],
                )

                # Return the existing job_id so the client streams from /jobs/{id}/stream
                # That endpoint immediately emits the terminal done event for completed jobs.
                return {"job_id": existing["job_id"]}
        except Exception:
            pass  # DB unavailable — proceed with redesign

        # Validate tier
        tier = body.tier if body.tier in ("free", "standard", "premium") else "free"

        # Rate limit check (localhost exempt)
        if not _is_localhost(ip):
            limited, retry_after = is_rate_limited(ip)
            if limited:
                _redesign_requests_total.labels(status="rate_limited").inc()
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

        # If Redis is available, use async job queue — return job_id immediately
        if svc is not None:
            _redesign_requests_total.labels(status="started").inc()
            job_id = await svc.enqueue(url=body.url, client_ip=ip, tier=tier)
            return {"job_id": job_id}

        # Fallback: inline processing (no Redis)
        # Concurrency check
        if _redesign_semaphore.locked():
            _redesign_requests_total.labels(status="concurrency_limited").inc()
            return JSONResponse(
                status_code=429,
                content={"error": "A redesign is already in progress. Please wait and try again."},
            )

        _redesign_requests_total.labels(status="started").inc()
        return EventSourceResponse(redesign_stream(body.url, tier))

    # ---- Job status endpoints ----

    @app.get("/jobs/{job_id}/stream")
    async def job_stream_endpoint(job_id: str):
        """SSE stream for a specific job. Reconnectable."""
        job = await get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

        if job["status"] in (JobStatus.DONE.value, JobStatus.FAILED.value):

            async def _terminal():
                if job["status"] == JobStatus.DONE.value:
                    payload = json.dumps(
                        {
                            "job_id": job_id,
                            "subdomain": job.get("subdomain", ""),
                            "url": job.get("url", ""),
                            "progress": 100,
                        }
                    )
                    yield format_sse_event(data_str=payload, event="done")
                else:
                    payload = json.dumps(
                        {
                            "job_id": job_id,
                            "error": job.get("error", "Job failed"),
                        }
                    )
                    yield format_sse_event(data_str=payload, event="error")

            return EventSourceResponse(_terminal())

        if svc is None:
            raise HTTPException(status_code=503, detail="Job queue unavailable")

        return EventSourceResponse(redis_job_stream(job_id))

    @app.get("/jobs/{job_id}")
    async def get_job_status(job_id: str):
        """Get the current status of a redesign job."""
        job = await get_job(job_id)
        if job is None:
            return JSONResponse(status_code=404, content={"error": "Job not found"})
        return JSONResponse(content=job)

    @app.get("/jobs")
    async def list_jobs_endpoint(
        status: str | None = None,
        limit: int = 50,
    ):
        """List recent redesign jobs."""
        jobs = await list_jobs(limit=min(limit, 100), status=status)
        return JSONResponse(content={"jobs": jobs, "count": len(jobs)})

    @app.get("/sites")
    async def list_sites_endpoint(limit: int = 100):
        """List all deployed redesigned sites."""
        sites_list = await list_sites(limit=min(limit, 200))
        return JSONResponse(content={"sites": sites_list, "count": len(sites_list)})

    # ---- Twenty CRM sync ----

    @app.post("/twenty/person")
    async def create_twenty_person(request: Request):
        from sastaspace.twenty_sync import get_twenty_client

        twenty = get_twenty_client(settings.twenty_url, settings.twenty_api_key)
        try:
            body = await request.json()
            name = body.get("name", "").strip()
            email = body.get("email", "").strip()
            message = body.get("message", "")
            domain = body.get("domain")  # subdomain or null

            if not email:
                return Response(status_code=400, content="Email required")

            parts = name.split(None, 1)
            first_name = parts[0] if parts else ""
            last_name = parts[1] if len(parts) > 1 else ""

            company_id = None
            if domain:
                company = await twenty.find_company_by_domain(domain)
                if not company:
                    company = await twenty.upsert_company(domain, name=domain)
                if company:
                    company_id = company.get("id")

            person = await twenty.create_person(
                email=email,
                company_id=company_id,
                first_name=first_name,
                last_name=last_name,
            )
            if person and message:
                await twenty.create_note(person["id"], message)

            return {"ok": True}
        except Exception as e:
            logger.warning("Twenty person creation failed: %s", e)
            return {"ok": True}  # Don't reveal failures

    # ---- Existing routes ----

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
            orig_escaped = html.escape(orig, quote=True)
            ts = entry.get("timestamp", "")[:19].replace("T", " ")
            rows += (
                f"<tr>"
                f"<td><a href='/{sub}/'>{sub}</a></td>"
                f"<td><a href='{orig_escaped}' target='_blank'>{orig_escaped}</a></td>"
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
_settings = Settings()
app = make_app(_settings.sites_dir)
