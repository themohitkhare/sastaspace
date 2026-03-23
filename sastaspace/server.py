# sastaspace/server.py
from __future__ import annotations

import asyncio
import logging
import os
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from sastaspace.config import Settings
from sastaspace.crawler import crawl  # noqa: F401 — re-exported for test patching
from sastaspace.database import close_db, init_db, set_mongo_url
from sastaspace.deployer import deploy  # noqa: F401 — re-exported for test patching
from sastaspace.jobs import JobService
from sastaspace.logging_setup import configure_logging, request_id_ctx
from sastaspace.routes.admin import create_admin_router
from sastaspace.routes.health import configure as configure_health
from sastaspace.routes.health import router as health_router
from sastaspace.routes.redesign import create_redesign_router
from sastaspace.routes.sites import create_sites_router
from sastaspace.routes.sse import active_sse_tasks, sites_deployed_gauge

logger = logging.getLogger(__name__)

# Module-level job service reference -- updated during lifespan, patchable in tests
svc: JobService | None = None

_SITES_DIR: Path = Path("./sites")
_startup_time: float = 0.0


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


def _create_lifespan(settings: Settings, sites_dir: Path):
    """Return the lifespan context manager for the FastAPI app."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global svc, _startup_time
        max_retries = 5
        retry_delay = 2

        # Connect MongoDB (required)
        set_mongo_url(settings.mongodb_url, settings.mongodb_db)
        for attempt in range(1, max_retries + 1):
            try:
                await init_db()
                logger.info(
                    "MongoDB connected at %s / %s", settings.mongodb_url, settings.mongodb_db
                )
                break
            except (ConnectionError, OSError, TimeoutError):
                if attempt == max_retries:
                    logger.error(
                        "MongoDB unavailable after %d attempts — refusing to start", max_retries
                    )
                    raise
                logger.warning(
                    "MongoDB attempt %d/%d failed, retrying in %ds...",
                    attempt,
                    max_retries,
                    retry_delay,
                )
                await asyncio.sleep(retry_delay)

        # Seed sites_deployed_total from disk on startup
        try:
            count = sum(1 for d in sites_dir.iterdir() if d.is_dir() and not d.name.startswith("_"))
            sites_deployed_gauge.set(count)
        except OSError:
            pass

        # Connect Redis (required -- without it, jobs go inline and crawling fails)
        if settings.redis_url:
            for attempt in range(1, max_retries + 1):
                try:
                    _svc = JobService(redis_url=settings.redis_url)
                    await _svc.connect()
                    svc = _svc
                    logger.info("Redis job service connected at %s", settings.redis_url)
                    break
                except (ConnectionError, OSError, TimeoutError):
                    if attempt == max_retries:
                        logger.error(
                            "Redis unavailable after %d attempts — refusing to start",
                            max_retries,
                        )
                        raise
                    logger.warning(
                        "Redis attempt %d/%d failed, retrying in %ds...",
                        attempt,
                        max_retries,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)

        # Startup health checks (non-blocking -- warn only, don't fail startup)
        claude_health_url = settings.claude_code_api_url.rstrip("/").rsplit("/v1", 1)[0]
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{claude_health_url}/health", timeout=10)
                if resp.status_code == 200:
                    logger.info("Claude Code API reachable at %s", claude_health_url)
                else:
                    logger.warning(
                        "Claude Code API returned status %d at %s/health",
                        resp.status_code,
                        claude_health_url,
                    )
        except (httpx.ConnectError, httpx.TimeoutException, OSError) as e:
            logger.warning("Claude Code API unreachable at %s/health: %s", claude_health_url, e)

        _startup_time = time.monotonic()
        logger.info("Server startup complete")

        yield

        # --- Graceful Shutdown ---
        logger.info("Shutting down gracefully...")

        if active_sse_tasks:
            logger.info(
                "Waiting for %d active SSE connection(s) to drain...", len(active_sse_tasks)
            )
            done, pending = await asyncio.wait(active_sse_tasks, timeout=10.0)
            if pending:
                logger.warning(
                    "Shutdown: %d SSE connection(s) did not drain in 10s, cancelling",
                    len(pending),
                )
                for task in pending:
                    task.cancel()

        if svc:
            await svc.close()
            svc = None

        await close_db()
        logger.info("Shutdown complete")

    return lifespan


# ---------------------------------------------------------------------------
# Middleware setup
# ---------------------------------------------------------------------------


def _setup_middleware(app: FastAPI, settings: Settings, get_client_ip):
    """Attach all middleware to the FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        """Generate a unique request ID, set it in contextvars, return in headers."""
        rid = request.headers.get("X-Request-ID") or str(uuid4())
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_ctx.reset(token)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    @app.middleware("http")
    async def log_request_duration(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)
        path = request.url.path
        if not path.startswith("/metrics"):
            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": get_client_ip(request),
                },
            )
        return response


# ---------------------------------------------------------------------------
# Helper functions (used by routes and middleware)
# ---------------------------------------------------------------------------


def _get_client_ip(request: Request) -> str:
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


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def make_app(sites_dir: Path) -> FastAPI:
    """Create the FastAPI app bound to a specific sites directory."""
    settings = Settings()

    _rate_limit_store: dict[str, list[float]] = {}
    _redesign_semaphore = asyncio.Semaphore(1)

    def is_rate_limited(ip: str) -> tuple[bool, int, int, int]:
        """Check rate limit status for an IP.

        Returns (is_limited, retry_after, remaining, reset_timestamp).
        """
        now = time.time()
        window = settings.rate_limit_window_seconds
        timestamps = _rate_limit_store.get(ip, [])
        timestamps = [t for t in timestamps if t > now - window]
        if not timestamps:
            _rate_limit_store.pop(ip, None)
        else:
            _rate_limit_store[ip] = timestamps

        remaining = max(0, settings.rate_limit_max - len(timestamps))
        reset_ts = int(timestamps[0] + window) if timestamps else int(now + window)

        if len(timestamps) >= settings.rate_limit_max:
            retry_after = int(timestamps[0] - (now - window)) + 1
            return (True, retry_after, 0, reset_ts)
        return (False, 0, remaining, reset_ts)

    def record_request(ip: str) -> None:
        _rate_limit_store.setdefault(ip, []).append(time.time())

    # --- Build the app ---
    app = FastAPI(title="SastaSpace Preview Server", lifespan=_create_lifespan(settings, sites_dir))

    # Prometheus metrics
    app.mount("/metrics", make_asgi_app())

    # Middleware
    _setup_middleware(app, settings, _get_client_ip)

    # A mutable proxy so routers can access the live `svc` reference
    # (updated in lifespan). Reads always reflect the current module-level svc.
    import sastaspace.server as _self_module

    class _SvcProxy(list):
        """List-like proxy that always returns the current module-level svc."""

        def __getitem__(self, idx):
            return _self_module.svc

    svc_ref = _SvcProxy([None])

    # Wire health check router
    configure_health(
        startup_time_ref=[0.0],
        active_sse_tasks=active_sse_tasks,
        svc_ref=svc_ref,
    )
    app.include_router(health_router)

    # Wire redesign + job routes
    redesign_router = create_redesign_router(
        settings=settings,
        sites_dir=sites_dir,
        get_client_ip=_get_client_ip,
        is_localhost_fn=_is_localhost,
        is_rate_limited_fn=is_rate_limited,
        record_request_fn=record_request,
        rate_limit_store=_rate_limit_store,
        semaphore=_redesign_semaphore,
        deploy_fn=deploy,
        svc_ref=svc_ref,
    )
    app.include_router(redesign_router)

    # Wire admin/webhook routes
    admin_router = create_admin_router(settings=settings, svc_ref=svc_ref)
    app.include_router(admin_router)

    # Wire site-serving routes (must be last -- catch-all path patterns)
    sites_router = create_sites_router(sites_dir)
    app.include_router(sites_router)

    return app


# ---------------------------------------------------------------------------
# Standalone server helpers (used by CLI)
# ---------------------------------------------------------------------------


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
configure_logging(_settings.log_format)
app = make_app(_settings.sites_dir)
