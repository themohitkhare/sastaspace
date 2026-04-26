# Admin STDB Token UX — Phase 4 Planned Fix

## Current state (Phase 3)

The admin panel requires the owner to manually paste their STDB JWT into the
browser UI (Settings → SpacetimeDB owner token). This token is stored in
`sessionStorage` under the key `admin_stdb_owner_token` and is used to
authenticate the owner's WebSocket connection to SpacetimeDB, enabling:

- Comment moderation actions (`set_comment_status_with_reason`, `delete_comment`)
- Live log streaming (`add_log_interest` / `remove_log_interest`)

**Why it's bad UX:** The owner already authenticates via Google OAuth. Having
to separately locate and paste a STDB JWT is a friction-heavy second step.

**Security improvement (2026-04-26):** Changed storage from `localStorage` to
`sessionStorage` (security audit D2). Token is now cleared when the tab closes,
reducing XSS blast radius. A migration path reads and relocates any
`localStorage` token on first load.

## Planned fix (Phase 4)

### Architecture

```
[Owner signs in via Google OAuth]
        ↓
[Next.js API route: POST /api/stdb-token]
  - verifies Google session (NextAuth session cookie)
  - checks session.user.email === process.env.OWNER_EMAIL
  - returns { token: process.env.STDB_OWNER_JWT }  ← server-only env var
        ↓
[Frontend stores token in sessionStorage]
  - no manual paste required
  - token never baked into the client bundle
```

### Files to create/modify

1. **`apps/admin/src/app/api/stdb-token/route.ts`** — new API route
   - `GET` handler, protected by NextAuth session check
   - Returns `{ token }` if `session.user.email === OWNER_EMAIL`, else 403
   - Reads `process.env.STDB_OWNER_JWT` (server-only, never passed to client)

2. **`apps/admin/src/components/auth/AuthSignIn.tsx`** (or Shell.tsx) — call
   the API route after Google sign-in completes and store the returned token
   via `setOwnerToken()`.

3. **`apps/admin/src/components/auth/OwnerTokenSettings.tsx`** — can be kept
   as an escape hatch for token rotation, but should be secondary to auto-fetch.

4. **`apps/admin/next.config.js`** — **IMPORTANT**: remove `output: 'export'`
   (or add `output: 'standalone'`). Static export mode does not support API
   routes. This is a prerequisite for the above approach.

### Deployment change required

Switching from `output: 'export'` to `output: 'standalone'` (or removing the
export config) means the admin app can no longer be served as pure static files
from the `admin-out/` artifact. Options:

- **Next.js standalone server**: run the Next.js server process in Docker
  (`next start`). Requires updating `infra/docker-compose.yml` to run
  `node .next/standalone/server.js` instead of serving `admin-out/` via nginx.
- **Keep static + use a separate micro-service**: expose the token-fetch as a
  separate small service (e.g. a Cloudflare Worker or a Next.js API-only
  project). This keeps admin as static but adds infra complexity.

**Recommendation**: Switch admin to `output: 'standalone'` in Phase 4. The
added infra complexity is justified by eliminating the manual token paste UX.

### Environment variables needed

```bash
# Server-only — never expose to client
OWNER_EMAIL=mohitkhare582@gmail.com
STDB_OWNER_JWT=<the STDB JWT for the owner identity>
```

`STDB_OWNER_JWT` is the same JWT currently pasted manually. It should be added
to the CI secrets and to the Docker compose env block for the admin service
(not in the client-side `NEXT_PUBLIC_*` namespace).

## Why not done in Phase 3

The Phase 3 parallel fix scope for this agent was limited to components,
hooks, and lib files — not `next.config.js` or infra. Switching to a dynamic
build target affects Group 5's CSP/security_headers work and the CI deploy
artifact pipeline, making it a cross-team change that belongs in a dedicated
Phase 4 commit.
