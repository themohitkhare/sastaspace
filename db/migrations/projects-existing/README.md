# Existing Shared Tables — Rails Ownership Strategy

## Decision: Option B — Leave outside Rails management, query via raw SQL / `execute`

### Tables covered

`public.projects`, `public.admins`, `public.visits`, `public.contact_messages`

These four tables were created by `db/migrations/0001–0005_*.sql` (the legacy
SQL migration suite).  They are already in production with live data.

### Why Option B wins here

**Option A (structure.sql takeover)** would require Rails to:
1. Dump the current live schema into `db/structure.sql` (only valid with
   `config.active_record.schema_format = :sql`).
2. Disable the legacy SQL migration runner for those tables — or delete the
   `.sql` files and hope they are never re-run.
3. Generate stub migrations that create the tables only if they do not exist,
   then mark them as run in `schema_migrations` without actually executing DDL.

The last step is the blocker: Rails's schema_migrations version tracking is
per-app, so "telling Rails a migration already ran" requires inserting a row
into that app's `schema_migrations` table manually — which is fragile and
hard to reproduce in new environments (CI, dev laptop after a `db:reset`).

**Option B** avoids that entirely:
- The tables stay owned by the SQL migration suite (`db/migrations/*.sql`).
- Rails apps query them via raw SQL or a thin ActiveRecord model that sets
  `self.table_name = "public.projects"` without attempting to manage the DDL.
- The `schema_search_path` for both Rails apps includes `public`, so
  `ActiveRecord::Base.connection.execute("SELECT ...")` works with no extra
  configuration.
- No `schema_migrations` pollution.

### How to query from Rails (landing app)

```ruby
# app/models/project.rb
class Project < ApplicationRecord
  self.table_name = "projects"   # or "public.projects" if search_path excludes public
  # Rails will NOT attempt to manage this table's DDL.
  # Keep it read-mostly; writes go through the existing SQL-migration-managed
  # constraints and RLS policies.
end
```

For `visits` and `contact_messages`, which are write-heavy from the web tier,
use `ActiveRecord::Base.connection.execute` or a slim model with
`establish_connection` pointing at the same DB with `schema_search_path = "public"`.

### Migration ordering

Because the landing Rails app runs after the SQL suite:

1. `db/migrations/` SQL files run first (part of `make migrate` / `make remote-migrate`).
2. `projects/landing-rails/` Rails migrations run second (`rails db:migrate`
   inside the landing container on first deploy).
3. `projects/almirah-rails/` Rails migrations run third (almirah deploy).

Steps 2 and 3 are independent — neither depends on the other — but both
depend on step 1 having completed (specifically: `public.admins` must exist
before `SeedAdmins` runs).

### Rollback plan if Rails migrations land but the app never deploys

`rails db:rollback` in reverse order:
1. SeedAdmins.down — clears users.admin flag (no-op if users table is empty)
2. CreateSessions.down — drops public.sessions
3. CreateUsers.down — drops public.users

The four legacy tables (`projects`, `admins`, `visits`, `contact_messages`) are
unaffected by any Rails rollback because Rails never touched them.
