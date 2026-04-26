# sastaspace e2e

Playwright tests that run against live prod by default. Override via
`E2E_BASE_*` env vars to point at a dev stack.

## Sign-in helpers (`helpers/auth.ts`)

Three exports, two backends:

| Export | Backend | Notes |
| --- | --- | --- |
| `signInViaFastapi(page, email)` | FastAPI side door | Legacy. `POST /auth/request` with `X-Test-Secret` against `auth.sastaspace.com`. Untouched through Phase 3. |
| `signInViaStdb(page, email)` | STDB `mint_test_token` reducer | Bypasses email queueing. Owner JWT + secret gated. Reads minted token via SQL from the private `last_test_token` table. |
| `signIn(page, email)` | dispatching wrapper | Branches on `E2E_AUTH_BACKEND` (`fastapi` default, `stdb` for the new path). |

Existing specs that import `signIn` get the STDB path automatically once
`E2E_AUTH_BACKEND=stdb` is exported — no per-spec edit needed.

## Standard run (legacy auth path)

```bash
pnpm exec playwright test
```

This exercises the FastAPI auth path (`auth.sastaspace.com` →
`/auth/callback`). Requires `E2E_TEST_SECRET` env var.

## STDB-native sign-in (`signInViaStdb` / `E2E_AUTH_BACKEND=stdb`)

When the FastAPI auth container is gone (Phase 3 cutover) the helpers
talk to the `mint_test_token(email, secret)` reducer in the sastaspace
STDB module. The reducer is `assert_owner` AND secret-gated; in prod the
secret row is absent so the side door fails closed with
`"test mode disabled"`. To enable it on a dev/CI compose:

```bash
# 1. Publish the module (once; Phase 3 cutover step).
cd modules/sastaspace && spacetime publish sastaspace --target wasm32-unknown-unknown

# 2. Install the test secret (once per fresh DB; the row persists).
spacetime call sastaspace set_e2e_test_secret '["a-long-random-hex-at-least-16-chars"]'

# 3. Run the suite with the STDB backend.
cd tests/e2e
E2E_AUTH_BACKEND=stdb \
  E2E_TEST_SECRET=a-long-random-hex-at-least-16-chars \
  E2E_STDB_OWNER_TOKEN=$(spacetime login show --token) \
  E2E_BASE_STDB=http://localhost:3100 \
  E2E_BASE_NOTES=http://localhost:3001 \
  pnpm exec playwright test
```

Required env for the STDB backend:

- `E2E_AUTH_BACKEND=stdb` — flips `signIn` to the STDB path
- `E2E_TEST_SECRET` — must match the secret installed via
  `set_e2e_test_secret` (matches the `mint_test_token` second arg)
- `E2E_STDB_OWNER_TOKEN` — owner JWT (`spacetime login show --token`); the
  reducer is `assert_owner`-gated AND used for the SQL read of
  `last_test_token`

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
- `E2E_AUTH_BACKEND=stdb` — flips the dispatching `signIn` helper onto the
  `signInViaStdb` path (mint_test_token reducer; see "STDB-native sign-in"
  below for full env requirements).
- `E2E_STDB_OWNER_TOKEN=<jwt>` — owner JWT used both as the
  `mint_test_token` caller and for SQL reads of `last_test_token`. Get it
  via `spacetime login show --token`.
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
