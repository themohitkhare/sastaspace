"""Docker SDK wrapper for container status and log streaming."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import AsyncIterator

import docker
import docker.errors


def _parse_started_at(iso: str | None) -> str:
    if not iso:
        return ""
    # Docker timestamps: "2026-04-20T10:12:00.123456789Z"
    try:
        ts = iso[:19] + "Z"
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).isoformat()
    except Exception:  # noqa: BLE001
        return iso[:19] + "Z"


def _uptime_s(started_at: str) -> int:
    if not started_at:
        return 0
    try:
        dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        return int((datetime.now(tz=timezone.utc) - dt).total_seconds())
    except Exception:  # noqa: BLE001
        return 0


def _mem_stats(container) -> tuple[int, int]:
    """Return (used_mb, limit_mb) from a stats snapshot."""
    try:
        stats = container.stats(stream=False)
        usage = stats["memory_stats"]["usage"]
        limit = stats["memory_stats"]["limit"]
        return round(usage / 1_048_576), round(limit / 1_048_576)
    except Exception:  # noqa: BLE001
        return 0, 0


def list_containers() -> list[dict]:
    client = docker.from_env()
    containers = client.containers.list(all=True)
    result = []
    for c in containers:
        attrs = c.attrs or {}
        state = attrs.get("State", {})
        started_at = _parse_started_at(state.get("StartedAt"))
        uptime = _uptime_s(started_at) if state.get("Status") == "running" else 0
        mem_used, mem_limit = _mem_stats(c) if state.get("Status") == "running" else (0, 0)
        image_tags = c.image.tags if c.image else []
        image = image_tags[0] if image_tags else (c.image.short_id if c.image else "")
        result.append(
            {
                "name": c.name,
                "status": state.get("Status", "unknown"),
                "image": image,
                "started_at": started_at,
                "uptime_s": uptime,
                "mem_usage_mb": mem_used,
                "mem_limit_mb": mem_limit,
                "restart_count": attrs.get("RestartCount", 0),
            }
        )
    return result


_KNOWN_CONTAINERS: list[str] | None = None

_LEVEL_RE = re.compile(r"\b(ERROR|WARN|WARNING|DEBUG)\b", re.IGNORECASE)


def _classify_level(line: str) -> str:
    m = _LEVEL_RE.search(line)
    if not m:
        return "info"
    word = m.group(1).upper()
    if word == "ERROR":
        return "error"
    if word in ("WARN", "WARNING"):
        return "warn"
    if word == "DEBUG":
        return "debug"
    return "info"


def known_container_names() -> list[str]:
    global _KNOWN_CONTAINERS
    if _KNOWN_CONTAINERS is None:
        client = docker.from_env()
        _KNOWN_CONTAINERS = [c.name for c in client.containers.list(all=True)]
    return _KNOWN_CONTAINERS


async def stream_logs(container_name: str, tail: int = 200) -> AsyncIterator[str]:
    """Async generator yielding SSE-formatted lines from `docker logs --follow`."""
    import json

    proc = await asyncio.create_subprocess_exec(
        "docker",
        "logs",
        "--follow",
        f"--tail={tail}",
        container_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    assert proc.stdout is not None

    async def _read():
        while True:
            raw = await proc.stdout.readline()
            if not raw:
                break
            line = raw.decode(errors="replace").rstrip("\r\n")
            # Strip Docker log timestamps if present (docker adds them with --timestamps)
            now = datetime.now(tz=timezone.utc)
            ts = now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"
            level = _classify_level(line)
            payload = json.dumps({"ts": ts, "text": line, "level": level})
            yield f"data: {payload}\n\n"

    async for event in _read():
        yield event

    if proc.returncode is None:
        proc.terminate()
        await proc.wait()
