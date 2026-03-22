# Twenty CRM Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Twenty CRM as a lead management system and admin panel for SastaSpace, with bidirectional sync (push on events, webhooks for admin actions, pull for reconciliation).

**Architecture:** A new `TwentyClient` (async, httpx-based) pushes job/contact data to Twenty's REST API. A `/webhooks/twenty` endpoint receives admin actions (delete/reprocess) with HMAC verification and Redis dedup. A `/admin/sync` endpoint reconciles missed events. Twenty runs as a separate k8s namespace on the same cluster.

**Tech Stack:** httpx (async HTTP), FastAPI webhooks, Redis (dedup), Twenty REST API, k8s manifests

**Spec:** `docs/superpowers/specs/2026-03-22-twenty-crm-integration-design.md`

---

## Task 1: Add httpx Dependency

**Files:**
- Modify: `pyproject.toml` (line 6-28, dependencies)

- [ ] **Step 1: Add httpx to dependencies**

Add to `[project.dependencies]` in `pyproject.toml`:
```toml
"httpx>=0.27.0",
```

- [ ] **Step 2: Sync lockfile**

Run: `uv sync`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add httpx for Twenty CRM async API client"
```

---

## Task 2: Config — Twenty Settings

**Files:**
- Modify: `sastaspace/config.py` (after line 57, Redis section)
- Test: `tests/test_config.py` (extend)

- [ ] **Step 1: Write test for new config fields**

Add to `tests/test_config.py`:
```python
def test_twenty_defaults_disabled():
    s = Settings()
    assert s.twenty_url == ""
    assert s.twenty_api_key == ""
    assert s.twenty_webhook_secret == ""
    assert s.twenty_admin_key == ""
```

- [ ] **Step 2: Run test — should fail**

Run: `uv run pytest tests/test_config.py::test_twenty_defaults_disabled -v`

- [ ] **Step 3: Add Twenty fields to Settings**

In `sastaspace/config.py`, add after the `redis_url` field (line 57):

```python
    # Twenty CRM (empty = integration disabled)
    twenty_url: str = ""
    twenty_api_key: str = ""
    twenty_webhook_secret: str = ""
    twenty_admin_key: str = ""
```

- [ ] **Step 4: Run test — should pass**

Run: `uv run pytest tests/test_config.py -v`

- [ ] **Step 5: Commit**

```bash
git add sastaspace/config.py tests/test_config.py
git commit -m "feat: add Twenty CRM config fields (disabled by default)"
```

---

## Task 3: TwentyClient — Core API Wrapper

**Files:**
- Create: `sastaspace/twenty_sync.py`
- Test: `tests/test_twenty_sync.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_twenty_sync.py
"""Tests for Twenty CRM sync client. All HTTP calls mocked."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sastaspace.twenty_sync import TwentyClient


@pytest.fixture
def client():
    return TwentyClient(base_url="http://twenty:3000/rest", api_key="test-key")


class TestUpsertCompany:
    @pytest.mark.asyncio
    async def test_creates_company_when_not_found(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            # First call: search returns empty
            # Second call: create returns new company
            mock_req.side_effect = [
                {"data": {"companies": []}},  # search
                {"data": {"createCompany": {"id": "c1"}}},  # create
            ]
            result = await client.upsert_company("example.com", name="Example Corp")
            assert result["id"] == "c1"
            assert mock_req.call_count == 2

    @pytest.mark.asyncio
    async def test_updates_company_when_found(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = [
                {"data": {"companies": [{"id": "c1", "domain": "example.com"}]}},  # search
                {"data": {"updateCompany": {"id": "c1"}}},  # update
            ]
            result = await client.upsert_company("example.com", name="Example Corp Updated")
            assert result["id"] == "c1"


class TestCreateRedesignJob:
    @pytest.mark.asyncio
    async def test_creates_job_record(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": {"createRedesignJob": {"id": "rj1"}}}
            result = await client.create_redesign_job(
                company_id="c1", job_id="j1", status="done", tier="free"
            )
            assert result["id"] == "rj1"


class TestCreatePerson:
    @pytest.mark.asyncio
    async def test_creates_person_linked_to_company(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": {"createPerson": {"id": "p1"}}}
            result = await client.create_person(
                email="test@example.com", company_id="c1",
                first_name="John", last_name="Doe"
            )
            assert result["id"] == "p1"

    @pytest.mark.asyncio
    async def test_creates_person_without_company(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": {"createPerson": {"id": "p2"}}}
            result = await client.create_person(
                email="test@example.com", company_id=None,
                first_name="Jane", last_name="Doe"
            )
            assert result["id"] == "p2"


class TestFeatureFlag:
    @pytest.mark.asyncio
    async def test_noop_client_does_nothing(self):
        from sastaspace.twenty_sync import NoopTwentyClient
        client = NoopTwentyClient()
        result = await client.upsert_company("example.com", name="Test")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_client_returns_noop_when_disabled(self):
        from sastaspace.twenty_sync import get_twenty_client, NoopTwentyClient
        client = get_twenty_client(twenty_url="", twenty_api_key="")
        assert isinstance(client, NoopTwentyClient)

    @pytest.mark.asyncio
    async def test_get_client_returns_real_when_configured(self):
        client = get_twenty_client(twenty_url="http://twenty:3000/rest", twenty_api_key="key")
        assert isinstance(client, TwentyClient)


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_api_error_returns_none(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = Exception("Connection refused")
            result = await client.upsert_company("example.com", name="Test")
            assert result is None
```

- [ ] **Step 2: Run tests — should fail (ImportError)**

Run: `uv run pytest tests/test_twenty_sync.py -v`

- [ ] **Step 3: Implement TwentyClient**

```python
# sastaspace/twenty_sync.py
"""Twenty CRM sync client — async wrapper around Twenty REST API."""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class TwentyClient:
    """Async client for Twenty CRM REST API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def _request(
        self, method: str, path: str, json: dict | None = None, params: dict | None = None
    ) -> dict:
        """Make an authenticated request to Twenty API."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(
                method,
                f"{self.base_url}{path}",
                json=json,
                params=params,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def find_company_by_domain(self, domain: str) -> dict | None:
        """Find a company by custom domain field."""
        try:
            data = await self._request(
                "GET", "/companies",
                params={"filter": f'{{"domain":{{"eq":"{domain}"}}}}'},
            )
            companies = data.get("data", {}).get("companies", [])
            return companies[0] if companies else None
        except Exception as e:
            logger.warning("Twenty find_company failed: %s", e)
            return None

    async def upsert_company(self, domain: str, **fields) -> dict | None:
        """Find company by domain, update if exists, create if not."""
        try:
            existing = await self.find_company_by_domain(domain)
            if existing:
                data = await self._request(
                    "PATCH", f"/companies/{existing['id']}", json=fields
                )
                return data.get("data", {}).get("updateCompany", existing)
            else:
                fields["domain"] = domain
                data = await self._request("POST", "/companies", json=fields)
                return data.get("data", {}).get("createCompany")
        except Exception as e:
            logger.warning("Twenty upsert_company failed for %s: %s", domain, e)
            return None

    async def create_redesign_job(self, company_id: str, **fields) -> dict | None:
        """Create a RedesignJob record linked to a company."""
        try:
            fields["companyId"] = company_id
            data = await self._request("POST", "/redesignJobs", json=fields)
            return data.get("data", {}).get("createRedesignJob")
        except Exception as e:
            logger.warning("Twenty create_redesign_job failed: %s", e)
            return None

    async def update_redesign_job(self, record_id: str, **fields) -> dict | None:
        """Update fields on an existing RedesignJob."""
        try:
            data = await self._request("PATCH", f"/redesignJobs/{record_id}", json=fields)
            return data.get("data", {}).get("updateRedesignJob")
        except Exception as e:
            logger.warning("Twenty update_redesign_job failed: %s", e)
            return None

    async def find_redesign_job(self, job_id: str) -> dict | None:
        """Find a RedesignJob by SastaSpace job ID."""
        try:
            data = await self._request(
                "GET", "/redesignJobs",
                params={"filter": f'{{"jobId":{{"eq":"{job_id}"}}}}'},
            )
            jobs = data.get("data", {}).get("redesignJobs", [])
            return jobs[0] if jobs else None
        except Exception as e:
            logger.warning("Twenty find_redesign_job failed: %s", e)
            return None

    async def create_person(
        self, email: str, company_id: str | None, first_name: str, last_name: str, **fields
    ) -> dict | None:
        """Create a Person record, optionally linked to a company."""
        try:
            body = {"email": email, "firstName": first_name, "lastName": last_name, **fields}
            if company_id:
                body["companyId"] = company_id
            data = await self._request("POST", "/people", json=body)
            return data.get("data", {}).get("createPerson")
        except Exception as e:
            logger.warning("Twenty create_person failed: %s", e)
            return None

    async def create_note(self, person_id: str, body: str) -> dict | None:
        """Create a Note linked to a person."""
        try:
            data = await self._request(
                "POST", "/notes", json={"body": body, "personId": person_id}
            )
            return data.get("data", {}).get("createNote")
        except Exception as e:
            logger.warning("Twenty create_note failed: %s", e)
            return None


class NoopTwentyClient:
    """No-op client used when Twenty integration is disabled."""

    async def upsert_company(self, *a, **kw):
        return None

    async def create_redesign_job(self, *a, **kw):
        return None

    async def update_redesign_job(self, *a, **kw):
        return None

    async def find_redesign_job(self, *a, **kw):
        return None

    async def find_company_by_domain(self, *a, **kw):
        return None

    async def create_person(self, *a, **kw):
        return None

    async def create_note(self, *a, **kw):
        return None


def get_twenty_client(twenty_url: str, twenty_api_key: str) -> TwentyClient | NoopTwentyClient:
    """Factory — returns NoopTwentyClient when twenty_url is empty."""
    if not twenty_url:
        return NoopTwentyClient()
    return TwentyClient(base_url=twenty_url, api_key=twenty_api_key)
```

- [ ] **Step 4: Run tests — should pass**

Run: `uv run pytest tests/test_twenty_sync.py -v`

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check sastaspace/twenty_sync.py tests/test_twenty_sync.py
uv run ruff format sastaspace/twenty_sync.py tests/test_twenty_sync.py
git add sastaspace/twenty_sync.py tests/test_twenty_sync.py
git commit -m "feat: add TwentyClient async API wrapper with NoopTwentyClient fallback"
```

---

## Task 4: Push Sync — Job Completion → Twenty

**Files:**
- Modify: `sastaspace/jobs.py` (after deploy step in `redesign_handler`, around line 500+)

- [ ] **Step 1: Add Twenty sync after job completion in redesign_handler()**

In `sastaspace/jobs.py`, after the successful deploy step (after `register_site()` call), add:

```python
    # Sync to Twenty CRM (fire-and-forget — failure doesn't affect pipeline)
    from sastaspace.twenty_sync import get_twenty_client
    twenty = get_twenty_client(settings.twenty_url, settings.twenty_api_key)

    try:
        # Upsert company from business profile
        bp = getattr(enhanced_result, "business_profile", None) if enhanced_result else None
        company_name = bp.business_name if bp and bp.business_name != "unknown" else crawl_result.title
        industry = bp.industry if bp and bp.industry != "unknown" else ""

        from sastaspace.urls import extract_domain
        domain = extract_domain(url)

        company = await twenty.upsert_company(
            domain,
            name=company_name,
            lastRedesignStatus="done",
            lastRedesignTier=tier,
            lastRedesignUrl=f"/{result.subdomain}/",
            industry=industry,
            lastRedesignedAt=datetime.now(UTC).isoformat(),
        )
        if company:
            await twenty.create_redesign_job(
                company_id=company["id"],
                jobId=job_id,
                status="done",
                tier=tier,
                previewUrl=f"/{result.subdomain}/",
                subdomain=result.subdomain,
                pagesFound=len(getattr(enhanced_result, "internal_pages", [])),
                assetsDownloaded=len(enhanced_result.assets.assets) if enhanced_result and hasattr(enhanced_result, "assets") else 0,
                businessIndustry=industry,
                createdAt=datetime.now(UTC).isoformat(),
                completedAt=datetime.now(UTC).isoformat(),
            )
    except Exception as e:
        logger.warning("Twenty sync failed for job %s: %s", job_id, e)
```

- [ ] **Step 2: Add sync on job failure**

In the error/failure path of `redesign_handler()` (where `status=JobStatus.FAILED` is set), add:

```python
    # Sync failure to Twenty CRM
    try:
        from sastaspace.twenty_sync import get_twenty_client
        from sastaspace.urls import extract_domain
        twenty = get_twenty_client(settings.twenty_url, settings.twenty_api_key)
        domain = extract_domain(url)
        company = await twenty.upsert_company(domain, name=crawl_result.title or domain, lastRedesignStatus="failed")
        if company:
            await twenty.create_redesign_job(
                company_id=company["id"], jobId=job_id, status="failed", tier=tier,
                errorMessage=str(error_msg)[:500],
                createdAt=datetime.now(UTC).isoformat(),
            )
    except Exception:
        pass  # Never fail the failure handler
```

- [ ] **Step 3: Run existing job tests**

Run: `uv run pytest tests/test_jobs.py tests/test_jobs_handler.py -v --tb=short`
Expected: All pass (Twenty sync is try/except, won't break existing tests)

- [ ] **Step 4: Commit**

```bash
git add sastaspace/jobs.py
git commit -m "feat: push job completion/failure data to Twenty CRM"
```

---

## Task 5: Webhook Endpoint — Admin Actions

**Files:**
- Create: `sastaspace/admin.py` (admin helper functions)
- Modify: `sastaspace/server.py` (add webhook route inside `make_app()`)
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write tests for admin helpers**

```python
# tests/test_admin.py
"""Tests for admin operations and webhook handling."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, patch

import pytest


class TestWebhookVerification:
    def test_valid_signature_passes(self):
        from sastaspace.admin import verify_webhook_signature
        secret = "test-secret"
        body = b'{"event":"redesignJob.updated"}'
        timestamp = str(int(time.time()))
        sig = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        assert verify_webhook_signature(body, sig, timestamp, secret) is True

    def test_invalid_signature_fails(self):
        from sastaspace.admin import verify_webhook_signature
        assert verify_webhook_signature(b"body", "badsig", str(int(time.time())), "secret") is False

    def test_expired_timestamp_fails(self):
        from sastaspace.admin import verify_webhook_signature
        old_timestamp = str(int(time.time()) - 600)  # 10 min ago
        body = b"body"
        sig = hmac.new(b"secret", old_timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        assert verify_webhook_signature(body, sig, old_timestamp, "secret") is False


class TestDeleteSiteFiles:
    @pytest.mark.asyncio
    async def test_deletes_site_directory(self, tmp_path):
        from sastaspace.admin import delete_site_files
        site_dir = tmp_path / "sites" / "test-site"
        site_dir.mkdir(parents=True)
        (site_dir / "index.html").write_text("<html></html>")
        (site_dir / "metadata.json").write_text("{}")
        assets_dir = site_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "logo.png").write_bytes(b"fake")

        await delete_site_files("test-site", sites_dir=tmp_path / "sites")
        assert not site_dir.exists()

    @pytest.mark.asyncio
    async def test_noop_on_missing_site(self, tmp_path):
        from sastaspace.admin import delete_site_files
        # Should not raise
        await delete_site_files("nonexistent", sites_dir=tmp_path / "sites")


class TestGetOriginalUrl:
    @pytest.mark.asyncio
    async def test_returns_url_from_db(self):
        from sastaspace.admin import get_original_url_from_db
        with patch("sastaspace.admin.find_site_by_subdomain", new_callable=AsyncMock) as mock:
            mock.return_value = {"original_url": "https://example.com"}
            url = await get_original_url_from_db("example-com")
            assert url == "https://example.com"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        from sastaspace.admin import get_original_url_from_db
        with patch("sastaspace.admin.find_site_by_subdomain", new_callable=AsyncMock) as mock:
            mock.return_value = None
            url = await get_original_url_from_db("nonexistent")
            assert url is None
```

- [ ] **Step 2: Run tests — should fail**

- [ ] **Step 3: Implement admin helpers**

```python
# sastaspace/admin.py
"""Admin operations — site management and webhook handling."""
from __future__ import annotations

import hashlib
import hmac
import logging
import shutil
import time
from pathlib import Path

from sastaspace.database import _get_db

logger = logging.getLogger(__name__)


def verify_webhook_signature(
    body: bytes, signature: str, timestamp: str, secret: str, max_age_seconds: int = 300
) -> bool:
    """Verify Twenty webhook HMAC SHA256 signature with replay protection."""
    # Check timestamp age
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > max_age_seconds:
            return False
    except (ValueError, TypeError):
        return False

    # Verify HMAC
    expected = hmac.new(
        secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def delete_site_files(subdomain: str, sites_dir: Path) -> None:
    """Delete site files from disk. Idempotent — no-op if already deleted."""
    site_dir = sites_dir / subdomain
    if site_dir.exists():
        shutil.rmtree(site_dir)
        logger.info("Deleted site files: %s", subdomain)


async def find_site_by_subdomain(subdomain: str) -> dict | None:
    """Find a site record in MongoDB by subdomain."""
    db = _get_db()
    doc = await db["sites"].find_one({"subdomain": subdomain})
    if doc:
        doc.pop("_id", None)
    return doc


async def get_original_url_from_db(subdomain: str) -> str | None:
    """Read original URL from MongoDB site record."""
    site = await find_site_by_subdomain(subdomain)
    return site.get("original_url") if site else None


async def delete_site_db_record(subdomain: str) -> None:
    """Remove site record from MongoDB."""
    db = _get_db()
    await db["sites"].delete_one({"subdomain": subdomain})
    logger.info("Deleted site DB record: %s", subdomain)
```

- [ ] **Step 4: Add webhook route to server.py**

Inside `make_app()` in `sastaspace/server.py`, add after the existing routes (before the `/{subdomain}/` catch-all routes):

```python
    @app.post("/webhooks/twenty")
    async def twenty_webhook(request: Request):
        """Handle admin actions from Twenty CRM via webhooks."""
        import hashlib

        from sastaspace.admin import (
            delete_site_db_record,
            delete_site_files,
            get_original_url_from_db,
            verify_webhook_signature,
        )
        from sastaspace.twenty_sync import get_twenty_client

        if not settings.twenty_webhook_secret:
            return Response(status_code=404)

        body = await request.body()
        signature = request.headers.get("X-Twenty-Webhook-Signature", "")
        timestamp = request.headers.get("X-Twenty-Webhook-Timestamp", "")

        if not verify_webhook_signature(body, signature, timestamp, settings.twenty_webhook_secret):
            return Response(status_code=401)

        # Redis dedup — skip duplicate webhooks
        # SET NX returns True if key was newly created (first time), None if it already existed
        payload_hash = hashlib.sha256(body).hexdigest()
        if svc and svc._redis:
            is_new = await svc._redis.set(
                f"webhook:twenty:{payload_hash}", "1", nx=True, ex=600
            )
            if not is_new:  # None = key already existed = duplicate webhook
                return Response(status_code=200, content="duplicate")

        payload = json.loads(body)
        data = payload.get("data", {})
        action = data.get("adminAction")
        subdomain = data.get("subdomain", "")
        record_id = data.get("id", "")

        twenty = get_twenty_client(settings.twenty_url, settings.twenty_api_key)

        if action == "delete":
            await delete_site_files(subdomain, settings.sites_dir)
            await delete_site_db_record(subdomain)
            await twenty.update_redesign_job(record_id, status="deleted", adminAction="none")
            return Response(status_code=200, content="deleted")

        elif action == "reprocess":
            url = await get_original_url_from_db(subdomain)
            if not url:
                await twenty.update_redesign_job(
                    record_id, adminAction="none", errorMessage="Original URL not found"
                )
                return Response(status_code=404, content="URL not found")
            # Enqueue new job BEFORE deleting files
            if svc:
                new_job_id = await svc.enqueue(url, "admin", tier=data.get("tier", "free"))
            else:
                return Response(status_code=503, content="Job service unavailable")
            await delete_site_files(subdomain, settings.sites_dir)
            await twenty.update_redesign_job(
                record_id, status="queued", jobId=new_job_id, adminAction="none"
            )
            return Response(status_code=200, content="reprocessing")

        return Response(status_code=400, content="Unknown action")
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_admin.py -v`

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check sastaspace/admin.py tests/test_admin.py
uv run ruff format sastaspace/admin.py tests/test_admin.py
git add sastaspace/admin.py sastaspace/server.py tests/test_admin.py
git commit -m "feat: add /webhooks/twenty endpoint with HMAC verification and Redis dedup"
```

---

## Task 6: Admin Sync + Sites Endpoints

**Files:**
- Modify: `sastaspace/server.py` (add routes inside `make_app()`)
- Test: `tests/test_admin.py` (extend)

- [ ] **Step 1: Add `/admin/sync` and `/admin/sites` routes**

Inside `make_app()` in `sastaspace/server.py`, add before the catch-all routes:

```python
    @app.get("/admin/sites")
    async def admin_list_sites(request: Request):
        """List all deployed sites for Twenty reconciliation."""
        auth = request.headers.get("Authorization", "")
        if not settings.twenty_admin_key or auth != f"Bearer {settings.twenty_admin_key}":
            return Response(status_code=401)
        sites = await list_sites(limit=1000)
        return {"sites": sites}

    @app.get("/admin/sync")
    async def admin_sync(request: Request):
        """Reconcile missed push events — sync recent jobs to Twenty."""
        auth = request.headers.get("Authorization", "")
        if not settings.twenty_admin_key or auth != f"Bearer {settings.twenty_admin_key}":
            return Response(status_code=401)

        from sastaspace.twenty_sync import NoopTwentyClient, get_twenty_client
        from sastaspace.urls import extract_domain

        twenty = get_twenty_client(settings.twenty_url, settings.twenty_api_key)
        if isinstance(twenty, NoopTwentyClient):
            return {"synced": 0, "message": "Twenty integration disabled"}

        # Get recent completed/failed jobs from last 24h
        recent_jobs = await list_jobs(limit=100, status="done")
        synced = 0
        already_exists = 0
        errors = 0

        for job in recent_jobs:
            job_id = job.get("id", "")
            try:
                existing = await twenty.find_redesign_job(job_id)
                if existing:
                    already_exists += 1
                    continue
                domain = extract_domain(job.get("url", ""))
                company = await twenty.upsert_company(domain, name=job.get("site_title", domain))
                if company:
                    await twenty.create_redesign_job(
                        company_id=company["id"],
                        jobId=job_id,
                        status=job.get("status", "done"),
                        tier=job.get("tier", "free"),
                        subdomain=job.get("subdomain", ""),
                    )
                    synced += 1
            except Exception as e:
                logger.warning("Sync failed for job %s: %s", job_id, e)
                errors += 1

        # Update totalRedesigns aggregate counts on companies
        # (avoids TOCTOU race in real-time push — this is the authoritative count)
        from sastaspace.database import _get_db
        db = _get_db()
        pipeline = [
            {"$group": {"_id": "$original_url", "count": {"$sum": 1}}},
        ]
        async for doc in db["sites"].aggregate(pipeline):
            domain = extract_domain(doc["_id"]) if doc["_id"] else None
            if domain:
                company = await twenty.find_company_by_domain(domain)
                if company:
                    await twenty.upsert_company(domain, totalRedesigns=doc["count"])

        return {"synced": synced, "already_exists": already_exists, "errors": errors}
```

- [ ] **Step 2: Run existing server tests**

Run: `uv run pytest tests/test_server.py -v --tb=short`

- [ ] **Step 3: Commit**

```bash
git add sastaspace/server.py
git commit -m "feat: add /admin/sync and /admin/sites endpoints for Twenty reconciliation"
```

---

## Task 7: Contact Form → Twenty Person

**Files:**
- Modify: `sastaspace/server.py` (add `/twenty/person` route)
- Modify: `web/src/app/api/contact/route.ts` (add Twenty sync call)

- [ ] **Step 1: Add `/twenty/person` endpoint to server.py**

Inside `make_app()`:

```python
    @app.post("/twenty/person")
    async def create_twenty_person(request: Request):
        """Create a Person in Twenty CRM from contact form submission."""
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

            # Split name
            parts = name.split(None, 1)
            first_name = parts[0] if parts else ""
            last_name = parts[1] if len(parts) > 1 else ""

            # Find or create company
            company_id = None
            if domain:
                company = await twenty.find_company_by_domain(domain)
                if not company:
                    company = await twenty.upsert_company(domain, name=domain)
                if company:
                    company_id = company.get("id")

            # Create person
            person = await twenty.create_person(
                email=email, company_id=company_id,
                first_name=first_name, last_name=last_name,
            )

            # Create note with message
            if person and message:
                await twenty.create_note(person["id"], message)

            return {"ok": True}
        except Exception as e:
            logger.warning("Twenty person creation failed: %s", e)
            return {"ok": True}  # Don't reveal failures to frontend
```

- [ ] **Step 2: Update contact form route**

In `web/src/app/api/contact/route.ts`, add after the Resend email call (around line 70), before the success response:

```typescript
    // Sync to Twenty CRM — strict 2s timeout
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2000);
      await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/twenty/person`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            email,
            message,
            domain: subdomain || null,
          }),
          signal: controller.signal,
        }
      );
      clearTimeout(timeout);
    } catch {
      // Twenty sync failure doesn't block the contact form
    }
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_server.py -v --tb=short`
Run: `cd web && npm test -- --run`

- [ ] **Step 4: Commit**

```bash
git add sastaspace/server.py web/src/app/api/contact/route.ts
git commit -m "feat: contact form creates Person in Twenty CRM with 2s timeout"
```

---

## Task 8: Twenty K8s Deployment Manifests

**Files:**
- Create: `k8s/twenty/namespace.yaml`
- Create: `k8s/twenty/server.yaml`
- Create: `k8s/twenty/worker.yaml`
- Create: `k8s/twenty/postgres.yaml`
- Create: `k8s/twenty/redis.yaml`
- Create: `k8s/twenty/ingress.yaml`
- Create: `k8s/twenty/secrets.yaml`

- [ ] **Step 1: Create namespace**

```yaml
# k8s/twenty/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: twenty
```

- [ ] **Step 2: Create secrets template**

```yaml
# k8s/twenty/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: twenty-env
  namespace: twenty
type: Opaque
stringData:
  APP_SECRET: "CHANGE_ME_GENERATE_A_RANDOM_STRING"
  PG_DATABASE_URL: "postgres://twenty:twenty@twenty-postgres:5432/twenty"
  REDIS_URL: "redis://twenty-redis:6379"
```

- [ ] **Step 3: Create PostgreSQL deployment**

```yaml
# k8s/twenty/postgres.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twenty-postgres
  namespace: twenty
spec:
  replicas: 1
  selector:
    matchLabels:
      app: twenty-postgres
  template:
    metadata:
      labels:
        app: twenty-postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_USER
          value: "twenty"
        - name: POSTGRES_PASSWORD
          value: "twenty"
        - name: POSTGRES_DB
          value: "twenty"
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: twenty-postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: twenty-postgres
  namespace: twenty
spec:
  selector:
    app: twenty-postgres
  ports:
  - port: 5432
    targetPort: 5432
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: twenty-postgres-pvc
  namespace: twenty
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

- [ ] **Step 4: Create Redis deployment**

```yaml
# k8s/twenty/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twenty-redis
  namespace: twenty
spec:
  replicas: 1
  selector:
    matchLabels:
      app: twenty-redis
  template:
    metadata:
      labels:
        app: twenty-redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "128Mi"
            cpu: "50m"
          limits:
            memory: "512Mi"
            cpu: "250m"
---
apiVersion: v1
kind: Service
metadata:
  name: twenty-redis
  namespace: twenty
spec:
  selector:
    app: twenty-redis
  ports:
  - port: 6379
    targetPort: 6379
```

- [ ] **Step 5: Create Twenty server deployment**

```yaml
# k8s/twenty/server.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twenty-server
  namespace: twenty
spec:
  replicas: 1
  selector:
    matchLabels:
      app: twenty-server
  template:
    metadata:
      labels:
        app: twenty-server
    spec:
      containers:
      - name: server
        image: twentycrm/twenty:latest
        ports:
        - containerPort: 3000
        envFrom:
        - secretRef:
            name: twenty-env
        env:
        - name: SERVER_URL
          value: "https://crm.sastaspace.com"
        - name: STORAGE_TYPE
          value: "local"
        - name: STORAGE_LOCAL_PATH
          value: "/app/storage"
        volumeMounts:
        - name: storage
          mountPath: /app/storage
        resources:
          requests:
            memory: "1Gi"
            cpu: "200m"
          limits:
            memory: "4Gi"
            cpu: "1000m"
        readinessProbe:
          httpGet:
            path: /healthz
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
      volumes:
      - name: storage
        emptyDir:
          sizeLimit: 5Gi
---
apiVersion: v1
kind: Service
metadata:
  name: twenty-server
  namespace: twenty
spec:
  selector:
    app: twenty-server
  ports:
  - port: 3000
    targetPort: 3000
```

- [ ] **Step 6: Create Twenty worker deployment**

```yaml
# k8s/twenty/worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twenty-worker
  namespace: twenty
spec:
  replicas: 1
  selector:
    matchLabels:
      app: twenty-worker
  template:
    metadata:
      labels:
        app: twenty-worker
    spec:
      containers:
      - name: worker
        image: twentycrm/twenty:latest
        command: ["yarn", "worker:prod"]
        envFrom:
        - secretRef:
            name: twenty-env
        resources:
          requests:
            memory: "512Mi"
            cpu: "100m"
          limits:
            memory: "2Gi"
            cpu: "500m"
```

- [ ] **Step 7: Create ingress**

```yaml
# k8s/twenty/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: twenty
  namespace: twenty
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  ingressClassName: public
  rules:
  - host: crm.sastaspace.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: twenty-server
            port:
              number: 3000
```

- [ ] **Step 8: Commit all manifests**

```bash
git add k8s/twenty/
git commit -m "infra: add Twenty CRM k8s deployment (server, worker, postgres, redis, ingress)"
```

---

## Task 9: Makefile + Cloudflare Tunnel

**Files:**
- Modify: `Makefile` (add twenty targets)

- [ ] **Step 1: Add Twenty deploy targets**

Add to `Makefile`:

```makefile
# --- Twenty CRM ---

deploy-twenty: ## Deploy Twenty CRM to k8s
	ssh $(REMOTE_USER)@$(REMOTE_HOST) "\
		sudo microk8s kubectl apply -f - < k8s/twenty/namespace.yaml && \
		sudo microk8s kubectl apply -f k8s/twenty/"

twenty-status: ## Show Twenty pod/svc/ingress status
	ssh $(REMOTE_USER)@$(REMOTE_HOST) "sudo microk8s kubectl get pods,svc,ingress -n twenty"

twenty-logs: ## Tail Twenty server + worker logs
	ssh $(REMOTE_USER)@$(REMOTE_HOST) "\
		sudo microk8s kubectl logs -n twenty -l app=twenty-server --tail=50 -f &\
		sudo microk8s kubectl logs -n twenty -l app=twenty-worker --tail=50 -f"

twenty-setup: ## First-time Twenty setup (create secrets, apply, wait)
	@echo "1. Edit k8s/twenty/secrets.yaml with real values"
	@echo "2. Run: make deploy-twenty"
	@echo "3. Wait for pods: make twenty-status"
	@echo "4. Access: https://crm.sastaspace.com"
```

- [ ] **Step 2: Add `crm.sastaspace.com` to Cloudflare tunnel**

This is a manual step documented in the Makefile target. The existing tunnel config routes all subdomains to `localhost:80` via `*.sastaspace.com` CNAME. The ingress rule in `k8s/twenty/ingress.yaml` handles the `Host: crm.sastaspace.com` header. No tunnel config change needed — the wildcard CNAME already covers it.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "feat: add Makefile targets for Twenty CRM deployment"
```

---

## Task 10: Docker Compose + Integration Test

**Files:**
- Modify: `docker-compose.yml` (add Twenty env vars to backend)
- Create: `tests/test_twenty_integration.py`

- [ ] **Step 1: Add Twenty env vars to docker-compose.yml**

In the `backend` service `environment` section:
```yaml
      TWENTY_URL: ""
      TWENTY_API_KEY: ""
      TWENTY_WEBHOOK_SECRET: ""
      TWENTY_ADMIN_KEY: ""
```

- [ ] **Step 2: Write integration test**

```python
# tests/test_twenty_integration.py
"""Integration tests for Twenty CRM sync flow. All HTTP calls mocked."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sastaspace.twenty_sync import TwentyClient, get_twenty_client, NoopTwentyClient


class TestFullSyncFlow:
    @pytest.mark.asyncio
    async def test_job_completion_creates_company_and_job(self):
        """Simulates the push sync that happens after a redesign job completes."""
        client = TwentyClient(base_url="http://twenty:3000/rest", api_key="test")

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            # upsert_company: search → not found → create
            # create_redesign_job: create
            mock_req.side_effect = [
                {"data": {"companies": []}},  # search
                {"data": {"createCompany": {"id": "c1"}}},  # create
                {"data": {"createRedesignJob": {"id": "rj1"}}},  # create job
            ]

            company = await client.upsert_company(
                "example.com", name="Example Corp", lastRedesignStatus="done"
            )
            assert company["id"] == "c1"

            job = await client.create_redesign_job(
                company_id="c1", jobId="j1", status="done", tier="free"
            )
            assert job["id"] == "rj1"

    @pytest.mark.asyncio
    async def test_contact_form_creates_person_with_note(self):
        """Simulates person creation from contact form."""
        client = TwentyClient(base_url="http://twenty:3000/rest", api_key="test")

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = [
                {"data": {"companies": [{"id": "c1"}]}},  # find company
                {"data": {"createPerson": {"id": "p1"}}},  # create person
                {"data": {"createNote": {"id": "n1"}}},  # create note
            ]

            company = await client.find_company_by_domain("example.com")
            person = await client.create_person(
                email="john@example.com", company_id=company["id"],
                first_name="John", last_name="Doe"
            )
            note = await client.create_note(person["id"], "I'd like to hire you!")

            assert person["id"] == "p1"
            assert note["id"] == "n1"

    @pytest.mark.asyncio
    async def test_noop_client_safe_for_all_operations(self):
        """NoopTwentyClient returns None for everything without errors."""
        client = NoopTwentyClient()
        assert await client.upsert_company("x.com") is None
        assert await client.create_redesign_job("c1") is None
        assert await client.create_person("a@b.com", None, "A", "B") is None
        assert await client.create_note("p1", "msg") is None
        assert await client.find_company_by_domain("x.com") is None
        assert await client.find_redesign_job("j1") is None
        assert await client.update_redesign_job("r1") is None
```

- [ ] **Step 3: Run all tests**

Run: `uv run pytest tests/test_twenty_sync.py tests/test_twenty_integration.py tests/test_admin.py -v`

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/ -v --tb=short`

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check sastaspace/ tests/ && uv run ruff format sastaspace/ tests/
git add docker-compose.yml tests/test_twenty_integration.py
git commit -m "test: add Twenty CRM integration tests + docker-compose env vars"
```

---

## Execution Order Summary

| Task | What | Dependencies | Parallelizable |
|------|------|-------------|----------------|
| 1 | httpx dependency | None | Wave 1 |
| 2 | Config fields | None | Wave 1 |
| 3 | TwentyClient | Task 1 | Wave 2 |
| 4 | Push sync (jobs.py) | Task 2, 3 | Wave 3 |
| 5 | Webhook endpoint | Task 2, 3 | Wave 3 |
| 6 | Admin sync endpoints | Task 3, 5 | Wave 4 |
| 7 | Contact form integration | Task 3 | Wave 3 |
| 8 | K8s manifests | None | Wave 1 |
| 9 | Makefile + tunnel | Task 8 | Wave 2 |
| 10 | Integration test | Tasks 3-7 | Wave 5 |

**Wave 1:** Tasks 1, 2, 8 (parallel)
**Wave 2:** Tasks 3, 9 (parallel)
**Wave 3:** Tasks 4, 5, 7 (parallel)
**Wave 4:** Task 6
**Wave 5:** Task 10
