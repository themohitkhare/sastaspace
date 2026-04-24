# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SastaSpace is a project-bank monorepo for building and showcasing multiple small projects on the `sastaspace.com` domain.

- Root portfolio: `projects/landing` (Rails 8, served at `sastaspace.com/`)
- Per-project deploy target: `sastaspace.com/<name>` (path-routed — design-log 006)
- Shared database: `supabase/postgres` (MicroK8s pod) with 50+ extensions
- Rails native sessions handle auth (OmniAuth Google OAuth2, Rails 8 authenticate generator); GoTrue / PostgREST / Studio pods from the old Next.js era are idle pending removal.

## Build & Dev Commands

### Local shared services (Docker Compose)

```bash
make keys          # one-time: generate .env with JWT_SECRET + ANON_KEY + SERVICE_ROLE_KEY
make up            # start postgres, postgrest, gotrue, pg-meta, studio
make up-full       # same + landing app as a container
make migrate       # apply db/migrations/*.sql in order
make verify        # end-to-end assertion suite (57 checks)
make psql          # psql shell into the postgres container
make down          # stop containers (keep data)
make reset         # stop + wipe volumes
```

### Per-project development (Rails 8)

```bash
cd projects/<name>
bundle install                  # first time
bin/rails server                # dev at http://localhost:3000 (landing) or /<name> for path-prefixed apps
bin/rails test                  # unit tests
bin/rails test:system           # Capybara system tests
bin/rubocop                     # lint (omakase preset)
bin/brakeman --no-pager         # static security scan
```

Database config lives in `config/database.yml` and reads `POSTGRES_URL` in production / `DATABASE_URL` or the default `postgres://postgres:postgres@localhost:5432/sastaspace` locally. Each app is a fresh `rails new` scaffold with Tailwind-Rails, Propshaft, Solid Queue, Solid Cache and OmniAuth preconfigured.

### Scaffold a new project

```bash
# Copy the _template with a name substitution. scripts/new-project.sh is
# out of date post-Rails migration — prefer the manual rsync form below.
rsync -a --exclude 'vendor/bundle' --exclude 'tmp/' --exclude 'log/' \
  projects/_template/ projects/<name>/
( cd projects/<name> && \
  find . -type f \( -name '*.rb' -o -name '*.yml' -o -name '*.erb' -o -name 'Dockerfile' -o -name 'Gemfile*' \) \
    -exec sed -i.bak "s/__NAME__/<name>/g" {} \; && \
  find . -name '*.bak' -delete )
```

### Remote / production host (192.168.0.37)

The remote box is the production host. It runs MicroK8s, and a Cloudflare tunnel (`cloudflared`) fronts `*.sastaspace.com` — no public IP or open ports. The `make remote-*` targets drive a Docker Compose side channel on the same box for quick iteration without going through the full k8s deploy.

```bash
make remote-env      # rewrite .env for remote host
make remote-up       # rsync + docker compose up on remote (compose side channel)
make remote-migrate  # apply migrations on remote
make remote-psql     # psql into remote postgres
```

### CI/CD

Single workflow `.github/workflows/deploy.yml` triggers on push to `main` **or `develop`**. The self-hosted runner lives on the production host (192.168.0.37) and: builds each project's Docker image, pushes to the MicroK8s-local registry (`localhost:32000`), applies shared + per-project k8s manifests (`projects/*/k8s.yaml`, globbed), then does a rolling restart with a 300s rollout check. Both branches deploy to the same cluster today; there is no separate staging namespace. No separate lint/test CI jobs yet.

New projects need one manual edit to the workflow — a `Build <name> image` + `Push <name> image` block per project — because Dockerfiles and build contexts vary. The apply + rollout steps pick up `projects/<name>/k8s.yaml` automatically via the glob.

**First-push-to-a-new-branch quirk.** If a push to a brand-new branch *also* introduces the `on:` trigger for that branch in the workflow file (the classic bootstrap situation), GitHub occasionally doesn't auto-trigger the run. Workaround: `gh workflow run deploy.yml --ref <branch>` once — the next push onward auto-triggers normally.

### Git flow

- `main` — production. Anything here should have been deployed and verified.
- `develop` — integration. Both branches deploy to the same cluster via the CI/CD workflow above; there is no separate staging environment today, so "land on develop" and "land on main" are effectively the same blast radius.
- Feature branches — named after what they do. Merge `--ff-only` into `develop` when ready, then fast-forward into `main` when you want the canonical tip to move. Don't rebase shared branches; don't force-push `main` or `develop`.
- When in doubt, develop → main is the safer path than feature → main directly, so the CI run on develop catches problems before they touch production-tagged history.

### Deploying a Rails app manually

CI wires the automatic path on push to `main`/`develop`. This is the direct recipe — identical shape for all Rails apps, rsync-then-build on the host to avoid cross-arch pain:

```bash
ssh 192.168.0.37 "mkdir -p /tmp/<name>-deploy"
rsync -az --exclude 'vendor/bundle' --exclude 'tmp/' --exclude 'log/' \
  projects/<name>/ 192.168.0.37:/tmp/<name>-deploy/

ssh 192.168.0.37 'cd /tmp/<name>-deploy && \
  TAG=$(date -u +%Y%m%d-%H%M%S) && \
  docker build \
    -t localhost:32000/sastaspace-<name>:$TAG \
    -t localhost:32000/sastaspace-<name>:latest . && \
  docker push localhost:32000/sastaspace-<name>:$TAG && \
  docker push localhost:32000/sastaspace-<name>:latest && \
  sudo microk8s kubectl apply -f k8s.yaml && \
  sudo microk8s kubectl -n sastaspace rollout restart deploy/<name>-rails && \
  sudo microk8s kubectl -n sastaspace rollout status   deploy/<name>-rails --timeout=180s'

# 2. DNS + tunnel public hostname — same keychain token (it has both scopes)
CF_TOKEN=$(security find-generic-password -a sastaspace -s cloudflare-api-token -w)
ZONE=f90dcc0f12180c1d2b5fb5d488887c24      # sastaspace.com
ACCOUNT=c207f71f99a2484494c84d95e6cb7178   # 32 hex chars — verify from
                                            #   curl /client/v4/zones/$ZONE | .result.account.id
                                            # Do NOT decode the tunnel token in your head; it's easy to
                                            # mis-transcribe and the API returns 7003 "Could not route"
                                            # for any typo, which looks like a permissions error.
TUNNEL=b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8

# 2a. CNAME the subdomain at the tunnel
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  --data "{\"type\":\"CNAME\",\"name\":\"<name>\",\"content\":\"$TUNNEL.cfargotunnel.com\",\"proxied\":true}"

# 2b. Add the public hostname to the tunnel ingress (ORDERED list; the trailing
#     {"service":"http_status:404"} catch-all must stay last)
CFG=$(curl -sS "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" \
       -H "Authorization: Bearer $CF_TOKEN")
echo "$CFG" | python3 -c '
import json,sys
d = json.load(sys.stdin)
cfg = d["result"]["config"]
ing = cfg["ingress"]
if not any(r.get("hostname") == "<name>.sastaspace.com" for r in ing):
    idx = next(i for i,r in enumerate(ing) if "hostname" not in r)
    ing.insert(idx, {"service": "http://localhost:80", "hostname": "<name>.sastaspace.com"})
json.dump({"config": cfg}, open("/tmp/cfg-new.json","w"))
'
curl -X PUT "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" --data @/tmp/cfg-new.json
```

Remote `~/sastaspace` often lags behind `main`. Don't rsync the whole tree to the remote unless you intend to sync the repo — build out of `/tmp/<name>-deploy/` instead.

### Cloudflare tunnel — managed tunnel + account-scoped API token

The tunnel `sastaspace-prod` (ID `b3d36ee8-8bd2-4289-83a0-bf2ab53aa3b8`) is a **Cloudflare-managed / remote-config** tunnel — it runs via `cloudflared --token …` under systemd, with no `cert.pem` on the host, so the `cloudflared` CLI can't edit it locally. Config lives in Cloudflare's side (`config_src: cloudflare`), accessed at `GET|PUT /accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations`.

The keychain token (`cloudflare-api-token`) has **both** zone-DNS and account-tunnel permissions. The current ingress list is ordered and looks like:
```
sastaspace.com, www.sastaspace.com, api.sastaspace.com, tasks.sastaspace.com,
monitor.sastaspace.com, llm.sastaspace.com, <your new host>, http_status:404 (catch-all)
```

Gotchas that cost real time on this repo:

- A malformed account ID (e.g. an extra hex char pulled from hand-transcribing the base64-decoded tunnel token) returns `7003 Could not route to /client/v4/accounts/<id>/cfd_tunnel/... perhaps your object identifier is invalid?` — the error reads like a permissions issue but is almost always a bad ID. Pull the correct account ID straight from `GET /zones/{zone}/.result.account.id` instead of decoding the token manually.
- Without a matching public-hostname row on the tunnel, a new subdomain returns **HTTP 404 from Cloudflare** even with a correct CNAME and a healthy ingress on the node. `server: cloudflare`, empty body — the tunnel drops the request before it reaches ingress-nginx.
- The `ingress` array is **ordered**. Always insert new hostnames before the trailing catch-all (the entry with no `hostname` field), never after.

### New project — end-to-end checklist

Path-routed — every project mounts at `sastaspace.com/<name>`. No new subdomain, no new Cloudflare hostname, no DNS change.

1. **Design log first.** `design-log/NNN-<name>.md` — scope, what shared infra you opt in to (users table? LiteLLM?), what data you need.
2. **Brand compliance.** Read `brand/BRAND_GUIDE.md` before writing any UI. Invariants that have bitten recent projects: no gradients/shadows/glows, only 400/500 font weights, paper (`#f5f1e8`) not white as the page bg, sasta orange used in ≤4 accent places (never body text). Code review rejects violations.
3. **Scaffold.** Rsync `projects/_template/` → `projects/<name>/` and substitute `__NAME__` (see "Scaffold a new project" above).
4. **Build the project.** Pure Rails 8. Scope routes under `/<name>` so incoming requests match without `SCRIPT_NAME` trickery. Point `RAILS_RELATIVE_URL_ROOT=/<name>` so asset URLs and redirects prepend correctly.
5. **Verify locally.** `bin/rails test && bin/rails test:system && bin/rubocop` before committing.
6. **Per-project manifest.** `projects/<name>/k8s.yaml` — Deployment + Service. Model it on `projects/landing/k8s.yaml` (for a root-path app) or `projects/almirah/k8s.yaml` (for `/name`-scoped). Image: `localhost:32000/sastaspace-<name>:latest`.
7. **Create the runtime Secret.** Per-app secret named `sastaspace-rails-<name>-runtime` holding `RAILS_MASTER_KEY`, `SECRET_KEY_BASE`, and any third-party keys; `POSTGRES_PASSWORD` comes from the shared `postgres-credentials` secret via `secretKeyRef`.
8. **Ingress path.** Add a new path rule to `infra/k8s/ingress.yaml` under the `sastaspace.com` host — `/<name>` → `<name>-rails:3000` — *before* the catch-all `/` rule. Re-apply: `kubectl apply -f infra/k8s/ingress.yaml`.
9. **Wire the CI build.** Add a `Build <name> image` step in `.github/workflows/deploy.yml`. The `apply` + `rollout` steps glob `projects/*/k8s.yaml` already.
10. **Land on `develop`** via fast-forward; CI deploys; smoke-test `https://sastaspace.com/<name>`. FF `develop` → `main` when you're confident.

### Known fragile spots

- Account ID typos read like permission errors (Cloudflare 7003). Always pull the account ID from `/zones/{zone}/.result.account.id`, never hand-decode the base64 tunnel token.
- `~/sastaspace` on the prod host is a separate clone and is often on a different branch from your local tip. `scripts/k8s-deploy.sh` and `scripts/remote.sh` do some rsyncs that assume the remote matches local — don't use them mid-flight if you're on a feature branch. Build out of `/tmp/<name>-deploy/` for feature-branch deploys.
- The Rails image's Dockerfile `ENTRYPOINT` runs Puma through [thruster](https://github.com/basecamp/thruster); thruster binds its HTTP port from `HTTP_PORT` (default 80 — fails under non-root k8s user 1000 with "permission denied"). Set `HTTP_PORT=3000`, `TARGET_PORT=3001`, `PORT=3001` in the k8s env (Rails listens on 3001 behind thruster on 3000). The k8s Service uses port 3000 to hit thruster.
- Rails `config.relative_url_root = "/name"` only rewrites **generated** URLs; it does *not* strip the path from incoming requests. Route matching requires `scope path: "/name"` in `config/routes.rb` — otherwise `/name/up` 404s even though the route table shows `get "up"`.
- Asset precompile needs `SECRET_KEY_BASE_DUMMY=1` in the Dockerfile's `RUN bin/rails assets:precompile` step so it can boot without the real master key. The runtime container receives `RAILS_MASTER_KEY` via the runtime Secret.

## Tech Stack

- Framework: Rails 8 (ERB + Turbo + Tailwind-Rails + Propshaft + Solid Queue + Solid Cache)
- Ruby: 4.0.3
- Database: Postgres (`supabase/postgres`) with pgvector, PostGIS, pg_cron, pg_graphql, etc. Still runs in MicroK8s.
- Auth: Rails 8 `authenticate` generator (HttpOnly signed+encrypted session cookie) + OmniAuth Google OAuth2
- Deployment: MicroK8s on 192.168.0.37 (`taxila`), fronted by `cloudflared` tunnel. Nginx-ingress does path-based routing so `sastaspace.com/<name>` hits `<name>-rails:3000`. No public IP, no open ports.
- LLM: LiteLLM (in-cluster) in front of Ollama / Gemma 4, reachable at `http://litellm.sastaspace.svc.cluster.local:4000`
- CI/CD: `.github/workflows/deploy.yml` via a self-hosted runner on taxila. Builds Rails images, pushes to `localhost:32000`, applies `projects/*/k8s.yaml` + `infra/k8s/*.yaml`, rolling-restart on each Deployment.

## Repository Layout

- `infra/k8s/` - shared Postgres, PostgREST, GoTrue (legacy), pg-meta (legacy), ingresses, almirah-subdomain-redirect
- `infra/docker-compose.yml` - local mirror of shared services
- `db/migrations/` - legacy SQL migrations (extensions, admin allowlist, RLS helpers). Rails apps now own their own ActiveRecord migrations under `projects/<name>/db/migrate/`.
- `projects/_template/` - Rails 8 scaffold with auth, Tailwind, Propshaft, Kamal configs stripped
- `projects/landing/` - Rails 8 app at `sastaspace.com/`
- `projects/almirah/` - Rails 8 app at `sastaspace.com/almirah`
- `scripts/` - key-gen, migrations, verify, scaffolder (needs Rails-era rewrite)
- `design-log/` - design decisions and implementation history

## Conventions

- Project folders use kebab-case: `projects/my-project`.
- Per-project Rails schema (when using shared Postgres): `project_<name>` (Rails migrations create it; AR models set `self.table_name = "project_<name>.<table>"`).
- Per-project manifests in `projects/<name>/k8s.yaml` (Deployment + Service); shared ingress + legacy pods in `infra/k8s/`.
- Image tag convention: `localhost:32000/sastaspace-<name>:latest` (plus `<sha>` or `<timestamp>` for immutable pins).
- No secrets in git: Rails `config/master.key` is gitignored and lives in macOS Keychain (`rails-master-key-<name>`). Per-app k8s runtime secrets are `sastaspace-rails-<name>-runtime`. Postgres password comes from the shared `postgres-credentials` secret.
- Design log first for significant changes (see `design-log/`).
- Commit message format for task-structured work: `<project>: task <n> — <short>`.
- Branch commits granularly, one commit per task; fast-forward merge feature branches into `develop`.

## Architecture

Single `sastaspace` namespace on MicroK8s. Rails apps are Deployments on the shared cluster; nginx-ingress does path-based routing.

```mermaid
graph TD
    CF[Cloudflare Tunnel]
    subgraph mk8s [MicroK8s · namespace sastaspace]
        ING[nginx-ingress]
        PG[(Postgres)]
        LLM[LiteLLM]
        LAND[landing-rails]
        ALM[almirah-rails]
        APPn[... future Rails apps]
    end
    CF -->|sastaspace.com :80| ING
    ING -->|/ | LAND
    ING -->|/almirah | ALM
    ING -->|/<name> | APPn
    LAND --> PG
    ALM --> PG
    ALM --> LLM
    APPn -.optional.-> PG
```

## Auth Model

- Rails 8 `authenticate` generator: HttpOnly signed+encrypted session cookies scoped to `sastaspace.com` (same-origin for all apps, no `Domain=` dance needed).
- Google sign-in via `omniauth-google-oauth2` with a single redirect URI: `https://sastaspace.com/auth/google/callback`.
- Shared `public.users` table. Admin status is defined by presence in the `public.admins(email)` allowlist.
- Legacy Supabase GoTrue/PostgREST/Studio pods are idle — delete once nothing in the repo or in Cloudflare references them.

## Workflow

For a substantive change (new project, architectural shift): follow the **New project end-to-end checklist** in Build & Dev Commands.

For an incremental change to an existing project:

1. Work on a feature branch, not on `develop` or `main` directly.
2. Keep commits small and task-scoped (`<project>: task <n> — <short>`).
3. Validate locally — `bin/rails test`, `bin/rails test:system`, `bin/rubocop` — before pushing.
4. Fast-forward merge into `develop`; CI deploys automatically. Fast-forward `develop` into `main` once you're confident.
5. Update the design log in `design-log/` when the change is significant enough that a future agent would benefit from the context.

## Testing conventions

Each Rails app ships with Minitest + Capybara (system tests). No extra test runner needed. Conventions:

- Put unit tests in `projects/<name>/test/models/`, system tests in `projects/<name>/test/system/`. The Rails defaults.
- Keep pure-function cores pure. A risk/score/price function that reaches for `Net::HTTP`, `Time.current`, or `SecureRandom` is hard to test deterministically — inject dependencies at the caller.
- System tests run Chrome headless via Selenium. They need a working Postgres — either the Compose one (`make up`) or a local Postgres with `postgres/postgres` creds.

## References

- Foundation design: `design-log/001-project-bank-foundations.md`
- Auth + UI upgrade: `design-log/002-auth-admin-ui-upgrade.md`
- Brand rollout: `design-log/003-brand-rollout.md`
- Rails + MicroK8s migration: `design-log/006-rails-kamal-migration.md` (the "Kamal" name in the title is retained for history — the final deploy target is MicroK8s, not Kamal)
- Root quickstart: `README.md`
