# Rails Schema Design — sastaspace.com Rails migration

**Status:** Ready for Phase 0 execution  
**Date:** 2026-04-24  
**Author:** Team 4 (database)  
**Ref:** design-log/006-rails-kamal-migration.md

---

## ER Diagram

```
public schema (shared, SQL-migration-owned)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 admins                       projects
 ┌──────────────┐             ┌───────────────────┐
 │ email PK     │             │ id BIGSERIAL PK    │
 │ note         │             │ slug UNIQUE        │
 │ added_at     │             │ name               │
 └──────────────┘             │ url                │
                              │ description        │
                              │ live_at            │
 visits                       │ created_at         │
 ┌──────────────┐             └───────────────────┘
 │ id BIGSERIAL │
 │ project_slug │  contact_messages
 │ referrer     │  ┌───────────────────┐
 │ ua           │  │ id BIGSERIAL PK    │
 │ created_at   │  │ name               │
 └──────────────┘  │ email              │
                   │ message            │
                   │ source_project     │
                   │ created_at         │
                   └───────────────────┘

public schema (Rails-landing-owned, new)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 users                        sessions
 ┌──────────────────┐        ┌─────────────────────┐
 │ id BIGSERIAL PK  │◄──┐   │ id UUID PK           │
 │ email UNIQUE     │   └───│ user_id FK→users.id  │
 │ name             │       │ user_agent            │
 │ google_uid       │       │ ip_address INET       │
 │ avatar_url       │       │ last_active_at        │
 │ admin BOOLEAN    │       │ created_at            │
 │ created_at       │       │ updated_at            │
 │ updated_at       │       └─────────────────────┘
 └──────────────────┘

project_almirah schema (Rails-almirah-owned)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 items                         outfits
 ┌──────────────────────┐     ┌──────────────────────┐
 │ id UUID PK           │     │ id UUID PK            │
 │ user_id FK→users.id  │     │ user_id FK→users.id   │
 │ kind TEXT            │     │ name TEXT             │
 │ name TEXT            │     │ created_at            │
 │ tone TEXT            │     │ updated_at            │
 │ rack TEXT            │     └──────────────────────┘
 │ last_worn_at         │             │
 │ wears_count INT      │             │ outfit_items (join)
 │ price_inr INT        │     ┌───────────────────────┐
 │ photo_path TEXT      │◄────│ outfit_id FK→outfits  │
 │ created_at           │     │ item_id   FK→items    │
 │ updated_at           │     │ position INT          │
 └──────────────────────┘     │ PK(outfit_id,item_id) │
           │                  └───────────────────────┘
           │ wear_events
 ┌──────────────────────┐
 │ id UUID PK           │
 │ item_id FK→items     │
 │ worn_at TIMESTAMPTZ  │
 │ event_name TEXT      │
 │ attendees TEXT[]     │
 │ notes TEXT           │
 │ created_at           │
 │ updated_at           │
 └──────────────────────┘

 ingest_jobs                   gap_suggestions
 ┌──────────────────────┐     ┌──────────────────────┐
 │ id UUID PK           │     │ id TEXT PK            │
 │ user_id FK→users.id  │     │ kind TEXT             │
 │ photo_count INT      │     │ name TEXT             │
 │ status TEXT          │     │ tone TEXT             │
 │ started_at           │     │ reason TEXT           │
 │ finished_at          │     │ source TEXT           │
 │ error_message        │     │ price_inr INT         │
 │ created_at           │     │ url TEXT              │
 │ updated_at           │     │ created_at            │
 └──────────────────────┘     │ updated_at            │
                              └──────────────────────┘
```

---

## Schema Ownership Table

| Schema | Tables | Owner | Migration runner |
|---|---|---|---|
| `public` | `admins`, `projects`, `visits`, `contact_messages` | SQL migration suite | `make migrate` / `make remote-migrate` |
| `public` | `users`, `sessions` | Rails landing app | `rails db:migrate` in landing container |
| `project_almirah` | all tables above | Rails almirah app | `rails db:migrate` in almirah container |
| `auth` | all GoTrue tables | Supabase GoTrue image | pre-installed, not managed by Rails |

---

## database.yml for each Rails app

### Landing app (`projects/landing-rails/config/database.yml`)

```yaml
default: &default
  adapter: postgresql
  encoding: unicode
  pool: <%= ENV.fetch("RAILS_MAX_THREADS") { 5 } %>
  url: <%= ENV["DATABASE_URL"] %>
  # search_path includes public only — no cross-schema leakage
  schema_search_path: "public,pg_catalog"
  migrations_paths: db/migrate

production:
  <<: *default

development:
  <<: *default

test:
  <<: *default
  url: <%= ENV.fetch("DATABASE_URL_TEST", ENV["DATABASE_URL"]) %>
```

`DATABASE_URL` format: `postgresql://postgres:<password>@<host>:5432/sastaspace`

### Almirah app (`projects/almirah-rails/config/database.yml`)

```yaml
default: &default
  adapter: postgresql
  encoding: unicode
  pool: <%= ENV.fetch("RAILS_MAX_THREADS") { 5 } %>
  url: <%= ENV["DATABASE_URL"] %>
  # project_almirah first so unqualified table names resolve there;
  # public second so cross-schema FKs and the users lookup work.
  schema_search_path: "project_almirah,public,pg_catalog"
  migrations_paths: db/migrate

production:
  <<: *default

development:
  <<: *default

test:
  <<: *default
  url: <%= ENV.fetch("DATABASE_URL_TEST", ENV["DATABASE_URL"]) %>
```

Both apps use the **same DATABASE_URL / same Postgres user / same database
(`sastaspace`)**.  Schema isolation comes entirely from `schema_search_path`,
not from separate DB users or separate databases.

---

## Cross-Schema Queries (almirah → public.users)

### Recommendation: schema_search_path (selected)

Configure almirah's `database.yml` with
`schema_search_path: "project_almirah,public,pg_catalog"`.

Result: `User.find(id)` in almirah resolves to `public.users` without
any extra configuration.  ActiveRecord's `User` model needs only:

```ruby
# projects/almirah-rails/app/models/user.rb
class User < ApplicationRecord
  self.table_name = "users"   # resolves to public.users via search_path
end
```

### Why not `establish_connection` or `connects_to`?

- `establish_connection` opens a second connection pool to the same DB,
  doubling connection count for no benefit.
- `connects_to` (Rails horizontal sharding) is designed for different database
  servers or physically different schemas, not for the same server with a
  different search path.  Using it here would mean two connection pools with
  the same underlying socket — wasteful.
- `schema_search_path` achieves the same resolution at zero cost.

### For explicit cross-schema SQL

When a query explicitly needs to join `project_almirah.items` with
`public.users` (e.g. for admin reporting), qualify the table name:

```ruby
ActiveRecord::Base.connection.execute(<<~SQL)
  SELECT u.email, count(i.id) AS item_count
    FROM public.users u
    JOIN project_almirah.items i ON i.user_id = u.id
   GROUP BY u.email;
SQL
```

This works from either app regardless of search_path because both schemas
are on the same connection.

---

## Migration Ordering

### What runs once per DB (the SQL migration suite)

Run via `make migrate` or `make remote-migrate` **before any Rails app
deploys**:

```
0001_enable_extensions.sql        — pgvector, postgis, pg_cron, pgcrypto etc.
0002_shared_schema.sql            — public.projects, visits, contact_messages
0003_auth_prep.sql                — auth schema, GoTrue roles, RLS helpers
0004_admins_and_helpers.sql       — public.admins, is_admin(), RLS policies
0005_fix_anon_grants_and_is_admin.sql — post-launch grant fixes
```

### What runs per Rails app (Rails migrations)

**Landing app** — run on first `kamal deploy` of landing:

```
20260424000001_create_users.rb         — public.users
20260424000002_create_sessions.rb      — public.sessions
20260424000003_seed_admins.rb          — insert admin email, backfill users.admin
```

**Almirah app** — run on first `kamal deploy` of almirah:

```
20260424010001_create_almirah_schema.rb  — CREATE SCHEMA IF NOT EXISTS project_almirah
20260424010002_create_items.rb           — project_almirah.items
20260424010003_create_outfits.rb         — project_almirah.outfits
20260424010004_create_outfit_items.rb    — project_almirah.outfit_items
20260424010005_create_wear_events.rb     — project_almirah.wear_events
20260424010006_create_ingest_jobs.rb     — project_almirah.ingest_jobs
20260424010007_create_gap_suggestions.rb — project_almirah.gap_suggestions
20260424010008_seed_almirah_items.rb     — 26 items + 3 gap suggestions
```

**Dependency:** almirah migrations depend on the landing migrations having
run first (items.user_id → public.users.id FK).  In practice: land the
landing app first, verify `public.users` exists, then deploy almirah.

---

## Existing Shared Tables — Option B

The four tables created by the SQL migration suite
(`public.projects`, `public.admins`, `public.visits`, `public.contact_messages`)
are **left outside Rails management**.

**Selected: Option B — query via raw SQL or slim ActiveRecord model**

Rationale: these tables are already in production with live data and RLS
policies.  Option A (structure.sql takeover) requires inserting fake rows into
`schema_migrations` to mark those tables as already-migrated, which is fragile
in new environments (CI, dev reset) and offers no benefit.  Option B queries
them as `ActiveRecord::Base.connection.execute` or via a model with
`self.table_name = "projects"` (resolves via search_path).  No `schema_migrations`
pollution.  Rails never issues DDL against these tables.

Full rationale: `db/migrations/projects-existing/README.md`

---

## Rollback Strategy

### If schema lands but app never deploys

Run `rails db:rollback STEP=N` in the relevant app's container in reverse
order:

**Landing rollback:**
```
SeedAdmins.down       — clears users.admin flag (no-op if users empty)
CreateSessions.down   — DROP TABLE public.sessions
CreateUsers.down      — DROP TABLE public.users
```

The four legacy tables are unaffected — Rails never touched them.

**Almirah rollback:**
```
SeedAlmirahItems.down        — DELETE seeded rows
CreateGapSuggestions.down    — DROP TABLE project_almirah.gap_suggestions
CreateIngestJobs.down        — DROP TABLE project_almirah.ingest_jobs
CreateWearEvents.down        — DROP TABLE project_almirah.wear_events
CreateOutfitItems.down       — DROP TABLE project_almirah.outfit_items
CreateOutfits.down           — DROP TABLE project_almirah.outfits
CreateItems.down             — DROP TABLE project_almirah.items
CreateAlmirahSchema.down     — DROP SCHEMA project_almirah (only if empty)
```

`CreateAlmirahSchema.down` raises if the schema is non-empty, which prevents
accidental data loss if tables were not rolled back first.

---

## Idempotency Checklist

Every migration is safe to re-run:

| Migration | Idempotency mechanism |
|---|---|
| CreateUsers | `CREATE TABLE IF NOT EXISTS`, `CREATE UNIQUE INDEX IF NOT EXISTS` |
| CreateSessions | `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS` |
| SeedAdmins | `ON CONFLICT (email) DO NOTHING` for admins insert; UPDATE is a no-op when already correct |
| CreateAlmirahSchema | `CREATE SCHEMA IF NOT EXISTS`; grants guarded by `IF EXISTS` role check |
| CreateItems | `CREATE TABLE IF NOT EXISTS`; CHECK constraints are `ADD CONSTRAINT` (will error if already exists — wrap in `IF NOT EXISTS` guard via `DO $$ IF NOT EXISTS` if re-run is expected post-deploy) |
| CreateOutfits | `CREATE TABLE IF NOT EXISTS` |
| CreateOutfitItems | `CREATE TABLE IF NOT EXISTS` |
| CreateWearEvents | `CREATE TABLE IF NOT EXISTS` |
| CreateIngestJobs | `CREATE TABLE IF NOT EXISTS` |
| CreateGapSuggestions | `CREATE TABLE IF NOT EXISTS` |
| SeedAlmirahItems | `ON CONFLICT (id) DO NOTHING` for all rows |

Note on ADD CONSTRAINT: Rails `execute "ALTER TABLE ... ADD CONSTRAINT ..."` 
will error on re-run if the constraint already exists.  For production safety,
wrap in a `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN NULL; END $$;`
block, or check `pg_constraint` first.  The migrations as written are safe for
a clean first run; teams should add the guard if they anticipate replaying on a
partially-migrated DB.

---

## Index Strategy

### public.users
- `idx_users_email` UNIQUE — covers the primary auth lookup (sign-in by email)
- `idx_users_google_uid` PARTIAL (WHERE NOT NULL) — covers OAuth callback lookup

### public.sessions
- Primary key on `id` UUID — every request does a single row lookup here
- `idx_sessions_user_id` — for "invalidate all sessions for user X"
- `idx_sessions_last_active_at DESC` — for pg_cron expiry sweeps

### project_almirah.items
- Primary key on `id` UUID
- `idx_items_user_id_id` UNIQUE — covers "all items for user" (most frequent query); satisfies the (user_id, id) unique requirement
- `idx_items_user_last_worn DESC NULLS LAST` — covers "sort by most recently worn"
- `idx_items_user_rack` — covers rack-filtered views (ethnic / office / weekend)

### project_almirah.wear_events
- `idx_wear_events_item_worn_at` — covers "wear history for item, newest first"
- `idx_wear_events_attendees` GIN — covers repeat-risk query `ARRAY['X'] && attendees`

### project_almirah.ingest_jobs
- `idx_ingest_jobs_user_id_status` — covers "active jobs for user" polling

---

## Security Considerations

1. **Sessions table as the session store** — no session data in cookies, only a
   UUID.  Signed HttpOnly cookie carries only `session.id`.  Revoke a session
   by deleting the row.  Compromise of the cookie store (Rails `secret_key_base`)
   only exposes the UUID, not session data.

2. **Cross-schema FK (items.user_id → public.users.id)** — Postgres enforces
   this at the constraint level; a deleted user cascades to delete their items.
   No orphan rows possible.

3. **CHECK constraints over ENUMs** — `kind`, `rack`, `status` use text CHECK
   constraints so new values can be added with a `DROP CONSTRAINT / ADD
   CONSTRAINT` pair that does not rewrite the table (unlike ALTER TYPE ADD VALUE
   which, in some Postgres versions, requires a transaction restart).

4. **inet type for ip_address** — stores the client IP as Postgres INET, not
   TEXT.  This enforces valid IP syntax at the DB level and enables future
   subnet queries.

5. **No plaintext passwords** — the schema has no password column.  All auth
   is Google OAuth in v1.  If email/password is added later, use bcrypt via
   Rails `has_secure_password` which hashes before insert.

6. **RLS** — the existing `public.*` tables already have RLS policies from the
   SQL migration suite.  The new `public.users` and `public.sessions` tables do
   not yet have RLS policies — add them before PostgREST is re-enabled if
   the PostgREST pod is ever brought back.  Rails apps talk directly as the
   `postgres` superuser (or a dedicated app role), bypassing RLS — this is
   acceptable while PostgREST is decommissioned per the migration plan.

---

## Verification Log

### Live DB inspection (2026-04-24)

Connected via:
```
ssh 192.168.0.37 microk8s kubectl -n sastaspace exec postgres-0 -- psql -U postgres -d sastaspace
```

Confirmed existing tables:

```
public.admins              — 1 row: mohitkhare582@gmail.com (already seeded)
public.projects            — exists
public.visits              — exists
public.contact_messages    — exists
auth.*                     — 23 GoTrue tables (untouched by Rails)
```

Confirmed NOT existing (no collisions):
- `public.users` — does not exist
- `public.sessions` — does not exist
- `project_almirah` schema — does not exist
- `ingest_job_status` enum type — does not exist

### Dry-run results

Each migration's DDL was tested in a `BEGIN; ... ROLLBACK;` transaction
against the live DB.  Results:

| Migration | SQL tested | Outcome |
|---|---|---|
| CreateUsers | CREATE TABLE public.users + 2 indexes | PASS — rolled back cleanly |
| CreateSessions | CREATE TABLE public.sessions + 2 indexes | PASS — FK to users resolved after users table created in same txn |
| SeedAdmins | INSERT INTO admins ON CONFLICT + UPDATE users | PASS — INSERT was no-op (row exists); UPDATE was no-op (users table empty) |
| CreateAlmirahSchema | CREATE SCHEMA project_almirah + grants | PASS — schema created, grants succeeded for existing roles |
| CreateItems | CREATE TABLE project_almirah.items + 3 indexes + 2 CHECK constraints | PASS |
| CreateOutfits | CREATE TABLE project_almirah.outfits + index | PASS |
| CreateOutfitItems | CREATE TABLE project_almirah.outfit_items + index | PASS |
| CreateWearEvents | CREATE TABLE project_almirah.wear_events + 2 indexes (incl. GIN) | PASS |
| CreateIngestJobs | CREATE TABLE project_almirah.ingest_jobs + index | PASS |
| CreateGapSuggestions | CREATE TABLE project_almirah.gap_suggestions | PASS |
| SeedAlmirahItems | Full 26-item + 3-gap INSERT (skipped user lookup — no user row) | PASS — seed correctly short-circuits with NOTICE when no admin user found |
