# sastaspace

> A sasta lab for the things I want to build.

Personal project-bank monorepo. The landing page is at `sastaspace.com`; each
experiment ships at `<name>.sastaspace.com`. One SpacetimeDB module backs every
project — same data, same auth, same connection.

## Stack

| Layer | Choice |
|---|---|
| Database + business logic | SpacetimeDB 2.1, Rust module |
| Client framework | Next.js 16 (App Router, static export) + Tailwind v4 |
| Brand layer | `@sastaspace/design-tokens` — single CSS file, five logos |
| Hosting (DB) | Self-hosted Docker on prod box behind Cloudflare Tunnel |
| Hosting (web) | Cloudflare Pages |
| CI | GitHub Actions — module test → publish; landing build → Pages deploy |

## Layout

```
sastaspace/
├── apps/
│   └── landing/                    # Next.js 16 — sastaspace.com
├── module/                         # Rust SpacetimeDB module (the database)
├── packages/
│   ├── design-tokens/              # colours, type, logos
│   └── stdb-bindings/              # generated TS client bindings
├── infra/
│   ├── docker-compose.yml          # SpacetimeDB on prod
│   ├── keygen.sh                   # one-time JWT keypair generator
│   └── cloudflared/                # tunnel ingress recipe
└── .github/workflows/
    ├── module.yml                  # rust test + spacetime publish
    └── landing.yml                 # next build + Cloudflare Pages
```

## Local development

Prereqs: Node 22, pnpm 9, Rust stable + `wasm32-unknown-unknown` target,
Docker, the SpacetimeDB CLI (`curl -sSf https://install.spacetimedb.com | sh`).

```bash
# 1. install
pnpm install

# 2. start a local spacetimedb (separate terminal)
spacetime start

# 3. publish the module to local + generate ts bindings
pnpm module:publish:local
pnpm bindings:generate

# 4. run the landing
pnpm dev
# open http://localhost:3000 — open it in two tabs to see the presence pill go to "2 in the lab"
```

## Deploying

### One-time prod setup

```bash
# from any workstation with the cloudflare-api-token in keychain
infra/cloudflared/add-stdb-ingress.sh         # adds stdb.sastaspace.com to the existing tunnel

# on the prod box
git clone <this repo>
cd sastaspace/infra
./keygen.sh                                   # creates JWT signing keys
docker compose up -d                          # starts spacetimedb on 127.0.0.1:3100

# from a workstation
spacetime server add prod --url https://stdb.sastaspace.com --no-fingerprint
spacetime login --server-issued-login prod
spacetime token export --server prod          # paste into GH secret SPACETIME_TOKEN
```

### GitHub secrets needed

| Secret | Where it comes from |
|---|---|
| `SPACETIME_TOKEN` | `spacetime token export --server prod` after `spacetime login` |
| `CF_API_TOKEN` | Cloudflare dashboard → My Profile → API Tokens → "Cloudflare Pages — Edit" template |
| `CF_ACCOUNT_ID` | `c207f71f99a2484494c84d95e6cb7178` (from your existing keychain note) |

### Continuous delivery

- Push to `main` touching `module/**` → CI runs `cargo fmt/clippy/test`, then publishes to `stdb.sastaspace.com` and uploads regenerated TS bindings as an artifact.
- Push to `main` touching `apps/landing/**` or `packages/**` → CI builds the static site and `wrangler pages deploy`s to Cloudflare Pages.
- After a module publish, the module workflow triggers the landing workflow to rebuild with fresh bindings.

## Brand invariants (enforce these — they're the lab's signature)

- Paper `#f5f1e8` is the page background, **never** pure white.
- Sasta orange `#c05621` is **chrome only** (button fills, chip fills, ≥18px display). For body-sized accents/links use Rust (`var(--brand-sasta-text)`, AAA on paper).
- Two font weights: 400 + 500. **No 600 or 700 anywhere.**
- Two type families: Inter + JetBrains Mono. No Devanagari.
- Sentence case in UI. No ALL CAPS, no Title Case.
- No drop shadows, no gradients, no glows. Borders only — `1px solid var(--brand-dust-40)`.
- No emoji in body copy. No resume metrics.

Full guide: `packages/design-tokens/src/colors-and-type.css` and the original bundle at `/tmp/sastaspace-design/sastaspace-design-system/`.

## Notes

- The landing is statically exported; SpacetimeDB is contacted from the browser only.
- The `presence` table is wiped if the module is re-published with a schema change. That's by design — presence is ephemeral.
- Module bindings live in `packages/stdb-bindings/src/generated/` and are gitignored. CI regenerates them on every module publish; locally, run `pnpm bindings:generate` after publishing.

---

Built sasta. Shared openly. © Mohit Khare, 2026.
