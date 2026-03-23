# sastaspace/routes/admin.py
"""Admin, webhook, and Twenty CRM sync endpoints."""

from __future__ import annotations

import hashlib
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from sastaspace.admin import (
    delete_site_db_record,
    delete_site_files,
    get_original_url_from_db,
    verify_webhook_signature,
)
from sastaspace.config import Settings
from sastaspace.database import list_jobs, list_sites
from sastaspace.deployer import derive_subdomain
from sastaspace.twenty_sync import NoopTwentyClient, get_twenty_client
from sastaspace.urls import extract_domain

logger = logging.getLogger(__name__)


def create_admin_router(settings: Settings, svc_ref: list) -> APIRouter:
    """Create the admin/webhook router with injected dependencies."""
    r = APIRouter()

    @r.post("/twenty/person", response_model=None)
    async def create_twenty_person(request: Request) -> JSONResponse:
        twenty = get_twenty_client(settings.twenty_url, settings.twenty_api_key)
        try:
            body = await request.json()
            name = body.get("name", "").strip()
            email = body.get("email", "").strip()
            message = body.get("message", "")
            domain = body.get("domain")

            if not email:
                return JSONResponse(status_code=400, content={"error": "Email required"})

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

            return JSONResponse(content={"ok": True})
        except (ValueError, KeyError, TypeError, OSError) as e:
            logger.warning("Twenty person creation failed: %s", e)
            return JSONResponse(content={"ok": True})  # Don't reveal failures

    @r.post("/webhooks/twenty", response_model=None)
    async def twenty_webhook(request: Request) -> Response:
        """Handle admin actions from Twenty CRM via webhooks."""
        if not settings.twenty_webhook_secret:
            return Response(status_code=404)

        body = await request.body()
        signature = request.headers.get("X-Twenty-Webhook-Signature", "")
        timestamp = request.headers.get("X-Twenty-Webhook-Timestamp", "")

        if not verify_webhook_signature(body, signature, timestamp, settings.twenty_webhook_secret):
            return Response(status_code=401)

        # Redis dedup -- skip duplicate webhooks
        svc = svc_ref[0] if svc_ref else None
        payload_hash = hashlib.sha256(body).hexdigest()
        if svc and svc._redis:
            is_new = await svc._redis.set(f"webhook:twenty:{payload_hash}", "1", nx=True, ex=600)
            if not is_new:
                return Response(status_code=200, content="duplicate")

        payload = json.loads(body)

        # --- Handle Twenty native CRUD events (company.deleted, etc.) ---
        event_name = payload.get("eventName", "")
        if event_name == "company.deleted":
            record = payload.get("record", {})
            domain_url = ""
            domain_name = record.get("domainName", {})
            if isinstance(domain_name, dict):
                domain_url = domain_name.get("primaryLinkUrl", "")
            if domain_url:
                subdomain = derive_subdomain(domain_url)
                logger.info("Twenty company.deleted -> subdomain=%s url=%s", subdomain, domain_url)
                await delete_site_files(subdomain, settings.sites_dir)
                await delete_site_db_record(subdomain)
                return Response(status_code=200, content="deleted")
            logger.warning("company.deleted but no domainName URL in record")
            return Response(status_code=200, content="no-url")

        # --- Handle custom admin actions (adminAction field) ---
        data = payload.get("data", {})
        action = data.get("adminAction")
        subdomain = data.get("subdomain", "")
        if action == "delete":
            await delete_site_files(subdomain, settings.sites_dir)
            await delete_site_db_record(subdomain)
            return Response(status_code=200, content="deleted")

        elif action == "reprocess":
            url = await get_original_url_from_db(subdomain)
            if not url:
                return Response(status_code=404, content="URL not found")
            if svc:
                await svc.enqueue(url, "admin", tier=data.get("tier", "free"))
            else:
                return Response(status_code=503, content="Job service unavailable")
            await delete_site_files(subdomain, settings.sites_dir)
            return Response(status_code=200, content="reprocessing")

        return Response(status_code=200, content="ignored")

    @r.get("/admin/sites", response_model=None)
    async def admin_list_sites(request: Request) -> JSONResponse | Response:
        """List all deployed sites for Twenty reconciliation."""
        auth = request.headers.get("Authorization", "")
        if not settings.twenty_admin_key or auth != f"Bearer {settings.twenty_admin_key}":
            return Response(status_code=401)
        sites = await list_sites(limit=1000)
        return JSONResponse(content={"sites": sites})

    @r.get("/admin/sync", response_model=None)
    async def admin_sync(request: Request) -> JSONResponse | Response:
        """Reconcile missed push events -- sync recent jobs to Twenty."""
        auth = request.headers.get("Authorization", "")
        if not settings.twenty_admin_key or auth != f"Bearer {settings.twenty_admin_key}":
            return Response(status_code=401)

        twenty = get_twenty_client(settings.twenty_url, settings.twenty_api_key)
        if isinstance(twenty, NoopTwentyClient):
            return JSONResponse(content={"synced": 0, "message": "Twenty integration disabled"})

        recent_jobs = await list_jobs(limit=100, status="done")
        synced = 0
        already_exists = 0
        errors = 0

        for job in recent_jobs:
            job_id = job.get("id", "")
            try:
                domain = extract_domain(job.get("url", ""))
                company = await twenty.upsert_company(domain, name=job.get("site_title", domain))
                if company:
                    synced += 1
            except (ValueError, KeyError, TypeError, OSError) as e:
                logger.warning("Sync failed for job %s: %s", job_id, e)
                errors += 1

        return JSONResponse(
            content={"synced": synced, "already_exists": already_exists, "errors": errors}
        )

    return r
