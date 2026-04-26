# @sastaspace/landing

The marketing site (`sastaspace.com`) and lab subpages (e.g. `/lab/deck`).
Built statically with Next.js (`next build`); CI rsyncs `out/` into the
`infra/landing/out/` volume mounted by the `landing` nginx container.

## Environment

`NEXT_PUBLIC_*` variables are inlined at build time, so they have to be
set before `pnpm --filter @sastaspace/landing build`. Setting them on
the running nginx container is a no-op.

| Variable | Purpose | Default |
| --- | --- | --- |
| `NEXT_PUBLIC_DECK_API_URL` | Legacy `services/deck` HTTP endpoint for `/lab/deck`. Will be removed in Phase 4 once STDB cutover is stable. | _unset_ (offline-prototype mode) |
| `NEXT_PUBLIC_USE_STDB_DECK` | Set to `"true"` to route `/lab/deck` through SpacetimeDB reducers (`request_plan`, `request_generate`) instead of the legacy HTTP service (Phase 2 F4 cutover gate). | `"false"` |
| `NEXT_PUBLIC_STDB_URI` | SpacetimeDB websocket URI used by `/lab/deck` when the flag above is on. | `wss://stdb.sastaspace.com` |
| `NEXT_PUBLIC_SASTASPACE_MODULE` | SpacetimeDB module name. | `sastaspace` |

## Phase 2 F4 deck rewire — operator notes

When `NEXT_PUBLIC_USE_STDB_DECK=true`:

- The `/lab/deck` page mints a per-browser anonymous SpacetimeDB identity
  on first load and persists the JWT in `localStorage` under
  `sastaspace.deck.anon.v1`. Reloading keeps the same identity, so the
  in-flight `plan_request` / `generate_job` rows in STDB stay associated
  with this browser.
- The W3 worker (`workers/src/agents/deck-agent.ts`) must be running with
  `WORKER_DECK_AGENT_ENABLED=true` for `pending` rows to flip past
  `done`/`failed`. Without it, the page hangs until the 60s plan timeout
  / 5min generate timeout, then falls back to the local procedural draft.
- The downloaded `.zip` is fetched from `<zipUrl>` returned in the
  `generate_job` row — this is the worker-produced zip on
  `https://deck.sastaspace.com/<job_id>.zip`, not a client-rendered stub.

When `NEXT_PUBLIC_USE_STDB_DECK=false` (the default), behaviour matches
the pre-F4 page: `fetch('/plan')` + `fetch('/generate')` against
`NEXT_PUBLIC_DECK_API_URL`, or local-draft fallback if unset.

Rollback from STDB to HTTP is a one-flag flip + rebuild.

## Compose note

The landing container in `infra/docker-compose.yml` is a static nginx
that serves a pre-built `out/` directory; it has no Node build stage of
its own. Set the `NEXT_PUBLIC_*` flags on the **build host / CI** before
running `pnpm build`, e.g.:

```bash
NEXT_PUBLIC_USE_STDB_DECK=true \
  pnpm --filter @sastaspace/landing build
rsync -a apps/landing/out/ infra/landing/out/
docker compose restart landing
```

## Scripts

```bash
pnpm dev        # Next.js dev server
pnpm build      # static build → out/
pnpm typecheck  # tsc --noEmit
pnpm lint       # eslint .
pnpm test       # vitest run
```
