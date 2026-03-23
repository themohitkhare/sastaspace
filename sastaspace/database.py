# sastaspace/database.py
"""MongoDB database for persistent job tracking and site metadata."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_MONGO_URL = "mongodb://localhost:27017"
_DB_NAME = "sastaspace"


class JobStatus(StrEnum):
    QUEUED = "queued"
    CRAWLING = "crawling"
    DISCOVERING = "discovering"
    DOWNLOADING = "downloading"
    ANALYZING = "analyzing"
    REDESIGNING = "redesigning"
    DEPLOYING = "deploying"
    DONE = "done"
    FAILED = "failed"


def set_mongo_url(url: str, db_name: str = "sastaspace") -> None:
    """Set MongoDB connection URL. Call before any DB operations."""
    global _MONGO_URL, _DB_NAME
    _MONGO_URL = url
    _DB_NAME = db_name


def _get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(_MONGO_URL)
        _db = _client[_DB_NAME]
    return _db


async def init_db() -> None:
    """Ensure indexes exist."""
    db = _get_db()
    jobs = db["jobs"]
    await jobs.create_index("status")
    await jobs.create_index("created_at")
    await jobs.create_index("client_ip")
    sites = db["sites"]
    await sites.create_index("subdomain", unique=True)
    await sites.create_index("url_hash")
    await sites.create_index("created_at")


async def close_db() -> None:
    """Close the MongoDB client."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None


async def create_job(
    job_id: str,
    url: str,
    client_ip: str,
    tier: str = "free",
    model_provider: str = "claude",
) -> dict:
    """Insert a new job record. Returns the job dict."""
    now = datetime.now(UTC).isoformat()
    doc = {
        "_id": job_id,
        "id": job_id,
        "url": url,
        "status": JobStatus.QUEUED.value,
        "client_ip": client_ip,
        "tier": tier,
        "model_provider": model_provider,
        "progress": 0,
        "message": "Queued",
        "subdomain": None,
        "original_url": None,
        "error": None,
        "html_path": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    await _get_db()["jobs"].insert_one(doc)
    logger.debug("create_job | id=%s url=%s tier=%s", job_id, url, tier)
    return {k: v for k, v in doc.items() if k != "_id"}


_SENTINEL = object()


@dataclass
class JobUpdate:
    status: str | None = None
    progress: int | None = None
    message: str | None = None
    error: str | None = None
    subdomain: str | None = None
    html_path: str | None = None
    site_colors: list[str] | None = None
    site_title: str | None = None
    checkpoint: dict | None | object = field(default_factory=lambda: _SENTINEL)
    pages_crawled: int | None = None
    assets_count: int | None = None
    assets_total_size: int | None = None
    business_profile: dict | None = None
    model_provider: str | None = None


def _job_update_to_dict(updates: JobUpdate) -> dict:
    """Convert a JobUpdate dataclass to a MongoDB $set dict, skipping unset fields."""
    result: dict = {}
    simple_fields = [
        "status",
        "progress",
        "message",
        "error",
        "subdomain",
        "html_path",
        "site_colors",
        "site_title",
        "pages_crawled",
        "assets_count",
        "assets_total_size",
        "business_profile",
        "model_provider",
    ]
    for f in simple_fields:
        val = getattr(updates, f)
        if val is not None:
            result[f] = val
    if updates.checkpoint is not _SENTINEL:
        result["checkpoint"] = updates.checkpoint
    return result


async def update_job(
    job_id: str,
    *,
    updates: JobUpdate | None = None,
    **kwargs: str | int | None,
) -> None:
    """Update fields on a job record.

    For simple updates, pass keyword arguments directly.
    For updates with many fields, pass a JobUpdate instance.
    """
    now = datetime.now(UTC).isoformat()
    mongo_updates: dict = {"updated_at": now}

    if updates is not None:
        mongo_updates.update(_job_update_to_dict(updates))
    for key, val in kwargs.items():
        if val is not None:
            mongo_updates[key] = val

    resolved_status = mongo_updates.get("status")
    if resolved_status in (JobStatus.DONE.value, JobStatus.FAILED.value):
        mongo_updates["completed_at"] = now

    await _get_db()["jobs"].update_one({"_id": job_id}, {"$set": mongo_updates})
    logger.debug("update_job | id=%s fields=%s", job_id, list(mongo_updates.keys()))


async def get_job(job_id: str) -> dict | None:
    """Fetch a single job by ID."""
    doc = await _get_db()["jobs"].find_one({"_id": job_id})
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


async def list_jobs(
    limit: int = 50,
    status: str | None = None,
) -> list[dict]:
    """List recent jobs, optionally filtered by status."""
    query = {"status": status} if status else {}
    cursor = _get_db()["jobs"].find(query).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d.pop("_id", None)
    return docs


async def register_site(
    subdomain: str,
    original_url: str,
    job_id: str,
    html_path: str,
    tier: str = "free",
    url_hash: str = "",
) -> None:
    """Register a deployed site (upsert by subdomain)."""
    now = datetime.now(UTC).isoformat()
    doc = {
        "subdomain": subdomain,
        "original_url": original_url,
        "job_id": job_id,
        "tier": tier,
        "html_path": html_path,
        "updated_at": now,
    }
    if url_hash:
        doc["url_hash"] = url_hash
    await _get_db()["sites"].update_one(
        {"subdomain": subdomain},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    logger.debug("register_site | subdomain=%s url=%s job=%s", subdomain, original_url, job_id)


async def find_site_by_url_hash(url_hash: str) -> dict | None:
    """Find an existing site by URL hash. Returns the site doc or None."""
    doc = await _get_db()["sites"].find_one({"url_hash": url_hash})
    if doc:
        doc.pop("_id", None)
    return doc


async def find_failed_job_checkpoint(url: str) -> dict | None:
    """Find the most recent failed job for a URL that has a checkpoint.

    Used to resume from the last successful pipeline step instead of
    restarting from scratch.
    """
    doc = await _get_db()["jobs"].find_one(
        {"url": url, "status": "failed", "checkpoint": {"$ne": None}},
        sort=[("created_at", -1)],
    )
    if doc and doc.get("checkpoint"):
        cp = doc["checkpoint"]
        # Validate checkpoint has useful data (not just empty/corrupt pipeline state)
        pipeline_data = cp.get("pipeline_data", {})
        data = pipeline_data.get("data", {}) if isinstance(pipeline_data, dict) else {}
        # Only reuse if at least the crawl analyst step completed
        if data.get("site_analysis") or cp.get("crawl_result"):
            return cp
    return None


async def list_sites(limit: int = 100) -> list[dict]:
    """List all deployed sites."""
    cursor = _get_db()["sites"].find({}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d.pop("_id", None)
    return docs
