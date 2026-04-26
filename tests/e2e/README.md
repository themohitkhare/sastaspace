# sastaspace e2e

Playwright tests that run against live prod by default. Override via
`E2E_BASE_*` env vars to point at a dev stack.

## Standard run (legacy auth path)

```bash
pnpm exec playwright test
```

This exercises the FastAPI auth path (`auth.sastaspace.com` →
`/auth/callback`). Requires `E2E_TEST_SECRET` env var.

## Phase 2 F1 matrix — legacy + STDB-native auth paths

The notes app sign-in flow is currently being moved off FastAPI onto the
`request_magic_link` + `verify_token` STDB reducers. Both paths coexist
behind `NEXT_PUBLIC_USE_STDB_AUTH` until the Phase 3 cutover.

**Two project entries** in `playwright.config.ts` drive the matrix:

```bash
# leg 1 — legacy (FastAPI POST → /auth/callback)
pnpm exec playwright test --project=notes-legacy

# leg 2 — stdb-native (request_magic_link reducer → /auth/verify)
E2E_STDB_AUTH=true pnpm exec playwright test --project=notes-stdb
```

The legacy spec at `specs/auth.spec.ts` runs in **both** legs (FastAPI auth
service stays up through Phase 3). The new spec at
`specs/notes-auth-stdb.spec.ts` is `test.skip()`d unless
`E2E_STDB_AUTH=true`.

For the stdb leg, additional env is required:

- `E2E_STDB_AUTH=true` — un-skips the new spec
- `E2E_STDB_OWNER_TOKEN=<jwt>` — owner token for SQL access to read the
  issued token from the `auth_token` table (test-only side door; production
  users get the token by email). Get it via `spacetime login show --token`.
- `NEXT_PUBLIC_USE_STDB_AUTH=true` baked into the notes deploy under test
  (otherwise the AuthMenu still POSTs to FastAPI and the `/auth/verify`
  page is a dead route).

Local end-to-end smoke against a dev compose:

```bash
# In one shell — compose with auth-mailer worker enabled and notes built
# with NEXT_PUBLIC_USE_STDB_AUTH=true.
cd infra && WORKER_AUTH_MAILER_ENABLED=true docker compose up -d
# In another:
cd tests/e2e && \
  E2E_STDB_AUTH=true \
  E2E_BASE_NOTES=http://localhost:3001 \
  E2E_BASE_STDB=http://localhost:3100 \
  E2E_STDB_OWNER_TOKEN=$(spacetime login show --token) \
  pnpm exec playwright test --project=notes-stdb
```

### CI matrix (Phase 3)

Phase 3 will wire CI to drive both legs. Sketch:

```yaml
strategy:
  matrix:
    auth-path: [legacy, stdb]
env:
  E2E_STDB_AUTH: ${{ matrix.auth-path == 'stdb' && 'true' || 'false' }}
  NEXT_PUBLIC_USE_STDB_AUTH: ${{ matrix.auth-path == 'stdb' && 'true' || 'false' }}
```

Until then, the existing `e2e` job in `.github/workflows/deploy.yml` runs
the legacy leg only — the new spec auto-skips so the matrix isn't blocking
on it.
