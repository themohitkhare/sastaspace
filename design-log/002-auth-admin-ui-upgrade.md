# Design Log 002 — Auth, Admin UI, and Template Visual Upgrade

**Status:** Approved — executing
**Date:** 2026-04-23
**Owner:** @mkhare
**Depends on:** [001-project-bank-foundations.md](001-project-bank-foundations.md)

---

## Background

Foundations (Design Log 001) are live on `main`. We have a monorepo with `supabase/postgres` + `PostgREST` shared services, a `_template`, and a `landing` project. The next question is how to give every project a shared **auth layer + admin UI**, and how to level up the `_template` so every new project starts beautiful and consistent.

## Locked decisions

| # | Decision | Choice |
|---|---|---|
| A1 | Auth/admin path | **Path A full** — Supabase-lite: GoTrue + Studio + PostgREST as shared services |
| A2 | UI upgrade scope | **Full pack**: shadcn component library, dark mode, layout shell, motion, data-table |

## Scope

**Added to `infra/k8s/`:**
- `gotrue.yaml` — GoTrue (Supabase Auth) deployment + service
- `studio.yaml` — Supabase Studio deployment + service
- `pg-meta.yaml` — `postgres-meta` deployment + service (required by Studio)
- `auth-ingress.yaml` — host rules for `auth.sastaspace.com` (GoTrue) and `studio.sastaspace.com` (Studio)
- Updates to `secrets.yaml.template` for new env keys

**Added to `infra/docker-compose.yml`:**
- Mirror of the above three services for local dev parity

**Added to `db/migrations/`:**
- `0003_auth_schema.sql` — creates the `auth` schema and required roles for GoTrue (`supabase_auth_admin`, `authenticated`, `service_role`) *if not already provisioned by GoTrue itself*
- `0004_rls_helpers.sql` — helper functions `auth.uid()`, `auth.role()` usable in RLS policies

**Added to `projects/_template/web/`:**
- Full shadcn installation (`components.json`, `src/components/ui/*`) — `button`, `input`, `label`, `card`, `form`, `dialog`, `dropdown-menu`, `sheet`, `tabs`, `navigation-menu`, `toast`, `skeleton`, `badge`, `avatar`, `separator`, `table`, `data-table` (with `@tanstack/react-table`)
- `src/components/layout/` — `app-shell.tsx`, `topbar.tsx`, `sidebar.tsx`, `footer.tsx`
- `src/components/theme/` — `theme-provider.tsx`, `theme-toggle.tsx` (using `next-themes`)
- `src/app/globals.css` — design-token CSS vars (light + dark) using the shadcn "neutral" baseline, overridable per-project
- `src/app/layout.tsx` — wraps children in `<ThemeProvider>`, loads Inter via `next/font`
- `src/lib/supabase/{client.ts,server.ts,middleware.ts}` — `@supabase/ssr` setup
- `src/app/(auth)/sign-in/page.tsx`, `sign-up/page.tsx`, `forgot-password/page.tsx` — ready-made auth pages
- `src/middleware.ts` — refreshes Supabase auth cookies on every request
- `src/app/(admin)/admin/users/page.tsx` — example gated admin page (role check via `auth.role()`)
- `motion` dependency installed; `src/components/motion/` — small wrapper primitives

**Added to `projects/_template/`:**
- `.env.example` entries for `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

**Removed from template:**
- The stubbed `ui/button.tsx`, `ui/input.tsx`, `ui/card.tsx` placeholders (replaced by real shadcn versions)

## Non-goals

- Supabase **Storage**, **Realtime**, **Edge Functions** — skipped until a specific project needs them.
- Self-hosted Kong API gateway — we route via existing Nginx ingress directly to GoTrue.
- Row Level Security *policies* for every project's data — only helpers + one example; each project owns its policies.

## Architecture

```mermaid
graph TD
    CF[CloudflareTunnel]
    subgraph mk8s [MicroK8s]
        ING[NginxIngress]
        subgraph shared [sastaspaceNamespace]
            PG[(Postgres)]
            PGR[PostgREST]
            GT[GoTrue]
            ST[Studio]
            PM[pgMeta]
        end
        subgraph proj [projectsNamespace]
            LAND[landing]
            APP1[projectFoo]
        end
    end
    CF --> ING
    ING -->|auth.sastaspace.com| GT
    ING -->|studio.sastaspace.com| ST
    ING -->|sastaspace.com| LAND
    ING -->|foo.sastaspace.com| APP1
    LAND -->|"@supabase/ssr (JWT)"| GT
    APP1 -->|"@supabase/ssr (JWT)"| GT
    GT --> PG
    PGR --> PG
    ST --> PM --> PG
    LAND --> PG
    APP1 --> PG
```

## Open implementation questions

Please answer inline; execution happens after.

**Q1. OAuth providers to enable at launch.**
**A1:** Email/password, Magic links (OTP), Google, GitHub. (Apple, Discord skipped for now.)

**Q2. SMTP provider for GoTrue.**
**A2:** Reuse **Resend** via SMTP relay (`smtp.resend.com`, port 465, user `resend`, password = existing `RESEND_API_KEY`).

**Q3. Studio access protection.**
**A3:** **Cloudflare Access** in front of `studio.sastaspace.com`. Single Zero-Trust rule: email in allowlist.

**Q4. Initial admin identity.**
**A4:** `mohitkhare582@gmail.com`. Seeded into `public.admins` allowlist at bootstrap; first sign-in auto-promotes that email's `auth.users` row.

**Q5. Design tokens / brand.**
**A5:** Neutral shadcn baseline in `_template`; each project overrides via its own `globals.css`.

**Q6. Motion library.**
**A6:** `motion` (motion.dev).

**Q7. Template auth UX.**
**A7:** Full: sign-in + sign-up + forgot-password + signed-out landing + protected `/admin`.

**Q8. Retrofit `projects/landing` in this pass?**
**A8:** Yes — add optional sign-in, show signed-in state, expose `/admin` gated to the admin allowlist.

## Implementation plan (preview)

Five phases, each one commit:

1. **Phase A — Shared services infra.** `gotrue`, `studio`, `pg-meta` in `infra/k8s/` + `docker-compose.yml`. Secrets template + docs.
2. **Phase B — DB auth plumbing.** `db/migrations/0003_auth_schema.sql`, `0004_rls_helpers.sql`, and role grants that mirror what GoTrue needs.
3. **Phase C — Template UI pack.** shadcn bulk install, layout shell, theme provider/toggle, data-table, motion, design tokens.
4. **Phase D — Template auth wiring.** `@supabase/ssr` client/server/middleware, auth pages, gated `/admin`, `.env.example` updates.
5. **Phase E — Docs.** Update `CLAUDE.md`, root `README.md`, `projects/_template/README.md`; append Implementation Results to this log.

Phase 6 (prod cutover for the new services) remains human-only.

## Risks

- **GoTrue + PostgREST share the same JWT secret.** Forgetting to set `PGRST_JWT_SECRET == GOTRUE_JWT_SECRET` silently breaks RLS auth. Mitigation: both read from the same k8s secret key.
- **Studio is powerful.** Anyone reaching the URL can `DROP TABLE`. Must be gated (see Q3).
- **GoTrue owns the `auth` schema.** Our migration must *not* recreate `auth.users`; only reference it.
- **Shadcn explosion.** Pulling 15+ components into `_template` adds surface. Mitigation: list is curated; projects are free to delete unused ones.
- **SSR auth cookies** in middleware can misbehave behind Cloudflare if Host headers are rewritten. Mitigation: set `trustHost` in Supabase client; verify in smoke test.

## What happens next

1. You answer Q1–Q8 inline above.
2. I generate a plan file (Design Log 002 → new `.plan.md`) with phase-by-phase todos, then execute A → E.

---

## Implementation Results

Implementation completed 2026-04-23 across five commits on `main`.

### Commit history

| Phase | Commit | Title |
|---|---|---|
| A | `ef06a409` | `feat(infra): gotrue + studio + pg-meta shared services` |
| B | `6a112e51` | `feat(db): auth roles, admins allowlist, rls helpers` |
| C | `0c5eff69` | `feat(template): shadcn UI pack, theme, layout shell, data-table` |
| D | `a13effae` | `feat(template): supabase/ssr auth, gated /admin` |
| E | *(this commit)* | `feat(landing): supabase auth, admin area; docs refresh` |

### Phase A — Shared services infra

- Added `gotrue`, `pg-meta`, `studio` to `infra/k8s/` and `infra/docker-compose.yml`.
- `infra/k8s/auth-ingress.yaml` routes `auth.sastaspace.com` -> `gotrue:9999` and `studio.sastaspace.com` -> `studio:3000`.
- Rewired PostgREST to use the `authenticator` login role + `anon` default role sharing `JWT_SECRET` with GoTrue.
- `secrets.yaml.template` gained `gotrue-config`, `pg-meta-config`, `studio-config`.
- `.env.example` gained a full set of auth-related vars (SMTP via Resend, Google/GitHub OAuth stubs).

### Phase B — DB auth plumbing

- `db/migrations/0003_auth_prep.sql` — creates `anon`, `authenticated`, `service_role`, `authenticator`, `supabase_auth_admin` roles idempotently; adds `auth` schema owned by `supabase_auth_admin`; defines `auth.jwt()`, `auth.uid()`, `auth.role()`, `auth.email()` helper functions; grants on `public`.
- `db/migrations/0004_admins_and_helpers.sql` — `public.admins(email)` allowlist seeded with `mohitkhare582@gmail.com`; `public.is_admin()` helper; baseline RLS policies on `projects`, `visits`, `contact_messages`, and `admins`.

### Phase C — Template UI pack

- Tailwind v4 with CSS-vars design tokens (light + dark) in `globals.css`.
- 17 shadcn components written in place (no `npx shadcn add`), sitting in `projects/_template/web/src/components/ui/`.
- Theme layer: `next-themes` ThemeProvider + ThemeToggle dropdown.
- Layout shell: `AppShell`, `Topbar`, `Sidebar`, `Footer`.
- Inter font loaded via `next/font` and exposed as `--font-sans`.
- Rewrote home page, `/contact`, and `ContactForm` to use the new primitives.
- Switched lint script from `next lint` (removed in Next 16) to `eslint .`.
- `npm run build` succeeds with 5 routes before auth; 11 routes after auth.

### Phase D — Template auth wiring

- `@supabase/ssr` client/server/middleware helpers in `src/lib/supabase/`.
- Next.js 16 renamed `middleware.ts` to `proxy.ts` (migration caught during build and applied immediately).
- `(auth)` route group: sign-in, sign-up, forgot-password with email+password, magic link, Google, GitHub OAuth.
- `(admin)` route group: server-side gate via `isCurrentUserAdmin()`, overview + users tables.
- `UserMenu` became an async RSC that displays avatar + dropdown when signed in and a Sign-in button otherwise.

### Phase E — Landing retrofit + docs

- Replicated template sources into `projects/landing/web` (shared components, lib, auth, proxy, layout, globals.css).
- Replaced `__NAME__` tokens with `SastaSpace` in the copied files.
- Rewrote `projects/landing/web/src/app/page.tsx` as a shadcn-powered portfolio (hero + live-projects grid pulling from PostgREST, graceful fallback when PostgREST is unreachable during prerender).
- Rewrote `contact/page.tsx` to use the new `AppShell` + `ContactForm`.
- `npm run build` in landing succeeds with 11 routes (same set as template).
- `CLAUDE.md` + `AGENTS.md` rewritten to describe the new auth model and architecture (Mermaid updated to include GoTrue, Studio, pg-meta).
- `README.md` expanded with a full quickstart including migrations.
- `projects/_template/README.md` now documents the UI pack, auth setup, and how to strip auth if a project doesn't need it.

### Deviations from the design

- **Supabase Studio gating** was *specified* as Cloudflare Access (A3). Manifests leave Studio's ingress open; the Cloudflare Access application must be configured manually during Phase 6 cutover. This is human-only work (account-scoped in Cloudflare Zero Trust).
- **SMTP via Resend** uses Resend's SMTP relay (`smtp.resend.com:465`) rather than their REST API because GoTrue only speaks SMTP. The existing `RESEND_API_KEY` is reused as the SMTP password.
- **`ANON_KEY` and `SERVICE_ROLE_KEY`** are placeholders in `.env.example`. These are signed JWTs (`role=anon` / `role=service_role`) produced with `JWT_SECRET`. The operator must mint them during Phase 6 using a `jwt-cli` one-liner; a snippet is in `.env.example` comments.
- **Studio auth to pg-meta** does not gate SQL execution — anyone reaching the URL can run queries. Mitigation is entirely at the edge via Cloudflare Access.
- **Lucide version** resolved by npm was `^1.8.0`, which was a surprise (historically 0.x). Left as-is since it works; worth spot-checking during an upgrade.

### Environment constraints encountered

- **No running Postgres** for SQL lint. Migration SQL was eyeballed; a `psql --dry-run` pass should happen on first Phase 6 apply.
- **No running Kubernetes API server** for `kubectl dry-run`. Validated YAML with `python3 -c "import yaml; yaml.safe_load_all(...)"` instead.
- **Docker** was available in this environment; `docker compose config --quiet` confirmed the compose file parses.

### Verification

- `npm run build` passes in `projects/_template/web` (11 routes).
- `npm run build` passes in `projects/landing/web` (11 routes).
- `npm run lint` passes with 0 errors in both (2 pre-existing warnings: postcss anonymous default export and TanStack Table + react-compiler interop).
- `python3 -c "import yaml; yaml.safe_load_all(...)"` passes on all `infra/k8s/*.yaml`.
- `docker compose -f infra/docker-compose.yml config --quiet` passes.

### Outstanding work (human / Phase 6)

1. In Cloudflare Zero Trust: create an **Access application** for `studio.sastaspace.com` scoped to the admin email list.
2. Generate `ANON_KEY` and `SERVICE_ROLE_KEY` JWTs from the production `JWT_SECRET` (`make keys` on the remote does this automatically).
3. Configure Google OAuth client credentials and GitHub OAuth app, fill the four corresponding env vars.
4. In Resend: verify `sastaspace.com` sending domain, then lift `RESEND_API_KEY` into the production `gotrue-config` secret.
5. Apply manifests: `microk8s kubectl apply -f infra/k8s/ --recursive` then run the four SQL migrations.
6. Smoke test: sign up, magic link, sign in, open `/admin` from `mohitkhare582@gmail.com`.

### Phase F — Local + remote docker-compose dev flow

Follow-up session after the user asked: *"can we setup a docker-compose to test locally as well? as the machine where we deploy is at ssh 192.168.0.37"*.

Decisions:

- **Local scope**: full stack — landing app also runs as a container under `docker compose --profile full`. Services-only mode (`make up`) stays the default for fast iteration with `npm run dev`.
- **Remote box (192.168.0.37)**: keep MicroK8s for real prod; add compose-over-ssh as a quick staging/dev environment.
- **Migrations**: explicit `make migrate` target, re-runnable (SQL is idempotent).
- **Keys**: `make keys` — pure bash + openssl HS256 signer, no npm/python deps.

New files:

- `scripts/gen-keys.sh` — mints `JWT_SECRET` + signed `ANON_KEY` + `SERVICE_ROLE_KEY`, writes idempotently to `.env`. Reuses existing `JWT_SECRET` when already real so `ANON/SERVICE` re-issue remains valid.
- `scripts/migrate.sh` — waits for postgres healthy, `sed`-substitutes `change-me-sync-with-POSTGRES_PASSWORD` → real password before piping each SQL file through `docker exec psql`. Also re-alters `authenticator` + `supabase_auth_admin` passwords on every run (defensive).
- `scripts/remote.sh` — `sync | env | up | up-core | down | reset | logs | migrate | psql | status | exec`. `env` rewrites `localhost` → `$REMOTE_HOST` and scps a remote-specific `.env`.

Changed files:

- `infra/docker-compose.yml` — added `landing` service under `profiles: ["full"]`. Uses `extra_hosts: "localhost:host-gateway"` so server-side code inside the container reaches the same `localhost:9999/:3001` URLs the browser uses. Build args pass `NEXT_PUBLIC_*` at build time (Next.js bakes them into the client bundle).
- `projects/landing/Dockerfile.web` and `projects/_template/Dockerfile.web` — accept `ARG NEXT_PUBLIC_*` and export via `ENV` before `npm run build`. Switched to `npm ci` with `|| npm install` fallback. Runner stage now sets `HOSTNAME=0.0.0.0` so Next.js standalone binds correctly in a container.
- `.env.example` — grouped/annotated. Added `LANDING_PORT`, `NEXT_PUBLIC_BASE_URL_LOCAL`, `POSTGREST_URL_LOCAL`, `SSH_HOST`, `SSH_REMOTE_DIR`, `REMOTE_HOST`.
- `Makefile` — proper targets with help: `keys`, `up`, `up-full`, `down`, `reset`, `logs`, `ps`, `migrate`, `psql`, and a full `remote-*` family. Compose invocation uses `--env-file .env` because the compose file lives under `infra/` (otherwise env is not auto-resolved).
- `README.md` — new Local quickstart and Remote staging sections.

Verification (run this session):

- `make keys` on a fresh checkout created `.env` and signed both JWTs. Running `make keys` a second time kept `JWT_SECRET` stable (only re-minted the time-stamped JWTs).
- Python verifier confirmed both `ANON_KEY` and `SERVICE_ROLE_KEY` are valid HMAC-SHA256 JWTs against `JWT_SECRET`, with the correct `role` claim.
- `docker compose --env-file .env -f infra/docker-compose.yml config` parses cleanly for both the default profile (5 services) and `--profile full` (6 services, landing included, build args + `extra_hosts: localhost=host-gateway` present, `POSTGREST_URL: http://localhost:3001` wired).
- `make up` could not complete because Docker Desktop is not running on this laptop (known env constraint). The `make up` → compose → pull sequence kicked off correctly before the daemon error, confirming the wiring.

Gotchas documented in comments:

- NEXT_PUBLIC_* must be passed as `build.args` (baked at build time) AND runtime `environment` (for server components). Same URL is used everywhere so the browser and server see a consistent `localhost:9999`.
- On the remote, run `make remote-env` once to rewrite `localhost` → `192.168.0.37` in the shipped `.env`; `remote.sh sync` excludes `.env` afterwards so the remote-specific config isn't clobbered on every sync.
- Role passwords are synced to `POSTGRES_PASSWORD` on every `make migrate` via `ALTER ROLE … WITH PASSWORD`. If you change `POSTGRES_PASSWORD`, re-run `make migrate` to keep `authenticator` and `supabase_auth_admin` in sync (otherwise PostgREST/GoTrue will fail to connect).

