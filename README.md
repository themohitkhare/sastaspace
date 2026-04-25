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
| Hosting | Both run as docker containers on `taxila` (prod box, 192.168.0.37) behind the existing Cloudflare Tunnel `sastaspace-prod` |
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
│   ├── docker-compose.yml          # spacetime + landing nginx on taxila
│   ├── keygen.sh                   # one-time PKCS#8 JWT keypair generator
│   ├── landing/nginx.conf          # static-site nginx config
│   └── cloudflared/                # tunnel ingress recipe
└── .github/workflows/
    ├── module.yml                  # rust test + spacetime publish
    └── landing.yml                 # next build + rsync to taxila
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

### Live URLs

- `https://sastaspace.com` — landing (nginx on taxila)
- `https://stdb.sastaspace.com` — SpacetimeDB websocket + REST endpoint
- Both routed through the existing `sastaspace-prod` Cloudflare Tunnel

### One-time prod setup (already done as of 2026-04-25)

```bash
# from a workstation with the cloudflare-api-token in keychain
infra/cloudflared/add-stdb-ingress.sh         # adds stdb.sastaspace.com to the tunnel

# on taxila
git clone git@github.com:themohitkhare/sastaspace.git
cd sastaspace/infra
./keygen.sh                                   # creates PKCS#8 ECDSA P-256 keys
mkdir -p data landing/out
docker compose up -d                          # starts spacetime + landing nginx

# from a workstation
spacetime server add prod --url https://stdb.sastaspace.com
spacetime publish --server prod sastaspace --module-path module -y
```

### GitHub secrets needed (for CI)

| Secret | What |
|---|---|
| `SPACETIME_TOKEN` | The `spacetimedb_token` value from your local `~/.config/spacetime/cli.toml`. CI uses it to publish as the same identity that owns the module — without it, the server treats the runner as a stranger and rejects publish. |

That's the only secret. GH workflows run on **self-hosted runners on taxila itself** (`runs-on: [self-hosted, Linux]`), so deploy is a local `rsync` + `docker exec nginx -s reload` — no SSH, no tailscale, no Cloudflare creds.

### About SpacetimeDB "auth" on self-hosted

There's no OAuth-style login. Identities are anonymous JWTs — the first time you `spacetime publish`, the CLI POSTs to `/v1/identity` and the server issues an identity bound to its own JWT signer. That identity becomes the database's `owner_identity`. From that moment on, only requests carrying a token for the same identity can re-publish or `--delete-data`. CI needs the same token, hence `SPACETIME_TOKEN`. There is no "registration" — the JWT is the identity.

### Continuous delivery

- Push to `main` touching `module/**` → CI runs `cargo fmt/clippy/test`, then publishes to `stdb.sastaspace.com` and uploads regenerated TS bindings as an artifact.
- Push to `main` touching `apps/landing/**` or `packages/**` → CI builds the static site, rsyncs to taxila, and reloads nginx.
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
