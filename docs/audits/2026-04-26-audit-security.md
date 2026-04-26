# Security Audit — 2026-04-26

**Auditor:** security
**Methodology:** Static analysis of all Rust reducer source (`modules/sastaspace/src/lib.rs`, `modules/typewars/src/*.rs`), Next.js app code (`apps/notes`, `apps/admin`), infra configs (`infra/landing/nginx.conf`, `infra/landing/security_headers.conf`, `infra/admin/security_headers.conf`, `infra/docker-compose.yml`, `infra/cloudflared/`), CI pipeline (`.github/workflows/deploy.yml`), and test helpers (`tests/e2e/helpers/auth.ts`, `tests/e2e/helpers/stdb.ts`). No live traffic was injected or observed. All findings are derived from source code and configuration inspection only.
**Overall grade:** 8/10

The codebase has meaningfully matured since `SECURITY_AUDIT.md` (2026-04-25). The prior CRITICAL finding (unauthenticated `upsert_project`) is remediated with a hardcoded owner-identity guard now present on every write reducer. Container hardening (`read_only`, `cap_drop`, `no-new-privileges`, `pids_limit`) is applied throughout `docker-compose.yml`. Security headers are in place. The main residual concerns are architectural: the workers container holds a full owner JWT (by design, but with no alternative), the `callback_url` in magic-link issuance is only `https://` prefix-validated (not domain-pinned), `add_log_interest` is ungated by owner (any identity can register interest), and `log_event` rows (container log text) are public to all subscribers. None of these are "pop the system" critical — they are medium/low hardening gaps.

---

## OWASP Top 10 quick verdict

| ID | Category | Verdict | Notes |
|---|---|---|---|
| A01 | Broken Access Control | **PASS** | Every write reducer calls `assert_owner` or checks `ctx.sender()`. Single exception: `add_log_interest` / `remove_log_interest` (no owner gate by design — see Medium finding). `claim_progress_self` correctly scopes to caller's own identity. |
| A02 | Cryptographic Failures | **PASS** | Magic-link tokens are 32-char alphanumeric from `ctx.rng()` (STDB's seeded RNG). 15-min TTL, single-use. Owner identity check is ECDSA P-256 (SpacetimeDB's default). No MD5/SHA-1 usage found. |
| A03 | Injection | **PASS (with caveat)** | No SQL built from user input in reducers (STDB uses its own type-safe query engine). Client-side SQL subscription in `apps/notes/src/lib/comments.ts:51` uses `escapeSql()` that strips `'` and `\` — adequate for a read-only subscription path. E2E `stdb.ts:sql()` uses fixed strings. No `eval`-style pattern found in app code. |
| A04 | Insecure Design | **LOW** | `callback_url` in `request_magic_link` is validated only as `starts_with("https://")` — not pinned to `*.sastaspace.com`. An attacker who can call the reducer (any authenticated identity) could supply `https://evil.example/callback` and receive a magic-link email pointing there. See Medium finding. |
| A05 | Security Misconfiguration | **LOW** | `log_event` and `system_metrics` are `public` tables — any anonymous subscriber can read container log text and host metrics. Acceptable for owner-operated site, but surfacing prod log output publicly is a misconfiguration risk. |
| A06 | Vulnerable and Outdated Components | **LOW** | `pnpm audit --audit-level high` used in CI (moderate threshold deferred for `@mastra/core` transitive advisories). Cargo audit clean. Tracked as known risk in workflow comment. |
| A07 | Identification and Authentication Failures | **PASS** | Magic-link flow is 15-min TTL, single-use, requires real email. Tokens are opaque 32-char random strings stored only in private `auth_token` table. `verify_token` is atomic: consumes token and registers identity in one reducer call. No session fixation observed. |
| A08 | Software and Data Integrity Failures | **PASS** | `pnpm install --frozen-lockfile` in CI and in Dockerfile. GitHub Actions uses pinned `@v6`/`@v7`/`@v8` action refs. No `--no-frozen-lockfile` workaround present (N8 remediated). |
| A09 | Security Logging and Monitoring Failures | **LOW** | Container log lines are routed into `log_event` (public table). No alerts or anomaly detection on owner-identity-impersonation attempts. Workers boot-time `noop_owner_check` provides one verification signal. |
| A10 | SSRF | **PASS** | No user-controlled URLs are fetched server-side from reducers. Workers fetch Ollama/LocalAI at fixed localhost addresses from env config, not from user input. |

---

## Critical findings (anything that lets an outsider pop the system)

**None identified.** All reducers that mutate owner-controlled tables are gated by `assert_owner`. The previous CRITICAL from `SECURITY_AUDIT.md` (unauthenticated `upsert_project`) is fully remediated.

---

## High-priority findings

### H1 — Workers container holds full owner JWT; no scoped identity exists

**Location:** `workers/.env` (runtime), `infra/docker-compose.yml:375-376`, `.github/workflows/deploy.yml:676-692`

**Detail:** The `STDB_TOKEN` written to `workers/.env` in CI (sourced from `secrets.WORKERS_STDB_TOKEN` or `secrets.SPACETIME_TOKEN`) is the **full owner identity JWT** — the same one that passes `assert_owner`. Every worker agent (auth-mailer, admin-collector, deck-agent, moderator-agent) runs with this token. If the workers container is compromised (e.g. via a supply-chain attack in `@mastra/core` or `node:22-alpine`), the attacker acquires an owner JWT capable of calling any owner-only reducer: deleting all projects, purging all users, overwriting auth tokens, etc.

**Context:** This is partly structural — SpacetimeDB 2.1 does not expose a scoped-identity mechanism at the time of this audit. The workers container has a `docker.sock` bind-mount (`:ro`) for log collection, which, combined with a full owner JWT, would allow full infrastructure control. The `docker.sock` mount is read-only, which limits but does not eliminate this risk.

**Risk:** HIGH — not externally exploitable without first compromising the container, but blast radius is total.

**Recommendation:** When SpacetimeDB gains capability-scoped identities or per-reducer allow-lists, split the workers token by agent. For now, at minimum: (a) ensure `workers/.env` has `chmod 600` (it does — deploy step calls `install -m 600`); (b) audit the `@mastra/core` dependency chain quarterly; (c) document that `WORKERS_STDB_TOKEN` is owner-equivalent, not a scoped credential.

---

### H2 — `request_magic_link` callback_url is prefix-validated only, not domain-pinned

**Location:** `modules/sastaspace/src/lib.rs:647-658` (`validate_magic_link_args`)

**Detail:** The `callback_url` argument to the publicly-callable `request_magic_link` reducer is only validated as: (a) starts with `https://`, (b) ≤ 400 chars. Any signed-in identity (not even owner — `request_magic_link` has **no owner gate**) can call this reducer with `callback_url = "https://attacker.example/steal?t="`. The resulting magic-link email will contain a live 15-min token pointing to the attacker's domain. If the victim clicks the link and the attacker's page extracts the token from the URL and replays it against the legitimate `verify_token` reducer on the correct origin, authentication is hijacked.

**Context:** The `app` argument IS validated against an allow-list (`"notes" | "typewars" | "admin"`), and the email address validates to contain `@`. But the callback URL itself is not domain-pinned to `*.sastaspace.com`.

**Risk:** HIGH — phishing with live auth tokens. The reducer is publicly callable (any identity including anonymous-auto-minted can call it).

**Recommendation:** Add domain allowlisting to `validate_magic_link_args`:

```rust
const ALLOWED_CALLBACK_PREFIXES: &[&str] = &[
    "https://notes.sastaspace.com/",
    "https://typewars.sastaspace.com/",
    "https://admin.sastaspace.com/",
];
if !ALLOWED_CALLBACK_PREFIXES.iter().any(|p| callback_url.starts_with(p)) {
    return Err("callback_url not in allowed domain list".into());
}
```

---

## Medium

### M1 — `add_log_interest` has no owner gate; any identity can register log interest

**Location:** `modules/sastaspace/src/lib.rs:1109-1124` (`add_log_interest`)

**Detail:** `add_log_interest` is callable by any connected identity (no `assert_owner`). Any anonymous or signed-in identity can register interest in any container name from the `ALLOWED_CONTAINERS` allow-list, causing the admin-collector worker to start a `docker logs --follow` subprocess for that container. This exposes log streaming to non-owner identities and can be used to: (a) trigger resource consumption on the host (one subprocess per interest row), (b) enumerate which containers are live.

The `log_interest` table itself is private (no `public`), so non-owner identities cannot SELECT rows. But they can INSERT via the reducer.

**Recommendation:** Gate `add_log_interest` and `remove_log_interest` with `assert_owner(ctx)?`.

---

### M2 — `log_event` (container log text) and `system_metrics` are public tables

**Location:** `modules/sastaspace/src/lib.rs:936` (`#[table(accessor = log_event, public)]`), `modules/sastaspace/src/lib.rs:877` (`#[table(accessor = system_metrics, public)]`), `modules/sastaspace/src/lib.rs:903` (`#[table(accessor = container_status, public)]`)

**Detail:** Any anonymous STDB subscriber can SELECT rows from `log_event`, `system_metrics`, and `container_status`. This exposes: raw container log text (from any of the 13 containers in `ALLOWED_CONTAINERS`), host CPU/RAM/disk/GPU metrics, and per-container status/uptime/restart counts. For a single-operator personal site this is low-severity, but log text may include email addresses, auth error strings, or internal error messages that aid enumeration.

**Recommendation:** If `log_event` and `system_metrics` are only consumed by the admin panel (which has the owner token), remove the `public` annotation. Admin panel subscriptions with a token would still work; anonymous clients would lose visibility, which is the desired behavior.

---

### M3 — STDB_TOKEN first 24 chars logged on every worker boot

**Location:** `workers/src/index.ts:23` (`token_prefix: env.STDB_TOKEN.slice(0, 24)`)

**Detail:** Workers boot log (captured by the admin-collector and stored in the public `log_event` table) contains `"token_prefix": "<first 24 chars of owner JWT>"`. JWTs are base64url and the first 24 chars of the payload section may include the identity hex if the JWT is structured as `header.payload.sig` — though in practice, the first 24 chars of the JWT string are typically the header (`eyJ...`). The risk is not immediate token recovery, but partial token disclosure in a public table is unnecessary.

**Recommendation:** Remove `token_prefix` and `token_len` from the boot log. A boolean `token_present: true` is sufficient for operator diagnostics.

---

### M4 — CI: `echo "SPACETIME_TOKEN=$SPACETIME_TOKEN"` writes secret to .env file but pattern looks like log leak

**Location:** `.github/workflows/deploy.yml:531`, `:586-588`, `:691-692`

**Detail:** In three deploy steps, CI uses `echo "SPACETIME_TOKEN=$SPACETIME_TOKEN"` (etc.) to write secrets to `.env` files on the prod host. GitHub Actions automatically masks secrets in log output, but only when the exact secret value appears as a literal string. If a secret contains a special character that causes shell word-splitting or quoting issues, the masking may fail for sub-strings. The `echo` pattern is also fragile — if the file descriptor redirect fails silently, the secret could end up in the default stdout log.

The correct pattern is `printf '%s\n' "SPACETIME_TOKEN=$SPACETIME_TOKEN" >> file` inside a group redirect, or using a heredoc with `<<'EOF'`. The CI steps here use brace-grouped redirects (`{ echo ...; } > file`) which is acceptable but the inner `echo` still expands the variable before writing.

**Risk:** Low in practice (GH Actions masking works on literal matches). Medium as a pattern to audit.

**Recommendation:** Use `printf '%s=%s\n' SPACETIME_TOKEN "$SPACETIME_TOKEN"` to avoid shell expansion side-effects, or use GH Actions' `::add-mask::` to register derived secrets if any transformations are applied.

---

### M5 — CSP: `'unsafe-inline'` and `'unsafe-eval'` required by Next.js/STDB SDK

**Location:** `infra/landing/security_headers.conf:45`, `infra/admin/security_headers.conf:16`

**Detail:** Both the landing and admin CSP allow `script-src 'unsafe-inline' 'unsafe-eval'`. The `unsafe-eval` is required by SpacetimeDB JS SDK 2.1 (uses dynamic `Function`/`eval` for schema-driven row parsing). The `unsafe-inline` is required for Next.js RSC's inline `self.__next_f.push(...)` hydration scripts. This is documented in the nginx config comments.

These permissions significantly weaken XSS mitigation. An XSS in any user-visible string (comment body, author name, post slug) could execute arbitrary JS.

**Current mitigations:** Comment bodies and author names are rendered via React JSX (not `dangerouslySetInnerHTML` — confirmed no occurrences in any app). Moderation queue filters all comments through pending → approved before public display.

**Recommendation:** Track the SpacetimeDB JS SDK roadmap for removal of `eval` dependency. When SpacetimeDB SDK drops `eval`, switch to a nonce-based CSP for Next.js inline scripts.

---

## Defense-in-depth opportunities

### D1 — STDB JWT tokens have no `exp` (no expiry)

As noted in the prior `SECURITY_AUDIT.md` (finding #9), `POST /v1/identity` returns JWTs with `"exp": null`. This remains true post-Phase 3. A leaked owner JWT or user JWT is permanently valid until the keypair rotates. For the owner JWT (held by workers container), a rotation would require reprovisioning all worker secrets.

**Recommendation:** Explore SpacetimeDB 2.1's `--jwt-default-ttl` flag. If it exists, set a 90-day TTL and plan a rotation procedure.

---

### D2 — Admin panel owner token stored in localStorage

**Location:** `apps/admin/src/hooks/useStdb.ts:19-33`

The admin panel stores the owner STDB JWT in `localStorage['admin_stdb_owner_token']`. Any XSS in the admin panel would exfiltrate the owner JWT. The admin-specific CSP allows `unsafe-inline` + `unsafe-eval`, so the blast radius of any XSS is full token exfiltration.

**Recommendation:** Consider `sessionStorage` instead of `localStorage` (at minimum limits exposure to tab lifetime). Longer term, if SpacetimeDB SDK gains a cookie-based auth flow, migrate there.

---

### D3 — Docker socket mounted read-only in workers and admin-api

**Location:** `infra/docker-compose.yml:305, 372`

Both `admin-api` (legacy, Phase 4 deletion) and `workers` mount `/var/run/docker.sock:ro`. Read-only docker socket still allows `docker inspect`, log reading, and container enumeration. Combined with a worker compromise, an attacker could enumerate all containers, read their environment (including secrets passed via `--env`), and identify other targets.

**Recommendation:** After Phase 4 deletes `admin-api`, evaluate whether `workers` can use the Docker HTTP API via TCP with TLS authentication instead of socket mount. If socket is required, consider `rootlesskit` or a docker-proxy sidecar that limits the allowed API calls.

---

### D4 — `user` table is public, exposing email addresses to all subscribers

**Location:** `modules/sastaspace/src/lib.rs:61` (`#[table(accessor = user, public)]`)

The `user` table (storing identity, email, display_name, created_at) is marked `public`. Any STDB subscriber can SELECT all registered user emails. The code comment says "email is NEVER surfaced to other clients via the public schema" — but the table itself IS public. The STDB SpacetimeDB 2.1 row-level filtering may gate this per-subscription query shape, but anonymous `SELECT *` SQL would return all rows.

**Recommendation:** Audit whether SpacetimeDB 2.1 enforces per-identity row-level access control on `public` tables. If not, remove `public` from the `user` table (admin and auth-mailer access user rows via owner-gated reducers, not subscriptions). Alternatively, add a `visibility` column and filter at the application layer.

---

### D5 — `prev_identity_hex` in magic-link URL is unvalidated hex

**Location:** `modules/sastaspace/src/lib.rs:669`

The `prev_identity_hex` query parameter is passed from the client into the magic-link URL with only `trim_start_matches("0x")` stripping. If a malicious actor sends a crafted `prev=<hex>` in the magic-link URL, the downstream `claim_progress_self` reducer would attempt to find a player with that identity and potentially merge stats. The merge itself is safe (it only merges if that player exists and is unverified), but the hex value is user-controlled.

**Recommendation:** Validate that `prev_identity_hex` is exactly 64 hex characters before embedding it in the URL. This is a low-severity hardening gap.

---

## Services flagged as Phase 4 deletion (findings noted for completeness, not action):

- `services/auth/` — legacy FastAPI auth service; now tombstoned (`auth.sastaspace.com` → HTTP 410). Will be removed in Phase 4.
- `services/admin-api/` — legacy admin API; replaced by workers admin-collector. Will be removed in Phase 4.
- `infra/agents/moderator/` — legacy Python moderator agent; replaced by workers moderator-agent. Will be removed in Phase 4.

These services held `SPACETIME_TOKEN` in their `.env` files (gitignored, provisioned by CI). Post-Phase 4, those `.env` files on the prod host should be deleted.

---

## Recommended next 5 actions

1. **Pin `callback_url` to `*.sastaspace.com` domains** in `validate_magic_link_args` (H2). This is a 5-line code change in `modules/sastaspace/src/lib.rs` and closes a live phishing token exfiltration path.

2. **Gate `add_log_interest` with `assert_owner`** (M1). One-line fix; prevents anonymous identities from triggering collector subprocesses and enumerating containers.

3. **Remove `public` from `user` table or audit row-level ACL behavior** (D4). Email addresses of all registered users are currently visible to anonymous STDB subscribers.

4. **Remove `token_prefix` from workers boot log** (M3). The first 24 chars of the owner JWT appear in the public `log_event` table. Replace with `token_present: true`.

5. **Document and plan owner JWT rotation procedure** (D1, H1). There is currently no documented process for rotating `WORKERS_STDB_TOKEN`/`SPACETIME_TOKEN`. A compromised token is permanently valid. Write a runbook: rotate keypair → re-publish module → re-provision all worker secrets → invalidate all user sessions (with user communication).

---

## Caveats

Things not verifiable from source code alone:

- **Prod host JWT key permissions.** The prior audit (`SECURITY_AUDIT.md` finding #2) found `infra/keys/id_ecdsa` at mode `0644`. `infra/keygen.sh` still `chmod 644`s both files. Cannot confirm current prod state without SSH access. If mode is still `0644`, this remains a HIGH finding.

- **SpacetimeDB row-level ACL behavior for `public` tables.** The STDB 2.1 documentation on whether `SELECT *` from a `public` table is truly unrestricted for anonymous identities was not audited against a live instance. The `user` table exposure (D4) severity depends on this.

- **Cloudflare tunnel ingress.** The prior audit found 4 stale hostnames (`tasks`, `monitor`, `llm`, `almirah`) pointing to dead ports. `infra/cloudflared/verify-no-api-ingress.sh` only checks for `api.sastaspace.com`. Cannot confirm whether the stale hostnames were pruned without a live `CF_TOKEN` query.

- **JWT `exp` TTL.** Cannot confirm whether `--jwt-default-ttl` was applied to the SpacetimeDB compose command without inspecting the live running process.

- **Workers `.env` file on prod.** CI provisions it with `chmod 600`, but host filesystem permissions cannot be verified from source code alone.

- **Admin `localStorage` token scope.** The admin panel stores the owner token in `localStorage` which persists across browser sessions. In a shared-computer scenario this is a persistent credential leak. No runtime mitigation is possible from the codebase alone.
