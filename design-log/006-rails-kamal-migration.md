# Design Log 006 — Migrate from Next.js + MicroK8s to Rails + Kamal (path-routed)

**Status:** Plan — awaiting sign-off on 3 open decisions before Phase 0
**Date:** 2026-04-24
**Owner:** @mkhare
**Session:** Continuation of 004/005 after a day of auth-flow bugs exposed the joint complexity of Next middleware + @supabase/ssr + nginx-ingress forwarding

> **2026-04-24 update after owner feedback:** Switch from subdomain-based routing (`almirah.sastaspace.com`) to **path-based routing** (`sastaspace.com/almirah`). This removes the entire cross-subdomain cookie/CORS/OAuth-redirect-per-host problem class in one cut. Reflected throughout this doc. The old decision D3 (repo shape) remains; D4 (deploy trigger) remains; D1 (frontend strategy) and D2 (database ownership) unchanged. The old subdomain listing decision is now moot.

---

## Background

Current state: two Next.js 16 apps (`projects/landing`, `projects/almirah`) on MicroK8s, fronted by Cloudflare tunnel, with shared Supabase-stack services (Postgres, GoTrue, PostgREST, Studio, pg-meta). Per-project Go API scaffolds exist but none are in use.

Today's bug cluster — origin leak (`0.0.0.0:3000` in `Location` headers), magic-link UI we didn't want, proxy fail-open, cookie-domain split across subdomains, PKCE exchange failing because of the cookie Domain dance — all share a common shape. They live at the joint between Next middleware, `@supabase/ssr` cookie ritual, and nginx-ingress's X-Forwarded-* handling. Each single fix is small; the combined surface is disproportionately fragile for a personal-tool portfolio.

Rails 8 + Kamal collapses most of that joint:
- Session auth is first-class (`authenticate` generator → signed HttpOnly cookies, no SDK glue).
- Kamal's proxy handles multi-host routing, rolling deploys, healthchecks, and SSL auto-renewal on a single Docker host — no k8s, no nginx-ingress ConfigMaps, no "which IP do I forward where".
- Google OAuth via `omniauth-google-oauth2` is ~20 lines.
- System tests via Capybara replace both `smoke.sh` and Playwright-MCP ad-hoc runs.
- One language in every project.

The cost: ~7–10 person-days of focused rewrite + cutover, plus the React-to-ERB/Turbo rewrite of the almirah rack visualisation (which is the one thing that's visually distinctive in our current stack).

## Scope of migration

In scope:
- `projects/landing` → Rails 8 app served at `sastaspace.com/` (root).
- `projects/almirah` → Rails 8 app served at `sastaspace.com/almirah` with the rack UI preserved visually.
- **Single origin** — everything at `sastaspace.com/*`. No more subdomains.
- Deploy target shifts from MicroK8s to Kamal + kamal-proxy on the same host (192.168.0.37). kamal-proxy's `path_prefix` label routes each Rails app to its own container.
- Auth: Rails native sessions, *ordinary* HttpOnly same-origin cookie. No `Domain=.sastaspace.com` dance because there are no sibling subdomains anymore. Google OAuth → one redirect URI, one OAuth client, one place.
- CI/CD: Kamal handles deploys from the dev machine (or a GitHub Actions runner — per decision D4).
- Testing: Minitest + Capybara system tests; `tests/e2e/smoke.sh` stays as a language-agnostic guard rail.

Explicitly preserved:
- **Postgres database server**, unchanged. The `supabase/postgres` image stays (pgvector, PostGIS, pg_cron are all valuable). Rails connects directly via ActiveRecord.
- **LiteLLM + Gemma 4** — the cluster-local AI backend. Rails talks to it via `ruby-anthropic` gem pointed at `LITELLM_BASE_URL`, mirroring the Next.js setup.
- **Cloudflare tunnel** — same tunnel ID, same public hostnames. kamal-proxy replaces nginx-ingress behind it.
- **Brand system** — tokens/colours port directly to `tailwindcss-rails`.
- **Design-log workflow** — this file is a log entry.
- **Single domain** — `sastaspace.com`. Subdomains become paths: `sastaspace.com/almirah`, future projects at `sastaspace.com/<name>`. Legacy `almirah.sastaspace.com` gets a 301 redirect at Cloudflare so any old link still lands correctly.

Out of scope (deleted or ignored):
- Next.js apps (archived in git history, current working copies removed after cutover).
- Go API scaffolds — unused in practice.
- `@supabase/ssr`, `@supabase/supabase-js` — no longer needed.
- MicroK8s, nginx-ingress, all `infra/k8s/*.yaml` — archived post-cutover.
- Supabase GoTrue, PostgREST, Studio, pg-meta pods — Rails subsumes their roles.
- Self-hosted GitHub Actions runner (optional — see decision D4).

## Target architecture

```
Browser  ──►  Cloudflare  ──►  cloudflared (unchanged)
                                   │
                                   ▼
                         kamal-proxy (192.168.0.37:80)
                                   │  path routing by prefix
                ┌──────────────────┼──────────────────┐
                ▼                  ▼                  ▼
        /            /almirah            /<future>
        landing app  almirah app         future apps
        (Puma)       (Puma)              (Puma)
```

All apps run on the same host, same port 80 facing cloudflared, different `path_prefix` labels. One Cloudflare tunnel ingress rule (`sastaspace.com → http://localhost:80`), not one per project.

Data plane:
```
Rails apps ─► Postgres 17 (supabase/postgres image, shared instance)
              ├── public.*            shared (users, projects, admins)
              ├── project_landing.*   owned by landing
              └── project_almirah.*   owned by almirah
Rails apps ─► LiteLLM (cluster-internal) ─► Ollama ─► gemma4:31b
Rails apps ─► Disk-backed Active Storage (mounted volume, backed up to cloud)
```

Auth: Rails session cookie **set on `sastaspace.com`** (same-origin, no `Domain=` attribute needed). Signed+encrypted. Every app reads the same session because they're on the same origin. Google OAuth: one client, redirect URI `https://sastaspace.com/auth/google/callback`. A single shared `public.users` table owned by landing; other apps read via cross-schema query.

**Path-prefix implications for Rails apps** (not-free but well-trodden):
- `config.relative_url_root = "/almirah"` in `config/application.rb` for almirah. Landing is at `/`, no prefix.
- All internal routes are defined normally; Rails prepends the prefix when generating URLs via `*_path` helpers.
- Asset pipeline emits `/almirah/assets/...` automatically via the `relative_url_root` config.
- kamal-proxy passes the full path through; Rails sees `/almirah/items/i05`, matches `items/:id` after stripping the prefix.
- Users deep-link to `sastaspace.com/almirah/item/i05` and it works like any Rails route.

## What path-routing simplifies vs. subdomain routing

| Concern | Subdomain stack (what we just fought) | Path-routed stack (target) |
|---|---|---|
| Session cookie | `Domain=.sastaspace.com`, race with legacy host-only cookies, PKCE verifier lost across subdomains | Ordinary same-origin cookie. Rails default. Done. |
| Google OAuth | Separate `redirect_uri` allow-listing strategy per subdomain (we routed through a central `api.sastaspace.com/auth/v1/callback`) | **One** redirect URI: `sastaspace.com/auth/google/callback`. |
| DNS/Cloudflare ops per new project | CNAME + tunnel public-hostname entry | Nothing. New route mounts at `/newproject` and deploys. |
| Cross-app link | `<a href="https://almirah.sastaspace.com/...">` | `<a href="/almirah/...">` |
| CORS | Potential issue any time two apps talk | Never. |
| Origin leak bugs like today's | Real threat (X-Forwarded-Host → publicOrigin → redirect) | Still exists but there's one origin, one host header, one answer. |

## Open decisions (require sign-off before Phase 0)

### D1 — Frontend strategy for almirah's rack UI

The landing page is simple enough that pure ERB + Turbo works. Almirah's rack UI (horizontal hanger-rod rails with SVG silhouettes, tonal item cards, paper+ink aesthetic) is where the current stack shines.

- **D1a — ERB + Stimulus only.** Rewrite `ItemCard`, the rail scroll-snap behaviour, the stage/hero item in ERB. Horizontal scrolling needs minimal JS (Stimulus controllers). Simplest stack, longest rewrite — 2–3 days of frontend work on almirah alone.
- **D1b — React islands via `vite_rails` or `esbuild-rails`.** Keep the existing `ItemCard`, `item-shapes`, and `rack.tsx` as React. Render via `<%= react_component "..." %>` helper. Rails owns routing + data; React owns just the visual layer. Shortest rewrite (~1 day for almirah), preserves visual polish, but now you have both Ruby and TS in one project again — partially defeats the "one language" pitch.
- **D1c — Hybrid: ERB by default, React islands only where they demonstrably win.** Landing stays pure ERB. Almirah gets React only for the rail/item-card/rack components. Profile preferences, me page, settings — ERB. Most pragmatic; roughly 1.5 days of almirah frontend work.

**Recommendation: D1c.** Get the "one language" wins where they matter (landing, settings pages, auth surfaces) and keep the differentiated visual work in React where it's already polished.

### D2 — Database ownership

- **D2a — Keep `supabase/postgres` image; Rails connects directly.** No data migration. ActiveRecord owns schema changes going forward. Drop only the GoTrue/PostgREST/Studio/pg-meta pods. All 50+ extensions (pgvector, PostGIS, pg_cron, pg_graphql) stay available.
- **D2b — Move to vanilla Postgres 17 in a Kamal accessory.** Clean cut from Supabase. Re-enable the extensions we actually use (pgvector). 1 day of data move, small long-term gain.

**Recommendation: D2a.** Zero-risk, preserves the shared extension surface, the `supabase/postgres` image is a Postgres 17 that happens to have plugins — no Supabase vendor lock-in there.

### D3 — Repo shape

- **D3a — Keep monorepo at `sastaspace/`; Rails apps live at `projects/landing/` and `projects/almirah/`.** Same layout as today, just replace the `web/` + `api/` subtrees with a single Rails root per project.
- **D3b — One repo per project.** `github.com/themohitkhare/sastaspace-landing`, `.../sastaspace-almirah`. Each deploys independently. Loses the "single `git push` redeploys everything" convenience but removes cross-project coupling.

**Recommendation: D3a.** The monorepo has been serving you well; the per-project Kamal config lives inside each `projects/<name>/` and is fully independent even inside one repo.

### D4 — Deploy trigger

- **D4a — Kamal from local dev machine.** `cd projects/almirah && kamal deploy`. No CI needed. Deploy on push to main.
- **D4b — GitHub Actions workflow that runs `kamal deploy` from a runner.** Same self-hosted runner on 192.168.0.37, or a fresh ubuntu-latest public runner that SSHes in.
- **D4c — Both.** Local is always available; CI as the default.

**Recommendation: D4a initially, add D4b later if pain.** For a personal portfolio on a home server, `kamal deploy` from your laptop is *simpler and faster* than CI. Most frustrations with today's CI (builds in a sudo shell, runner on the prod host, image pushes to localhost:32000) disappear.

## Phased execution plan

Each phase ends with a working, deployable checkpoint. Old Next.js stack stays running until cutover — per-project — so you can A/B.

### Phase 0 — Foundation (1 day)

1. Write `projects/_rails_template/` — a Rails 8 scaffold with Tailwind, omniauth-google-oauth2 pre-wired, Kamal config templated, a seed migration for `public.users` + `public.sessions`.
2. Port brand tokens into `tailwindcss-rails` config (direct copy of `brand/tokens.css` → tailwind theme).
3. Capybara system-test harness with one smoke test: `visit "/sign-in" && click_on "Continue with Google"` asserts 302 to Google.
4. Test-first: every migration step below gets at least one failing Rails system test before implementation. The TDD discipline from earlier in this session stays.

Deliverable: `rails new` + `kamal init` produces a deployable hello-world at `hello.sastaspace.com` in ≤ 1 hour.

### Phase 1 — Landing at `sastaspace.com/` (2 days)

1. `projects/landing-rails/` scaffolded from the template. Mounted at root (no `relative_url_root`).
2. **One page, one card-per-project.** Data lives in `public.projects` as today; read via ActiveRecord. Project cards now link to `/<slug>` not `https://<slug>.sastaspace.com`.
3. Google OAuth → user row in `public.users`. Admin gate uses the existing `public.admins` allowlist table. Single redirect URI: `https://sastaspace.com/auth/google/callback` (update Google Cloud Console as part of this phase).
4. Copy the current landing visual exactly — ERB templates rendering the same markup pattern as `projects/landing/web/src/app/page.tsx`.
5. Kamal config: single host `sastaspace.com`, kamal-proxy serves plain HTTP behind cloudflared (TLS remains at Cloudflare).
6. **Deploy to a separate path first** — `sastaspace.com/v2` or similar staging mount, A/B against existing landing pod, cut over when green.
7. Cutover = swap the Cloudflare tunnel ingress for `sastaspace.com` from the current k8s service to `kamal-proxy:80` on the host. Single atomic change.

Deliverable: `sastaspace.com` served by Rails via kamal-proxy; old `landing` deployment scaled to 0 replicas (not deleted).

### Phase 2 — Almirah at `sastaspace.com/almirah` (4 days)

1. `projects/almirah-rails/` scaffolded. `config.relative_url_root = "/almirah"` in place before any route work.
2. **Rack/item/ingest data model** — new ActiveRecord migrations under schema `project_almirah`. Tables: `items`, `outfits`, `outfit_items` (join), `wear_events`, `ingest_jobs`.
3. **Seed the 26 existing items + gap suggestions** from `projects/almirah/web/src/lib/almirah/items.ts` via a one-shot Rake task. Keeps the current browse experience working on day 1.
4. **Frontend per D1 decision** — either ERB-only (D1a), React islands (D1b), or hybrid (D1c).
5. `POST /almirah/api/tag_images` using `ruby-anthropic` gem against `LITELLM_BASE_URL` (identical behaviour to current `/api/tag-image`).
6. `POST /almirah/ingest` accepts bulk uploads, enqueues a Solid Queue job per image, writes back to `items`.
7. System tests: sign in via stubbed Google on `sastaspace.com`, navigate to `/almirah`, see at least one seed item, upload a fixture image, confirm an item row appears.
8. Kamal adds a second service with `path_prefix=/almirah` label to the same kamal-proxy. No second Cloudflare entry needed.
9. Cutover: no visible URL change from the user's perspective until we delete the almirah subdomain. Soft-cut by pointing `almirah.sastaspace.com` to a Cloudflare 301 redirect to `sastaspace.com/almirah`, or leave the old hostname serving the old Next app during the bake-in period.
10. Eventually delete the `almirah.sastaspace.com` Cloudflare hostname + DNS record once traffic is drained.

Deliverable: `sastaspace.com/almirah` served by Rails. Old almirah pod scaled to 0. Old subdomain kept as a 301 for 30 days, then removed.

### Phase 3 — Cutover hygiene (0.5 day)

1. Delete scaled-down k8s Deployments + Services after 48h of Rails stability.
2. Delete GoTrue, PostgREST, Studio, pg-meta deployments — nothing uses them anymore.
3. Keep Postgres pod running. (It's still the one database; Rails connects to it.)
4. Update `.github/workflows/deploy.yml` — remove landing/almirah image builds; optionally replace with a Kamal trigger per D4.
5. Delete `projects/landing/` and `projects/almirah/` Next.js directories. Rename `projects/landing-rails/` → `projects/landing/`, same for almirah.
6. Update `CLAUDE.md` for the Rails conventions.

### Phase 4 — Template + scaffold.sh for next project (0.5 day)

1. `projects/_template/` replaced with a Rails 8 template.
2. `scripts/new-project.sh` rewritten: `rails new` + `kamal init` + Cloudflare hostname + DNS CNAME in one command.
3. Decommission `scripts/k8s-deploy.sh` and `scripts/remote.sh`.

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| React-island tooling in Rails (vite_rails, esbuild-rails) turns out clunky | Medium | Decide D1c up front; fall back to D1a if D1c sprawls past a day |
| Cutover breaks shared cookies mid-flight (users logged out) | Low | Expected. Test users get one forced re-login at cutover. Communicate by — there are no users. |
| LiteLLM / ruby-anthropic compatibility gap | Low | LiteLLM exposes the Anthropic protocol; ruby-anthropic speaks it. One integration test in Phase 2.5. Fallback: a thin Ruby wrapper around a raw HTTP call. |
| Active Storage on host disk fills up | Medium-long | Monitor. Switch to S3-compatible storage (Backblaze B2 or Cloudflare R2) when >10 GB. Swap is one `config/storage.yml` line. |
| Kamal + Cloudflare-proxied hostname fights over cert issuance | Medium | Kamal-proxy serves plain HTTP behind the Cloudflare tunnel exactly like today's setup. Do not enable kamal-proxy's letsencrypt mode; let Cloudflare handle TLS. |
| "Two stacks in parallel during migration" eats disk/CPU on 192.168.0.37 | Low | Dedicated check: `df -h && top`. The old Next.js pods idle at ~100Mi each; room exists. |

## What I'm explicitly NOT doing

- **Not moving off Cloudflare.** Tunnel + DNS stay.
- **Not moving off Postgres.** Schema migrates in place; same DB server.
- **Not adding Redis unless Solid Queue wants it.** (Rails 8 Solid Queue uses Postgres by default — one fewer moving part.)
- **Not rewriting the brand system.** Tokens port directly.
- **Not re-doing today's auth design.** Shared-cookie on `.sastaspace.com`, unified sign-in page on `sastaspace.com`, `next=` redirect handoff — all that UX carries forward unchanged. The *implementation* under it gets simpler.
- **Not migrating the design-log or brand/ directories.** They live at the repo root and are stack-agnostic.

## Acceptance criteria

Migration is "done" when all of these hold for at least 72 hours:

1. `tests/e2e/smoke.sh` (rewritten for path-routing) passes against `sastaspace.com/` and `sastaspace.com/almirah`, both served by Rails.
2. Google sign-in works at `sastaspace.com/sign-in`; the resulting session is valid at both `/` and `/almirah` (trivially true — same origin).
3. `sastaspace.com/almirah/onboarding` accepts an image upload and returns a tagged result (unchanged behaviour from today's `almirah.sastaspace.com/onboarding`).
4. `sastaspace.com` lists both projects and reads from `public.projects`; project cards link to `/almirah` not the old subdomain.
5. `almirah.sastaspace.com` returns a Cloudflare 301 redirect to `sastaspace.com/almirah` for old-link compatibility.
6. No `localhost:32000` images in `kubectl get pod -n sastaspace` other than Postgres itself.
7. Old Next.js source deleted from `projects/`, archived only in git history.
8. `CLAUDE.md` reflects Rails + path-routing conventions.

## Time estimate

Total: **7–9 person-days** if execution is linear.
Landing and almirah can overlap — realistic **5–7 calendar days** with parallelism.

## Next actions

Before I start Phase 0, please sign off on D1/D2/D3/D4 (or counter-propose). If you accept my recommendations as-is, just say "go with recommendations" and I'll scaffold Phase 0.

## References
- Log 001 — Project-bank foundations (why the Supabase stack was chosen)
- Log 004 — Almirah design (item-level atoms, rack UI)
- Log 005 — Current auth + Gemma vision wiring (what we're replacing)
- `brand/BRAND_GUIDE.md` — tokens + invariants (port as-is)
- Kamal docs: https://kamal-deploy.org/docs/
- Rails 8 auth generator: https://guides.rubyonrails.org/security.html#authentication
- Omniauth Google OAuth2: https://github.com/zquestz/omniauth-google-oauth2
