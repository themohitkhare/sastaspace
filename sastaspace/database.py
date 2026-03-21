# sastaspace/database.py
"""MongoDB database for persistent job tracking and site metadata."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_MONGO_URL = "mongodb://localhost:27017"
_DB_NAME = "sastaspace"


class JobStatus(StrEnum):
    QUEUED = "queued"
    CRAWLING = "crawling"
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
    tier: str = "standard",
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
    return {k: v for k, v in doc.items() if k != "_id"}


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
    updates: dict = {"updated_at": now}

    if status is not None:
        updates["status"] = status
    if progress is not None:
        updates["progress"] = progress
    if message is not None:
        updates["message"] = message
    if error is not None:
        updates["error"] = error
    if subdomain is not None:
        updates["subdomain"] = subdomain
    if html_path is not None:
        updates["html_path"] = html_path
    if status in (JobStatus.DONE.value, JobStatus.FAILED.value):
        updates["completed_at"] = now

    await _get_db()["jobs"].update_one({"_id": job_id}, {"$set": updates})


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
    tier: str = "standard",
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


async def find_site_by_url_hash(url_hash: str) -> dict | None:
    """Find an existing site by URL hash. Returns the site doc or None."""
    doc = await _get_db()["sites"].find_one({"url_hash": url_hash})
    if doc:
        doc.pop("_id", None)
    return doc


async def list_sites(limit: int = 100) -> list[dict]:
    """List all deployed sites."""
    cursor = _get_db()["sites"].find({}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d.pop("_id", None)
    return docs
