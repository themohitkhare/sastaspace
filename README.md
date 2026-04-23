# SastaSpace Project Bank

SastaSpace is a personal project bank monorepo.

Each project lives in `projects/<name>/` and is deployed to `<name>.sastaspace.com`.
The root domain `sastaspace.com` is served by `projects/landing`.

## Shared services

- **Postgres** (`supabase/postgres`) — one database, 50+ extensions (pgvector, PostGIS, pg_cron, pg_graphql, pgjwt, pg_net, pg_trgm, ...)
- **PostgREST** — auto REST API from your tables, honors RLS
- **GoTrue** (Supabase Auth) at `auth.sastaspace.com` — email+password, magic links, Google, GitHub
- **Studio** (Supabase) at `studio.sastaspace.com` — DB browser, SQL editor, user management (behind Cloudflare Access)

Every project shares the same JWT secret so RLS policies written in SQL apply uniformly.

## Local quickstart

Requires Docker + Docker Compose.

```bash
make keys          # generates .env + JWT_SECRET + signed ANON/SERVICE keys
make up            # boots postgres, postgrest, gotrue, pg-meta, studio
make migrate       # applies db/migrations/*.sql (roles, auth, RLS, helpers)
```

Everything is now reachable on your machine:

| Service      | URL                      |
| ------------ | ------------------------ |
| Landing app  | http://localhost:3000    |
| PostgREST    | http://localhost:3001    |
| GoTrue       | http://localhost:9999    |
| Studio       | http://localhost:3002    |
| pg-meta      | http://localhost:8080    |
| Postgres     | localhost:5432           |

Then run the landing app against those services:

```bash
cd projects/landing/web && npm install && npm run dev
```

Prefer everything containerised? `make up-full` builds and runs the landing app
as a container too (at http://localhost:3000, alongside the rest).

Other useful targets: `make logs`, `make ps`, `make psql`, `make down`,
`make reset` (wipes volumes), `make help`.

## Remote staging on 192.168.0.37

The same compose stack runs on your deploy box over ssh. One-time setup:

```bash
# On the remote: ensure docker is installed and your user is in the docker group.
# Locally:
make remote-env           # creates a remote .env (rewrites localhost → 192.168.0.37)
make remote-up            # rsync repo + `make up-full` on the remote
make remote-migrate       # apply migrations on the remote
```

The stack is then reachable at `http://192.168.0.37:3000`, `:9999`, `:3002`, …
from any machine on the LAN. Useful targets: `make remote-logs`,
`make remote-status`, `make remote-psql`, `make remote-down`, `make remote-reset`.

Production (MicroK8s + Cloudflare tunnel with real `sastaspace.com` subdomains)
still ships via `infra/k8s/` — see `design-log/001-project-bank-foundations.md`.

## Scaffold a new project

```bash
make new p=my-project
```

## Structure

- `infra/` — Kubernetes manifests and local Docker Compose
- `db/` — shared migrations, auth roles, RLS helpers, seeds
- `projects/_template/` — default scaffold (Next.js + shadcn + Supabase auth + Go API)
- `projects/landing/` — `sastaspace.com` portfolio app
- `scripts/` — key-gen, migrations, ssh/remote helpers, scaffolder
- `design-log/` — architecture and implementation decisions

## Design logs

- `design-log/001-project-bank-foundations.md` — baseline architecture
- `design-log/002-auth-admin-ui-upgrade.md` — auth, admin UI, and template visual upgrade
