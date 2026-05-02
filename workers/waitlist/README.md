# @threadly/waitlist

A tiny Cloudflare Worker that captures waitlist signups for the Threadly landing page (`web/index.html`).

## Endpoints

- `POST /join` — `{ email, source }` → `{ ok: true, position }` (or `{ ok: true, duplicate: true }`)
- `GET /count` — `{ count }`, public signup count

Rate-limited at 5 requests/min per IP. Emails are stored in a single KV namespace, keyed by `email:<lowercase-email>`. A `__count__` key holds the running total.

## Deploy

```sh
cd workers/waitlist
pnpm install

# 1. Create the KV namespace and copy the returned id into wrangler.toml
pnpm kv:create

# 2. Deploy
pnpm deploy
```

Once deployed at `https://threadly-waitlist.<account>.workers.dev`, point the landing page's `WAITLIST_ENDPOINT` constant in `web/index.html` at it.

## Local dev

```sh
pnpm dev
# POST a test signup
curl -X POST http://localhost:8787/join \
  -H 'content-type: application/json' \
  -d '{"email":"test@example.com","source":"local"}'
```

## Notes

- The landing page falls back to `localStorage` when the worker is unreachable, so the form is never broken even without the worker deployed.
- For production, restrict `ALLOWED_ORIGINS` in `wrangler.toml` to your real domains.
- To export the list: `wrangler kv key list --binding=WAITLIST` then `wrangler kv key get --binding=WAITLIST email:<addr>`.
