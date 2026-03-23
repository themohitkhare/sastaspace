# sastaspace/routes/admin.py
"""Admin, webhook, and EspoCRM sync endpoints."""

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
from sastaspace.espocrm_sync import NoopEspoCRMClient, get_espocrm_client
from sastaspace.urls import extract_domain

logger = logging.getLogger(__name__)


def create_admin_router(settings: Settings, svc_ref: list) -> APIRouter:
    """Create the admin/webhook router with injected dependencies."""
    r = APIRouter()

    @r.post("/crm/lead", response_model=None)
    async def create_espocrm_lead(request: Request) -> JSONResponse:
        """Create or update a lead in EspoCRM from a contact form submission."""
        espo = get_espocrm_client(settings.espocrm_url, settings.espocrm_api_key)
        try:
            body = await request.json()
            name = body.get("name", "").strip()
            email = body.get("email", "").strip()
            message = body.get("message", "")
            domain = body.get("domain", "")

            if not email:
                return JSONResponse(status_code=400, content={"error": "Email required"})

            parts = name.split(None, 1)
            first_name = parts[0] if parts else ""
            last_name = parts[1] if len(parts) > 1 else ""

            website = f"https://{domain}" if domain else ""
            await espo.create_or_update_lead(
                first_name=first_name,
                last_name=last_name,
                email=email,
                website=website,
                description=message,
            )

            return JSONResponse(content={"ok": True})
        except (ValueError, KeyError, TypeError, OSError) as e:
            logger.warning("EspoCRM lead creation failed: %s", e)
            return JSONResponse(content={"ok": True})  # Don't reveal failures

    @r.post("/webhooks/crm", response_model=None)
    async def crm_webhook(request: Request) -> Response:
        """Handle admin actions from EspoCRM (or any CRM) via webhooks."""
        if not settings.twenty_webhook_secret:
            return Response(status_code=404)

        body = await request.body()
        signature = request.headers.get("X-Webhook-Signature", "")
        timestamp = request.headers.get("X-Webhook-Timestamp", "")

        if not verify_webhook_signature(body, signature, timestamp, settings.twenty_webhook_secret):
            return Response(status_code=401)

        # Redis dedup -- skip duplicate webhooks
        svc = svc_ref[0] if svc_ref else None
        payload_hash = hashlib.sha256(body).hexdigest()
        if svc and svc._redis:
            is_new = await svc._redis.set(f"webhook:crm:{payload_hash}", "1", nx=True, ex=600)
            if not is_new:
                return Response(status_code=200, content="duplicate")

        payload = json.loads(body)

        # --- Handle admin actions (adminAction field) ---
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
        """List all deployed sites for CRM reconciliation."""
        auth = request.headers.get("Authorization", "")
        admin_key = settings.espocrm_admin_key or settings.twenty_admin_key
        if not admin_key or auth != f"Bearer {admin_key}":
            return Response(status_code=401)
        sites = await list_sites(limit=1000)
        return JSONResponse(content={"sites": sites})

    @r.get("/admin/sync", response_model=None)
    async def admin_sync(request: Request) -> JSONResponse | Response:
        """Reconcile missed push events -- sync recent jobs to EspoCRM."""
        auth = request.headers.get("Authorization", "")
        admin_key = settings.espocrm_admin_key or settings.twenty_admin_key
        if not admin_key or auth != f"Bearer {admin_key}":
            return Response(status_code=401)

        espo = get_espocrm_client(settings.espocrm_url, settings.espocrm_api_key)
        if isinstance(espo, NoopEspoCRMClient):
            return JSONResponse(content={"synced": 0, "message": "EspoCRM integration disabled"})

        recent_jobs = await list_jobs(limit=100, status="done")
        synced = 0
        already_exists = 0
        errors = 0

        for job in recent_jobs:
            job_id = job.get("id", "")
            try:
                domain = extract_domain(job.get("url", ""))
                lead_id = await espo.create_or_update_lead(
                    first_name="",
                    last_name=job.get("site_title", domain),
                    email="",
                    website=f"https://{domain}",
                    description=f"Synced from job {job_id}",
                )
                if lead_id:
                    synced += 1
            except (ValueError, KeyError, TypeError, OSError) as e:
                logger.warning("Sync failed for job %s: %s", job_id, e)
                errors += 1

        return JSONResponse(
            content={"synced": synced, "already_exists": already_exists, "errors": errors}
        )

    return r
