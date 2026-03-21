# sastaspace/database.py
"""SQLite database for persistent job tracking and site metadata."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import aiosqlite

_DB_PATH: Path | None = None
_SCHEMA_VERSION = 1


class JobStatus(StrEnum):
    QUEUED = "queued"
    CRAWLING = "crawling"
    REDESIGNING = "redesigning"
    DEPLOYING = "deploying"
    DONE = "done"
    FAILED = "failed"


SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    subdomain TEXT,
    original_url TEXT,
    client_ip TEXT,
    tier TEXT NOT NULL DEFAULT 'standard',
    progress INTEGER NOT NULL DEFAULT 0,
    message TEXT DEFAULT '',
    error TEXT,
    html_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_client_ip ON jobs(client_ip);

CREATE TABLE IF NOT EXISTS sites (
    subdomain TEXT PRIMARY KEY,
    original_url TEXT NOT NULL,
    job_id TEXT REFERENCES jobs(id),
    tier TEXT NOT NULL DEFAULT 'standard',
    created_at TEXT NOT NULL,
    html_path TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sites_created_at ON sites(created_at);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
"""


def set_db_path(path: Path) -> None:
    """Set the database file path. Call before any DB operations."""
    global _DB_PATH
    _DB_PATH = path


def _get_db_path() -> Path:
    if _DB_PATH is None:
        return Path("./data/sastaspace.db")
    return _DB_PATH


async def get_db() -> aiosqlite.Connection:
    """Get an async SQLite connection."""
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    """Initialize the database schema."""
    db = await get_db()
    try:
        await db.executescript(SCHEMA_SQL)
        # Check/set schema version
        cursor = await db.execute("SELECT COUNT(*) FROM schema_version")
        row = await cursor.fetchone()
        if row[0] == 0:
            await db.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (_SCHEMA_VERSION,)
            )
        await db.commit()
    finally:
        await db.close()


async def create_job(
    job_id: str,
    url: str,
    client_ip: str,
    tier: str = "standard",
) -> dict:
    """Insert a new job record. Returns the job dict."""
    now = datetime.now(UTC).isoformat()
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO jobs
               (id, url, status, client_ip, tier, progress, message, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, url, JobStatus.QUEUED.value, client_ip, tier, 0, "Queued", now, now),
        )
        await db.commit()
        return {
            "id": job_id,
            "url": url,
            "status": JobStatus.QUEUED.value,
            "client_ip": client_ip,
            "tier": tier,
            "progress": 0,
            "message": "Queued",
            "created_at": now,
            "updated_at": now,
        }
    finally:
        await db.close()


async def update_job(
    job_id: str,
    *,
    status: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    error: str | None = None,
    subdomain: str | None = None,
    html_path: str | None = None,
) -> None:
    """Update fields on a job record."""
    now = datetime.now(UTC).isoformat()
    fields = ["updated_at = ?"]
    values: list = [now]

    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if progress is not None:
        fields.append("progress = ?")
        values.append(progress)
    if message is not None:
        fields.append("message = ?")
        values.append(message)
    if error is not None:
        fields.append("error = ?")
        values.append(error)
    if subdomain is not None:
        fields.append("subdomain = ?")
        values.append(subdomain)
    if html_path is not None:
        fields.append("html_path = ?")
        values.append(html_path)
    if status in (JobStatus.DONE.value, JobStatus.FAILED.value):
        fields.append("completed_at = ?")
        values.append(now)

    values.append(job_id)

    db = await get_db()
    try:
        await db.execute(
            f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        await db.commit()
    finally:
        await db.close()


async def get_job(job_id: str) -> dict | None:
    """Fetch a single job by ID."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        await db.close()


async def list_jobs(
    limit: int = 50,
    status: str | None = None,
) -> list[dict]:
    """List recent jobs, optionally filtered by status."""
    db = await get_db()
    try:
        if status:
            cursor = await db.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def register_site(
    subdomain: str,
    original_url: str,
    job_id: str,
    html_path: str,
    tier: str = "standard",
) -> None:
    """Register a deployed site in the sites table."""
    now = datetime.now(UTC).isoformat()
    db = await get_db()
    try:
        await db.execute(
            """INSERT OR REPLACE INTO sites
               (subdomain, original_url, job_id, tier, created_at, html_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (subdomain, original_url, job_id, tier, now, html_path),
        )
        await db.commit()
    finally:
        await db.close()


async def list_sites(limit: int = 100) -> list[dict]:
    """List all deployed sites."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM sites ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def count_recent_jobs(client_ip: str, window_seconds: int) -> int:
    """Count jobs created by an IP within the last N seconds."""
    cutoff = datetime.now(UTC).timestamp() - window_seconds
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=UTC).isoformat()
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM jobs WHERE client_ip = ? AND created_at > ?",
            (client_ip, cutoff_iso),
        )
        row = await cursor.fetchone()
        return row[0]
    finally:
        await db.close()
