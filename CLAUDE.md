# Threadly

AI wardrobe stylist. This repo contains the marketing site and waitlist backend.

## Layout

- `web/index.html` — single-file static landing page (Fraunces + Inter, vanilla JS, no build step).
- `workers/waitlist/` — Cloudflare Worker that captures waitlist signups into KV.

## Conventions

- Keep `web/index.html` a single self-contained file. No build pipeline. Inline CSS and JS.
- The waitlist worker is the only backend. If you add more workers, drop them in `workers/<name>/` and they'll be picked up by the pnpm workspace automatically.
- The landing page form has a `localStorage` fallback so it stays functional even when the worker is down or the endpoint is misconfigured.
- The `WAITLIST_ENDPOINT` constant in `web/index.html` must match the deployed worker URL.
