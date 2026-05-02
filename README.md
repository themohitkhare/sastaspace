# Threadly

> Your wardrobe, finally working for you.

Threadly is an AI stylist that knows every piece you own. Snap your clothes, get outfit suggestions every morning, and shop only what fits what you already have.

This repo contains the marketing site and waitlist backend. Product app code lives elsewhere.

## Layout

```
threadly/
├── web/                  # marketing landing page (single static HTML)
│   └── index.html
└── workers/
    └── waitlist/         # Cloudflare Worker capturing waitlist signups
        ├── src/index.ts
        ├── wrangler.toml
        └── README.md
```

## Run the site locally

The landing page is a single self-contained file. Serve it with anything:

```sh
npx serve web
# or: python3 -m http.server -d web 8000
```

## Deploy

**Site** — host `web/` on Cloudflare Pages, Netlify, Vercel, or any static host.

**Waitlist worker** — see [`workers/waitlist/README.md`](workers/waitlist/README.md). Quick version:

```sh
cd workers/waitlist
pnpm install
pnpm kv:create          # paste returned KV id into wrangler.toml
pnpm deploy
```

Then update `WAITLIST_ENDPOINT` in `web/index.html` to point at the deployed worker URL.

## License

MIT.
