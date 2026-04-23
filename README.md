# SastaSpace Project Bank

SastaSpace is a personal project bank monorepo.

Each project lives in `projects/<name>/` and is deployed to `<name>.sastaspace.com`.
The root domain `sastaspace.com` is served by `projects/landing`.

## Quickstart

1. Copy env vars:
   - `cp .env.example .env`
2. Start shared local services:
   - `docker compose -f infra/docker-compose.yml up -d postgres postgrest`
3. Run landing project:
   - `cd projects/landing/web && npm install && npm run dev`
4. Scaffold a new project:
   - `make new p=my-project`

## Structure

- `infra/` - Kubernetes and local infra definitions
- `db/` - shared migrations and seeds
- `projects/` - deployable projects and template
- `scripts/` - scaffolding and local dev helpers
- `design-log/` - architecture and implementation logs

## Design log

See `design-log/001-project-bank-foundations.md` for the baseline architecture and implementation phases.
