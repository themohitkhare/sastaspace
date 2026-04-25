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
| `SPACETIME_TOKEN` | `spacetime token export --server prod` (after `spacetime login --server-issued-login prod`) |
| `TAXILA_SSH_KEY` | private SSH key authorized to `mkhare@taxila` (deploy key, ed25519) |
| `TAXILA_SSH_HOST` | the address GH Actions can reach — needs a tailscale-action step or public bastion (taxila is LAN-only by default) |
| `TAXILA_SSH_USER` | `mkhare` |

> **Note**: GH-hosted runners can't reach `192.168.0.37`. Use a tailscale-action
> in the deploy job (`tailscale/github-action@v3`) and set `TAXILA_SSH_HOST` to
> the tailscale hostname. Until then, run `pnpm build && rsync apps/landing/out/
> 192.168.0.37:~/sastaspace/infra/landing/out/` from your workstation.

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
