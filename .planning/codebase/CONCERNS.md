# Codebase Concerns

**Analysis Date:** 2026-03-21

---

## Tech Debt

**In-memory rate limiting resets on restart:**
- Issue: `_rate_limit_store` is a plain `dict[str, list[float]]` allocated inside `make_app()`. Every pod restart or redeploy clears all tracked IPs. With a single replica, a deploy takes the rate limit back to zero for all users.
- Files: `sastaspace/server.py` (lines 50, 68–79)
- Impact: Determined users can bypass the 3-requests-per-hour limit by timing a request just after a deploy.
- Fix approach: Back the store with Redis, or document the limitation clearly.

**`streamRedesign` defaults to `localhost:8080` instead of `NEXT_PUBLIC_BACKEND_URL`:**
- Issue: `sse-client.ts` has `apiBase: string = "http://localhost:8080"` hardcoded as the default. The call site in `use-redesign.ts` passes `undefined`, so in production the SSE POST always targets `localhost:8080` from the user's browser rather than `api.sastaspace.com`.
- Files: `web/src/lib/sse-client.ts` (line 8), `web/src/hooks/use-redesign.ts` (line 68)
- Impact: The redesign flow is broken in production unless the browser happens to be on the same machine. The iframe and CTA link in `result-view.tsx` use `NEXT_PUBLIC_BACKEND_URL` correctly, but the SSE POST does not.
- Fix approach: Change the default to `process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080"` in `sse-client.ts`, or pass the env var explicitly from `use-redesign.ts`.

**`NEXT_PUBLIC_BACKEND_URL` is baked at build time but set at runtime in k8s:**
- Issue: `k8s/frontend.yaml` sets `NEXT_PUBLIC_BACKEND_URL=https://api.sastaspace.com` as a runtime env var. However, `NEXT_PUBLIC_*` variables are embedded into the Next.js bundle at build time — runtime env vars have no effect on the already-compiled static assets.
- Files: `k8s/frontend.yaml` (lines 21–23), `web/src/components/result/result-view.tsx` (line 34)
- Impact: `process.env.NEXT_PUBLIC_BACKEND_URL` resolves to `undefined` inside the running container, causing the iframe `src` to be a relative URL pointing to the Next.js origin instead of the backend. The preview iframe is broken in production.
- Fix approach: Pass `NEXT_PUBLIC_BACKEND_URL` as a Docker build argument (`ARG` / `--build-arg`) in `web/Dockerfile` and in the CI build step, or proxy `/{subdomain}/` through Next.js to eliminate the dependency on the env var.

**`claude-code-api` k8s manifest is missing from source control:**
- Issue: `k8s/backend.yaml` hard-codes `CLAUDE_CODE_API_URL=http://claude-code-api:8000/v1`, expecting a `claude-code-api` Service in the cluster. No such manifest is tracked in git (`k8s/` contains only `backend.yaml`, `frontend.yaml`, `ingress.yaml`, `namespace.yaml`).
- Files: `k8s/backend.yaml` (line 27), `k8s/` directory
- Impact: Fresh cluster deploys fail silently — the backend pod starts but every redesign request errors because the `claude-code-api` service is unreachable. Must be provisioned manually each time.
- Fix approach: Add `k8s/claude-code-api.yaml` to version control, or document the manual provisioning step in `docs/DEPLOYMENT.md`.

**`make deploy` and CI workflow are inconsistent:**
- Issue: `Makefile` `deploy` target only builds/restarts `backend` and `frontend`. The GitHub Actions workflow in `.github/workflows/deploy.yml` additionally builds, pushes, and restarts `claude-code-api`. The two deployment paths are out of sync.
- Files: `Makefile` (lines 42–51), `.github/workflows/deploy.yml` (lines 34–65)
- Impact: Manual deploys via `make deploy` leave `claude-code-api` on a stale image.
- Fix approach: Align the Makefile to mirror the workflow, or deprecate one in favour of the other.

**`sastaspace-env` k8s secret is undocumented and not created by any script:**
- Issue: `k8s/backend.yaml` loads env from a Secret named `sastaspace-env` with `optional: true`. There is no documentation, Makefile target, or creation script for this Secret. Frontend secrets (Resend, Turnstile, `OWNER_EMAIL`) have no k8s counterpart at all.
- Files: `k8s/backend.yaml` (lines 21–24), `docs/DEPLOYMENT.md`
- Impact: Contact form and Turnstile verification silently fail in production unless the operator manually creates the Secret out-of-band.
- Fix approach: Add a `k8s/secrets-template.yaml` (with placeholder values) or a documented `kubectl create secret generic sastaspace-env --from-env-file=.env` command in `docs/DEPLOYMENT.md`.

**`_ensure_chromium()` dry-run check logic is inverted:**
- Issue: In `crawler.py`, `_ensure_chromium()` runs `playwright install chromium --dry-run` and installs if `returncode != 0 AND "chromium" in stdout.lower()`. The dry-run exits 0 when Chromium IS installed, so the condition never triggers for genuinely missing Chromium.
- Files: `sastaspace/crawler.py` (lines 15–29)
- Impact: On a fresh environment without Chromium, the auto-install silently fails, causing all crawls to error.
- Fix approach: Check `returncode != 0` alone, or parse the dry-run output for "will be installed" language.

---

## Security Considerations

**SSRF — no URL allowlist/blocklist on the `/redesign` endpoint:**
- Risk: The `url` field in `RedesignRequest` is passed directly to Playwright with no validation. An attacker can submit `http://169.254.169.254/latest/meta-data/` (AWS metadata), `http://localhost:8000/` (claude-code-api admin), or any internal service address.
- Files: `sastaspace/server.py` (lines 30–32, 96), `sastaspace/crawler.py` (line 133)
- Current mitigation: Rate limiting (3 req/hour/IP). No URL scheme or address validation.
- Recommendations: Block RFC1918 addresses, link-local (169.254.x.x), loopback, and non-HTTP(S) schemes before the crawl starts. Validate using `urllib.parse.urlparse` before passing to `crawl()`.

**Path traversal — subdomain parameter used as filesystem path component without containment check:**
- Risk: The `{subdomain}` route parameter in `/serve_site` and `/serve_site_asset` is appended to `sites_dir` without verifying the resolved path stays within `sites_dir`. A crafted request to `GET /../../etc/passwd/` could escape the sites directory.
- Files: `sastaspace/server.py` (lines 237–255)
- Current mitigation: `derive_subdomain()` in `deployer.py` strips all non-alphanumeric chars except `-`, so deployer-created subdomains are safe. However, any direct HTTP request uses the raw URL parameter without going through the deployer.
- Recommendations: Add `index_path.resolve().is_relative_to(sites_dir.resolve())` guards before serving files in both route handlers.

**`claude-code-api` container mounts host `~/.claude` via `hostPath`:**
- Risk: The k8s manifest (present on filesystem but not in git) mounts `/home/mkhare/.claude` from the host node into the container as a volume. This directory contains Claude authentication tokens and conversation history.
- Files: `k8s/claude-code-api.yaml` (hostPath volume definition)
- Current mitigation: Volume is `readOnly: true`.
- Recommendations: Migrate Claude credentials to a k8s Secret. `hostPath` volumes are node-specific and will break on multi-node clusters or after re-imaging the server.

**No `securityContext` on any k8s container:**
- Risk: All deployments run with default security contexts — root user, writable root filesystem, all Linux capabilities retained.
- Files: `k8s/backend.yaml`, `k8s/frontend.yaml`
- Current mitigation: Cloudflare Tunnel limits external ingress surface.
- Recommendations: Add `securityContext: runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, and `capabilities: drop: [ALL]` to each container spec.

**No liveness probes on any k8s deployment:**
- Risk: All three deployments define only `readinessProbe`. If a container deadlocks (e.g., hangs in the `asyncio.Semaphore` or an SSE stream), it will pass readiness but never self-recover.
- Files: `k8s/backend.yaml` (lines 35–43), `k8s/frontend.yaml` (lines 24–29)
- Current mitigation: None. k8s will not restart a container that is passing readiness.
- Recommendations: Add `livenessProbe` with `initialDelaySeconds: 60` targeting the same health endpoints.

**No TLS block in the ingress manifest:**
- Risk: `k8s/ingress.yaml` defines HTTP rules for all three hosts but has no `tls:` section. Without it, cert-manager cannot issue certificates automatically, and nginx serves plaintext HTTP inside the cluster.
- Files: `k8s/ingress.yaml`
- Current mitigation: TLS is terminated at Cloudflare edge. Traffic travels over the cloudflared tunnel (encrypted). End-to-end encryption exists via Cloudflare only — the cluster's nginx serves plaintext internally.
- Recommendations: Add cert-manager `ClusterIssuer` annotation and `tls:` block to the ingress for defence in depth. The `cert-manager` addon is already enabled per `docs/DEPLOYMENT.md`.

**Contact form email field lacks format validation:**
- Risk: `route.ts` only checks `!email?.trim()` — any non-empty string is accepted. Malformed `replyTo` addresses are passed raw to Resend.
- Files: `web/src/app/api/contact/route.ts` (line 27)
- Current mitigation: `escapeHtml()` sanitizes content in the HTML email body. The `replyTo` value is not sanitized.
- Recommendations: Add server-side email format validation (regex or `zod` schema) before sending.

---

## Performance Bottlenecks

**Global semaphore serialises all redesign requests:**
- Problem: `_redesign_semaphore = asyncio.Semaphore(1)` means only one redesign can run at a time globally. All other users receive an immediate 429.
- Files: `sastaspace/server.py` (lines 51, 171–175)
- Cause: Playwright is CPU/memory intensive; single semaphore prevents OOM. Intentional but queue-less.
- Improvement path: Per-IP semaphore with a small global pool (e.g., 3 concurrent max), or queue-based processing with polling/SSE status updates.

**Playwright `networkidle` + hard 2-second sleep on every crawl:**
- Problem: `page.goto(url, wait_until="networkidle", timeout=30000)` followed by `await asyncio.sleep(2)` means every crawl takes at minimum 2 seconds after network quiescence, with a 30-second timeout before that.
- Files: `sastaspace/crawler.py` (line 161)
- Cause: Conservative wait to ensure SPAs are hydrated.
- Improvement path: Switch to `wait_until="domcontentloaded"` with a shorter explicit wait for common SPA frameworks, or reduce the hard sleep to 0.5s.

**`max_tokens=16000` requested on every redesign call:**
- Problem: Each redesign requests 16,000 output tokens regardless of page complexity. Simple pages could be completed in 4,000–8,000 tokens.
- Files: `sastaspace/redesigner.py` (line 119)
- Cause: Defensive maximum to avoid truncation.
- Improvement path: Attempt with 8,000 tokens, retry with 16,000 if `_validate_html()` detects truncation.

---

## Fragile Areas

**`ensure_running()` — subprocess-based server launch is fragile:**
- Files: `sastaspace/server.py` (lines 266–317)
- Why fragile: Polls for 5 seconds then unconditionally writes the port file, even if the server never started. On subsequent calls, a stale port file causes early return without checking liveness.
- Safe modification: Assert `_is_port_listening(port)` before writing the port file. Add a PID file to detect dead-but-port-reused processes.
- Test coverage: Not unit-tested; tested indirectly through CLI integration.

**`deploy()` writes `index.html` non-atomically:**
- Files: `sastaspace/deployer.py` (lines 80–81)
- Why fragile: `index_path.write_text(html)` is not atomic. A crash mid-write leaves a truncated `index.html` while the registry records the entry as `"status": "deployed"`.
- Safe modification: Write to a temp file first, then `os.replace()` — matching the pattern already used for `_registry.json`.

**`_registry.json` grows unboundedly:**
- Files: `sastaspace/deployer.py` (lines 91–93), `sastaspace/server.py` (lines 181–199)
- Why fragile: Every deploy appends to the registry with no cleanup policy. Under abuse the registry and stored sites could fill the 10Gi PVC.
- Safe modification: Cap registry at N most-recent entries, or add a `sastaspace cleanup --older-than 30d` command.

**`serve_site_asset` falls back to `index.html` for all unresolved paths:**
- Files: `sastaspace/server.py` (lines 247–255)
- Why fragile: For any asset path that doesn't exist, the server returns `index.html` silently. Missing CSS/JS references in redesigned sites produce no 404 — they return HTML — making debugging very difficult.
- Safe modification: Only fall back to `index.html` for extensionless paths (SPA routing convention), serve 404 for paths with file extensions that don't resolve.

---

## Scaling Limits

**Single-replica deployments with no pod disruption budget:**
- Current capacity: 1 replica each for `backend`, `frontend`.
- Limit: Rolling restart on every deploy causes a brief outage. No `PodDisruptionBudget` means k8s may take down the single pod before the replacement is ready.
- Files: `k8s/backend.yaml`, `k8s/frontend.yaml`
- Scaling path: Add `PodDisruptionBudget` with `minAvailable: 1`. For multiple backend replicas, the PVC access mode must change (see below).

**PVC is `ReadWriteOnce` — blocks horizontal backend scaling:**
- Current capacity: 10Gi single-node PVC (`ReadWriteOnce`).
- Limit: Cannot run 2+ backend replicas simultaneously — second pod fails to mount the volume.
- Files: `k8s/backend.yaml` (lines 65–75)
- Scaling path: Switch to `ReadWriteMany` storage class (NFS or CephFS via microk8s), or move site file storage to object storage (S3/R2) and serve via signed URLs.

---

## Dependencies at Risk

**`next: 16.2.1` — major version with breaking changes:**
- Risk: Next.js 16 has breaking API changes. `web/AGENTS.md` explicitly warns that "APIs, conventions, and file structure may differ from training data."
- Files: `web/package.json` (line 23), `web/CLAUDE.md`, `web/AGENTS.md`
- Impact: AI-assisted code changes risk generating code against the Next.js 14/15 API rather than 16.
- Migration plan: Document specific Next.js 16 breaking changes affecting this project in `web/AGENTS.md`.

**`claude-code-api` is an unversioned repo clone, not a pinned dependency:**
- Risk: The `claude-code-api/` directory is a full repository clone (excluded from git via `.gitignore`). No commit hash is pinned. The k8s image is built from whatever is in `~/claude-code-api` on the server.
- Files: `.gitignore`, `k8s/backend.yaml` (line 27), `docs/DEPLOYMENT.md` (section 12)
- Impact: Breaking upstream changes are invisible until the next build.
- Migration plan: Pin the repo to a specific commit in `docs/DEPLOYMENT.md` and verify it during CI.

---

## Test Coverage Gaps

**No test for SSRF via `/redesign` endpoint:**
- What's not tested: A request to `POST /redesign` with `url=http://169.254.169.254/` or `url=http://localhost:8000/`.
- Files: `tests/test_server.py`, `sastaspace/server.py`
- Risk: SSRF vulnerability is undetected and untestable regression.
- Priority: High

**No test verifying `streamRedesign` uses correct API base in production:**
- What's not tested: That `use-redesign.ts` passes `NEXT_PUBLIC_BACKEND_URL` (not `undefined`) to `streamRedesign`.
- Files: `web/src/__tests__/sse-client.test.ts`, `web/src/hooks/use-redesign.ts`
- Risk: The hardcoded `localhost:8080` default is the active code path in production. Current tests always pass `apiBase` explicitly, masking the real production behaviour.
- Priority: High

**No test for path traversal in `serve_site` / `serve_site_asset`:**
- What's not tested: That requests like `GET /../../etc/passwd/` are rejected.
- Files: `tests/test_server.py`, `sastaspace/server.py` (lines 237–255)
- Risk: Path traversal vulnerability is both unmitigated and untested.
- Priority: High

**`og-image.png` referenced in metadata but not present:**
- What's not tested: `web/src/app/[subdomain]/page.tsx` hardcodes `images: ["/og-image.png"]` in OpenGraph metadata. The file does not exist in `web/public/`.
- Files: `web/src/app/[subdomain]/page.tsx` (line 17), `web/public/`
- Risk: Social share previews for all result pages show a broken image.
- Priority: Medium

**Crawler tests are fully mocked — no test for `_ensure_chromium()` failure path:**
- What's not tested: That the crawler handles a missing Chromium installation gracefully. That `wait_until="networkidle"` timeout (30s) path is handled.
- Files: `tests/test_crawler.py`, `sastaspace/crawler.py`
- Risk: Crawler startup failures in Docker (e.g., missing system libraries for Chromium) are not caught by CI.
- Priority: Medium

---

*Concerns audit: 2026-03-21*
