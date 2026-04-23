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

## Quickstart

1. Copy env vars: `cp .env.example .env` and edit. The important one is a strong `JWT_SECRET` (min 32 chars).
2. Start shared local services:
   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```
   This brings up Postgres, PostgREST, GoTrue, pg-meta, and Studio.
3. Apply migrations into the database (SQL files in order):
   ```bash
   for f in db/migrations/*.sql; do
     docker exec -i sastaspace-postgres psql -U postgres -d sastaspace < "$f"
   done
   ```
4. Run the landing project:
   ```bash
   cd projects/landing/web && npm install && npm run dev
   ```
5. Scaffold a new project:
   ```bash
   make new p=my-project
   ```

## Structure

- `infra/` — Kubernetes manifests and local Docker Compose
- `db/` — shared migrations, auth roles, RLS helpers, seeds
- `projects/_template/` — default scaffold (Next.js + shadcn + Supabase auth + Go API)
- `projects/landing/` — `sastaspace.com` portfolio app
- `scripts/` — scaffolder and dev helpers
- `design-log/` — architecture and implementation decisions

## Design logs

- `design-log/001-project-bank-foundations.md` — baseline architecture
- `design-log/002-auth-admin-ui-upgrade.md` — auth, admin UI, and template visual upgrade
