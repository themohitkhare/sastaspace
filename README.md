# SastaSpace Project Bank

SastaSpace is now a personal project bank monorepo.

Each project lives under `projects/<name>/` and is deployed to `<name>.sastaspace.com`.

This repository is currently being reset from the legacy AI redesigner stack to the new foundations.

## Current status

- Foundations plan: `design-log/001-project-bank-foundations.md`
- Execution mode: phased migration (Phase 0 through Phase 5)
- Production cutover remains manual in Phase 6

## What to expect next

- Shared Postgres (`supabase/postgres`) with core extensions
- Optional shared PostgREST sidecar
- Project template for Next.js + Go
- Landing project at `sastaspace.com`

See `design-log/001-project-bank-foundations.md` for the full design and implementation phases.
