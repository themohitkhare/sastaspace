# sastaspace/routes/health.py
"""Health check endpoint."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Health check cache (avoid hammering Redis/MongoDB on every probe)
_health_cache: dict = {}
_health_cache_ts: float = 0.0
_HEALTH_CACHE_TTL = 30.0  # seconds

# These are set by the server module during app setup
_startup_time_ref: list[float] = [0.0]
_active_sse_tasks_ref: set | None = None
_svc_ref: list = [None]  # mutable container for the job service reference


def configure(
    startup_time_ref: list[float],
    active_sse_tasks: set,
    svc_ref: list,
) -> None:
    """Wire runtime references from the main server module.

    IMPORTANT: we store the *same* svc_ref object (a _SvcProxy in production)
    rather than copying its contents.  The proxy's __getitem__ dynamically reads
    the module-level ``svc`` variable, so copying would lose that behaviour and
    the health check would always see the initial ``None``.
    """
    global _active_sse_tasks_ref, _svc_ref
    _startup_time_ref[:] = startup_time_ref
    _active_sse_tasks_ref = active_sse_tasks
    _svc_ref = svc_ref


@router.get("/health", response_model=None)
async def health_check() -> JSONResponse:
    """Enhanced health check with component status and uptime."""
    global _health_cache, _health_cache_ts

    now = time.monotonic()
    if now - _health_cache_ts < _HEALTH_CACHE_TTL and _health_cache:
        return JSONResponse(content=_health_cache)

    components: dict[str, str] = {}
    overall = "healthy"

    # Check MongoDB
    try:
        from sastaspace.database import _client

        if _client is not None:
            await _client.admin.command("ping")
            components["mongodb"] = "ok"
        else:
            components["mongodb"] = "not_connected"
            overall = "degraded"
    except Exception:
        components["mongodb"] = "error"
        overall = "degraded"

    # Check Redis
    svc = _svc_ref[0] if _svc_ref else None
    if svc and svc._redis:
        try:
            await svc._redis.ping()
            components["redis"] = "ok"
        except Exception:
            components["redis"] = "error"
            overall = "degraded"
    else:
        components["redis"] = "not_connected"
        overall = "degraded"

    # Claude API status is expensive to probe -- report as unknown
    components["claude_api"] = "unknown"

    startup_time = _startup_time_ref[0] if _startup_time_ref else 0.0
    uptime = int(now - startup_time) if startup_time > 0 else 0

    sse_count = len(_active_sse_tasks_ref) if _active_sse_tasks_ref is not None else 0

    result = {
        "status": overall,
        "components": components,
        "uptime_seconds": uptime,
        "active_sse_connections": sse_count,
    }

    _health_cache = result
    _health_cache_ts = now

    return JSONResponse(content=result)
