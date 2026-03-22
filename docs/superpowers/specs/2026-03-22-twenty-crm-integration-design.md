# Twenty CRM Integration — Design Spec

> Lead management CRM + admin operations via Twenty CRM, self-hosted on the same k8s cluster.

## Problem

SastaSpace generates leads (URL submissions → redesigns → contact form inquiries) but has no way to track, manage, or follow up on them. Admin operations (delete sites, reprocess, view status) require SSH access and manual MongoDB/filesystem commands.

## Solution Overview

Integrate [Twenty CRM](https://github.com/twentyhq/twenty) (open-source, self-hosted) as both a **lead management CRM** and an **admin panel** for SastaSpace:

1. **Push sync** — SastaSpace pushes job completions, business profiles, and contact form submissions to Twenty in real-time
2. **Webhook admin actions** — Admin triggers actions (delete, reprocess) from Twenty's UI → webhook → SastaSpace executes
3. **Pull reconciliation** — Fallback sync endpoint catches any missed push events
4. **Contact form integration** — Contact form submissions create People records in Twenty linked to the Company

## Architecture

```
SastaSpace                                Twenty CRM (crm.sastaspace.com)
─────────                                ──────────────────────────────────

Worker (job completes)
  → POST /rest/companies (upsert)        Company record created/updated
  → POST /rest/redesignJobs (create)     RedesignJob record linked to Company

Contact form (submit)
  → POST /twenty/person
  → Backend: POST /rest/people (create)  Person linked to Company
  → Resend email (unchanged)             Email notification still sent

                                          Admin sets adminAction = "delete"
  ← Webhook POST /webhooks/twenty        → Backend deletes site files + DB records
                                          → Backend updates Twenty: status = "deleted"

                                          Admin sets adminAction = "reprocess"
  ← Webhook POST /webhooks/twenty        → Backend deletes + re-enqueues job
                                          → Backend updates Twenty: status = "queued"

Cron / manual (fallback)
  GET /admin/sync                        → Reconciles missed pushes (last 24h)
  GET /admin/sites                       → Twenty pulls full site list to refresh
```

## Twenty Data Model

### Company (built-in, enhanced with custom fields)

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `name` | text | Built-in | From BusinessProfile `business_name` |
| `domainName` | link | Built-in | Full URL |
| `domain` | text | Custom | Raw domain string for matching (e.g., `mrbrownbakery.com`) |
| `lastRedesignStatus` | select | Custom | `done`, `failed`, `in_progress` |
| `lastRedesignTier` | select | Custom | `free`, `premium` |
| `lastRedesignUrl` | link | Custom | `https://sastaspace.com/{subdomain}/` |
| `totalRedesigns` | number | Custom | Incremented on each job completion |
| `industry` | text | Custom | From BusinessProfile extraction |
| `lastRedesignedAt` | date | Custom | Timestamp of last completed job |

### RedesignJob (custom object)

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `jobId` | text | Unique | SastaSpace job ID |
| `company` | relation | Linked | Many-to-one with Company |
| `status` | select | | `queued`, `crawling`, `discovering`, `downloading`, `analyzing`, `redesigning`, `deploying`, `done`, `failed`, `deleted` |
| `tier` | select | | `free`, `premium` |
| `previewUrl` | link | | `https://sastaspace.com/{subdomain}/` |
| `subdomain` | text | | Filesystem slug |
| `pagesFound` | number | | From enhanced crawl `internal_pages` count |
| `assetsDownloaded` | number | | From enhanced crawl `assets` count |
| `businessIndustry` | text | | From BusinessProfile `industry` |
| `errorMessage` | text | | Populated on failure |
| `adminAction` | select | | `none`, `delete`, `reprocess` — admin sets this to trigger actions |
| `createdAt` | date | | Job creation timestamp |
| `completedAt` | date | | Job completion timestamp |

### People (built-in, used as-is)

| Field | Source | Notes |
|-------|--------|-------|
| `firstName` | Contact form | Split from name field |
| `lastName` | Contact form | Split from name field |
| `email` | Contact form | Email address |
| `company` | Relation | Linked by domain match |

Contact form message stored as a Note linked to the Person.

## New Module: `sastaspace/twenty_sync.py`

Thin wrapper around Twenty's REST API.

```python
class TwentyClient:
    """Async client for Twenty CRM REST API using httpx."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url  # e.g., "http://twenty-server.twenty:3000/rest"
        self.api_key = api_key
        # Uses httpx.AsyncClient — compatible with the async FastAPI/motor codebase.
        # No asyncio.to_thread() wrappers needed.

    def upsert_company(self, domain: str, **fields) -> dict:
        """Find company by domain, update if exists, create if not."""

    def create_redesign_job(self, company_id: str, **fields) -> dict:
        """Create a RedesignJob record linked to a company."""

    def update_redesign_job(self, job_twenty_id: str, **fields) -> dict:
        """Update fields on an existing RedesignJob."""

    def create_person(self, email: str, company_id: str, **fields) -> dict:
        """Create a Person record linked to a company."""

    def create_note(self, person_id: str, body: str) -> dict:
        """Create a Note linked to a person (for contact form messages)."""

    def find_company_by_domain(self, domain: str) -> dict | None:
        """Query companies by custom domain field."""

    def find_redesign_job(self, job_id: str) -> dict | None:
        """Query redesign jobs by SastaSpace job ID."""

    def list_redesign_jobs(self, since: str | None = None) -> list[dict]:
        """List RedesignJob records, optionally filtered by date."""
```

### Failure Handling

All Twenty API calls are wrapped in try/except. If Twenty is unreachable:
- Log a warning
- Continue — the redesign pipeline must never fail because Twenty is down
- The reconciliation endpoint catches up later

### Feature Flag

```python
# sastaspace/config.py — new fields
twenty_url: str = ""           # empty = Twenty sync disabled
twenty_api_key: str = ""
twenty_webhook_secret: str = ""
```

When `twenty_url` is empty, `TwentyClient` is not instantiated. All sync calls become no-ops. Zero overhead when Twenty isn't deployed.

## Push Sync: SastaSpace → Twenty

### On Job Completion (in `redesign_handler()`)

After the deploy step succeeds:

1. `upsert_company(domain)` — match by `domain` field. Set:
   - `name` from `business_profile.business_name` (or page title if profiling failed)
   - `lastRedesignStatus = "done"`
   - `lastRedesignTier = tier`
   - `lastRedesignUrl = https://sastaspace.com/{subdomain}/`
   - `industry` from `business_profile.industry`
   - `lastRedesignedAt = now`
   - Increment `totalRedesigns`

2. `create_redesign_job(company_id)` — set all fields from job data:
   - `jobId`, `status = "done"`, `tier`, `previewUrl`, `subdomain`
   - `pagesFound`, `assetsDownloaded`, `businessIndustry`
   - `createdAt`, `completedAt`

### On Job Failure

Same flow but with `status = "failed"` and `errorMessage` populated. Failed jobs are still valuable data — they show which sites have issues.

### On Contact Form Submission

New backend endpoint `POST /twenty/person`:

1. Extract domain from the redesigned site's subdomain (passed from frontend)
2. `find_company_by_domain(domain)` — if not found, create minimal Company with just domain
3. `create_person(email, company_id, firstName, lastName)`
4. `create_note(person_id, message)` — the contact form message body

This is called from the Next.js contact form route AFTER Turnstile verification and ALONGSIDE the Resend email. Both paths are independent — failure in one doesn't block the other.

### Contact Form Route Changes (`web/src/app/api/contact/route.ts`)

Add after the existing Resend email call:

```typescript
// Sync to Twenty CRM (fire-and-forget, don't block response)
try {
    await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/twenty/person`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, message, domain: subdomain }),
    });
} catch {
    // Twenty sync failure doesn't block the contact form
}
```

## Webhooks: Twenty → SastaSpace

### New Endpoint: `POST /webhooks/twenty`

Handles admin actions triggered from Twenty's UI.

**Security:**
- HMAC SHA256 verification using `X-Twenty-Webhook-Signature` and `X-Twenty-Webhook-Timestamp` headers
- Reject if timestamp is older than 5 minutes (replay protection)
- Return 401 on verification failure

**Webhook Payload (from Twenty):**

```json
{
    "event": "redesignJob.updated",
    "data": {
        "id": "twenty-record-id",
        "jobId": "sastaspace-job-id",
        "adminAction": "delete",
        "subdomain": "mrbrownbakery-com"
    },
    "timestamp": "2026-03-22T..."
}
```

**Action Handling:**

```python
async def handle_twenty_webhook(payload: dict):
    event = payload["event"]
    data = payload["data"]
    action = data.get("adminAction")

    if action == "delete":
        # Idempotent: deleting an already-deleted site is a 200 no-op
        # 1. Delete site files from disk
        # 2. Remove site record from MongoDB
        # 3. Update Twenty: status = "deleted", clear adminAction
        await delete_site(data["subdomain"])  # no-op if already deleted
        await twenty_client.update_redesign_job(data["id"], status="deleted", adminAction="none")

    elif action == "reprocess":
        # IMPORTANT: Read original URL from MongoDB BEFORE deleting site files
        # 1. Read original URL from MongoDB site/job record
        # 2. Delete existing site files
        # 3. Enqueue new job with same URL and tier
        # 4. Update Twenty: status = "queued", clear adminAction
        url = await get_original_url_from_db(data["subdomain"])  # reads from MongoDB
        if not url:
            await twenty_client.update_redesign_job(data["id"], adminAction="none",
                                                     errorMessage="Original URL not found")
            return
        await delete_site(data["subdomain"])
        job_id = await enqueue_redesign(url, tier=data.get("tier", "free"))
        await twenty_client.update_redesign_job(data["id"], status="queued", jobId=job_id, adminAction="none")
```

## Pull Reconciliation (Fallback)

### `GET /admin/sync`

Protected by API key (same `twenty_api_key` or a separate admin key).

**Logic:**
1. Query MongoDB for all jobs completed/failed in the last 24 hours
2. For each job, check if a matching RedesignJob exists in Twenty (by `jobId`)
3. Create missing Company + RedesignJob records for any gaps
4. Return summary: `{ synced: 3, already_exists: 12, errors: 0 }`

**Trigger options:**
- Manual: call from Twenty workflow or curl
- Automated: k8s CronJob runs daily at midnight

### `GET /admin/sites`

Returns all current sites as JSON for Twenty to pull/refresh:

```json
{
    "sites": [
        {
            "subdomain": "mrbrownbakery-com",
            "original_url": "https://mrbrownbakery.com",
            "status": "deployed",
            "created_at": "2026-03-22T...",
            "assets_count": 12,
            "has_assets_dir": true
        }
    ]
}
```

## Twenty K8s Deployment

### New Namespace: `twenty`

Manifests in `k8s/twenty/`:

```
k8s/twenty/
├── namespace.yaml
├── server.yaml         # Twenty server, port 3000, 512Mi-2Gi RAM
├── worker.yaml         # Twenty worker (yarn worker:prod), 256Mi-1Gi RAM
├── postgres.yaml       # PostgreSQL 16, PVC 10Gi, 256Mi-1Gi RAM
├── redis.yaml          # Redis, PVC 1Gi, 128Mi-512Mi RAM
├── ingress.yaml        # crm.sastaspace.com → twenty-server:3000
└── secrets.yaml        # Template: APP_SECRET, PG_DATABASE_URL, REDIS_URL
```

### Server Deployment

```yaml
image: twentycrm/twenty:latest
env:
  - SERVER_URL: "https://crm.sastaspace.com"
  - PG_DATABASE_URL: "postgres://twenty:PASSWORD@twenty-postgres:5432/twenty"
  - REDIS_URL: "redis://twenty-redis:6379"
  - APP_SECRET: "<generated>"
  - STORAGE_TYPE: "local"
  - STORAGE_LOCAL_PATH: "/app/storage"
resources:
  requests: { memory: "512Mi", cpu: "100m" }
  limits: { memory: "2Gi", cpu: "1000m" }
```

### Ingress

`crm.sastaspace.com` → `twenty-server:3000` in the `twenty` namespace.

### Cloudflare Tunnel

Add route to the existing tunnel configuration:
```json
{"hostname": "crm.sastaspace.com", "service": "http://localhost:80"}
```

The microk8s nginx ingress already routes based on `Host` header, so this just needs the ingress rule in the `twenty` namespace.

### Makefile Targets

```makefile
deploy-twenty:          # Apply twenty namespace + manifests
twenty-status:          # kubectl get pods,svc,ingress -n twenty
twenty-logs:            # Tail twenty server + worker logs
twenty-setup:           # First-time: create secrets, apply manifests, wait for ready
```

## Configuration & Secrets

### New Environment Variables (SastaSpace)

| Variable | Location | Purpose |
|----------|----------|---------|
| `TWENTY_URL` | `sastaspace-env` secret | Twenty REST API base URL |
| `TWENTY_API_KEY` | `sastaspace-env` secret | Bearer token for Twenty API |
| `TWENTY_WEBHOOK_SECRET` | `sastaspace-env` secret | HMAC secret for webhook verification |

### New Settings Fields (`sastaspace/config.py`)

```python
twenty_url: str = ""              # empty = Twenty integration disabled
twenty_api_key: str = ""
twenty_webhook_secret: str = ""
```

### Twenty-Side Configuration (Manual, One-Time)

After deploying Twenty:
1. Create workspace, set up admin account
2. Go to Settings > Data Model > create custom fields on Company
3. Create custom object "RedesignJob" with fields from the data model
4. Go to Settings > APIs & Webhooks > create API key
5. Create webhook pointing to `https://api.sastaspace.com/webhooks/twenty`
6. Store the API key and webhook secret in SastaSpace's k8s secret

## File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `sastaspace/twenty_sync.py` | TwentyClient class — REST API wrapper |
| `tests/test_twenty_sync.py` | Unit tests for TwentyClient (mocked HTTP) |
| `k8s/twenty/namespace.yaml` | Twenty namespace |
| `k8s/twenty/server.yaml` | Twenty server deployment + service |
| `k8s/twenty/worker.yaml` | Twenty worker deployment |
| `k8s/twenty/postgres.yaml` | PostgreSQL for Twenty + PVC |
| `k8s/twenty/redis.yaml` | Redis for Twenty + PVC |
| `k8s/twenty/ingress.yaml` | crm.sastaspace.com ingress |
| `k8s/twenty/secrets.yaml` | Secret template |

### Modified Files

| File | Changes |
|------|---------|
| `sastaspace/config.py` | Add `twenty_url`, `twenty_api_key`, `twenty_webhook_secret` |
| `sastaspace/jobs.py` | Call `TwentyClient` after job completion/failure in `redesign_handler()` |
| `sastaspace/server.py` | Add `/webhooks/twenty`, `/twenty/person`, `/admin/sync`, `/admin/sites` endpoints |
| `web/src/app/api/contact/route.ts` | Add fire-and-forget call to `/twenty/person` |
| `Makefile` | Add `deploy-twenty`, `twenty-status`, `twenty-logs`, `twenty-setup` targets |

## Testing Strategy

### Unit Tests (`tests/test_twenty_sync.py`)

- `TwentyClient.upsert_company()` — mock HTTP, verify request body, handle 200/404/500
- `TwentyClient.create_redesign_job()` — mock HTTP, verify company relation
- `TwentyClient.create_person()` — mock HTTP, verify name splitting
- `TwentyClient.find_company_by_domain()` — mock HTTP, handle found/not found
- Feature flag: verify no HTTP calls when `twenty_url` is empty

### Webhook Tests

- HMAC verification (valid signature, invalid signature, expired timestamp)
- Delete action: verify site files deleted + MongoDB cleared + Twenty updated
- Reprocess action: verify delete + re-enqueue + Twenty updated
- Unknown action: return 400, no side effects

### Integration Tests

- Full push flow: job completes → Company + RedesignJob created in Twenty (mocked)
- Contact form → Person created in Twenty (mocked) + email sent
- Reconciliation: create job in MongoDB without Twenty record → `/admin/sync` creates it

## New Dependencies

| Package | Purpose |
|---------|---------|
| `httpx>=0.27.0` | Async HTTP client for Twenty API calls (already a transitive dep of FastAPI) |

No new system dependencies. `httpx` is preferred over `requests` because the entire backend is async — avoids blocking the event loop.

## New Helper Functions

These abstractions are needed in `sastaspace/server.py` or a new `sastaspace/admin.py`:

| Function | Purpose |
|----------|---------|
| `delete_site(subdomain)` | Delete site files from disk + remove MongoDB site record. Idempotent (no-op if already deleted). |
| `get_original_url_from_db(subdomain)` | Read original URL from MongoDB site/job record. Returns None if not found. |
| `enqueue_redesign(url, tier)` | Create a new job via `JobService.enqueue()`. Returns job_id. |

## Admin Endpoint Authentication

The `/admin/sync` and `/admin/sites` endpoints use a dedicated admin key:

```python
twenty_admin_key: str = ""  # separate from twenty_api_key
```

Checked via `Authorization: Bearer {twenty_admin_key}` header. Using a separate key from `twenty_api_key` prevents bidirectional compromise — if the Twenty-side key leaks from logs, admin endpoints remain secure.

## Webhook Idempotency

All webhook action handlers are idempotent:
- **Delete** on an already-deleted site → 200 no-op
- **Reprocess** on a site being processed → 409 Conflict (job already queued)
- **Unknown action** → 400, no side effects
- Duplicate webhook delivery (same event ID) → detect via MongoDB and skip

## `totalRedesigns` Increment

Twenty's REST API does not support atomic increments. To avoid race conditions:
1. Read current `totalRedesigns` value from Twenty
2. Increment client-side
3. Write back

For the rare case of two simultaneous completions for the same domain, the reconciliation sync (`/admin/sync`) corrects the count by querying MongoDB for the true job count per domain.

## Resource Considerations

The server has 112GB RAM and a Ryzen 9 7900X — resource limits for Twenty are well within capacity:
- Twenty total: ~1.2Gi request / ~4.5Gi limit
- Existing stack: ~2Gi request / ~8Gi limit (app + monitoring)
- Available headroom: ~100GB+

Twenty's Redis could share the existing Redis instance (using database number 1 instead of 0) to save a container, but separate instances provide better isolation. With 112GB RAM, the extra ~128Mi is negligible. Keep them separate.

## Docker Compose Changes (Local Dev)

Add Twenty env vars to the backend service in `docker-compose.yml`:
```yaml
environment:
  TWENTY_URL: ""  # disabled in local dev by default
  TWENTY_API_KEY: ""
  TWENTY_WEBHOOK_SECRET: ""
```

## What Stays the Same

- Redesign pipeline (crawl → redesign → deploy) — unchanged
- Existing API endpoints — unchanged
- Frontend polling — unchanged
- Email notifications via Resend — still sent, Twenty is additive
- Rate limiting, dedup, concurrency — unchanged
- All existing tests — no regressions
