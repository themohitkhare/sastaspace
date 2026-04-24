# Design Log 005 — Almirah: auth gate + local Gemma 4 vision

**Status:** Implemented — pending deploy + real-photo soak
**Date:** 2026-04-24
**Owner:** @mkhare
**Session:** Claude Code (continuation of 004 after design pivot)

---

## Pivot recorded

Log 004 scoped Almirah as a *household* wardrobe. The Claude Design session pivoted to **personal only** with a deferred "plan-with-a-friend" v2, and shifted the atomic unit from *outfits* → *items* (ecommerce SKU-style grid, closet-as-a-rack visual). This log records the resulting implementation against that pivot.

Concretely: no `households` / `household_members` tables in v1. Auth gates a single user to their own closet. Sharing-with-one-other-person lives behind a "plan with a friend · coming in v2" stub in `/me`.

## Auth

Almirah opts fully into the shared SastaSpace auth stack.

- **Supabase GoTrue** at `https://api.sastaspace.com` (browser) and `http://gateway.sastaspace.svc.cluster.local:8000` (server-side, cluster-internal).
- `@supabase/ssr` on the Next side with `AUTH_COOKIE_NAME = "sb-sastaspace-auth-token"` (matches landing, so sessions survive a future cross-project flow).
- `src/proxy.ts` refreshes the session on every request and redirects any unauthenticated hit of a non-public route to `/signin?next=...`. Public paths: `/signin`, `/auth/*`, `/api/health`.
- `/signin` offers Google OAuth + email magic link. Both return to `/auth/callback?next=<original>` which exchanges the code and redirects home.
- `/auth/sign-out` is a `POST` route; hitting it clears the session and returns to `/signin`.
- Server-side route handlers that need the current user call `getSessionUser()` from `src/lib/supabase/auth-helpers.ts`. `/api/tag-image` refuses with 401 when not signed in.

## Vision / tagging via Gemma 4 (cluster-local)

We do **not** call Anthropic from Almirah. All vision/tagging goes through the cluster's own **LiteLLM proxy**, which routes every model name (including Claude-shaped ones) to **`gemma4:31b` via Ollama at `10.0.1.1:11434`**.

- Anthropic-compatible endpoints are exposed at `http://litellm.litellm.svc.cluster.local:4000` with `anthropic_proxy.enabled: true`.
- Almirah points the official `@anthropic-ai/sdk` at this base URL via `LITELLM_BASE_URL` + `LITELLM_API_KEY`. No code change is needed to swap back to real Anthropic — just flip env vars.
- `src/lib/almirah/litellm.ts` exposes `tagOutfitImage(base64, mediaType)` which prompts the model for a strict JSON response describing visible garments (kind / colour / fabric-hint), dominant colours, style family, occasion hint, and people count. Indian vocabulary (kurta, saree, dupatta, lehenga, sherwani, kurti, salwar, churidar, dhoti, juttis) is first-class in the prompt.
- The model is named via the Claude-shaped alias (`claude-haiku-4-5-20251001`) rather than `gemma4-31b` so a future provider switch doesn't ripple through the codebase.
- `POST /api/tag-image` takes a `multipart/form-data` upload with an `image` field (JPEG/PNG/WebP/GIF, ≤8 MB), runs the tagger, and returns the structured result.
- `/onboarding` is wired end-to-end: user picks N photos → each one is sent to `/api/tag-image` serially → structured result rendered inline. This is the live ingest loop without DB persistence yet.

### Why LiteLLM and not direct Ollama

- Anthropic protocol compatibility means the Anthropic SDK works as-is, with full TS types + streaming.
- Master-keyed access control without per-pod auth.
- Free drop-down path to real Anthropic for comparison runs.
- Per-model `num_ctx` tuning lives centrally in the `litellm-config` ConfigMap.

## What remains from log 004

- **Database persistence for items.** The current flow returns tags to the browser and never writes them. Next pass: a `project_almirah` schema (items, wears, events, planner_runs) + RLS, and a writer in `/api/ingest` that replaces `/api/tag-image`. The existing seed `ITEMS` in `src/lib/almirah/items.ts` stays until real data can back the browse screens.
- **Supabase Storage** for the original photos.
- **Embeddings** for "similar outfits" / "complete the look" ranking. Open question per log 004.
- **Segmentation** (one crop per visible item). v1 relies on the whole photo + a structured tag list — no per-item crops.
- **Deploy.** The `.github/workflows/deploy.yml` now has an almirah build block. Still owed manually: create `almirah-runtime` secret on the cluster with the Supabase + LiteLLM keys, and add the `almirah.sastaspace.com` Cloudflare DNS + tunnel public-hostname entries.

## One-shot to bootstrap the cluster secret

```bash
# from your local machine, with kubectl context set to the prod cluster
kubectl -n sastaspace create secret generic almirah-runtime \
  --from-literal=NEXT_PUBLIC_SUPABASE_URL="https://api.sastaspace.com" \
  --from-literal=NEXT_PUBLIC_SUPABASE_ANON_KEY="$(kubectl -n sastaspace get secret landing-runtime -o jsonpath='{.data.NEXT_PUBLIC_SUPABASE_ANON_KEY}' | base64 -d)" \
  --from-literal=SUPABASE_SERVICE_ROLE_KEY="$(kubectl -n sastaspace get secret landing-runtime -o jsonpath='{.data.SUPABASE_SERVICE_ROLE_KEY}' | base64 -d)" \
  --from-literal=LITELLM_API_KEY="<paste from litellm-config master_key>"
```

After creating the secret, nudge the deploy: `git push origin <branch>` and the workflow rolls `almirah`.

## Verification path

- `npm run build` clean, `npx eslint .` clean.
- Local dev with `.env.local` pointing `LITELLM_BASE_URL` at a port-forwarded litellm service: upload one outfit JPEG, get a JSON tag result inline on `/onboarding`.
- After deploy: hit `/api/health` (public) → 200; hit `/` unauthenticated → 302 to `/signin?next=/`; hit `/signin` → renders; magic-link round-trip sets the cookie; `/` renders the rack.

## References
- Log 004 for scope, taxonomy, personas
- `infra/k8s/landing.yaml` — the envFrom + gateway pattern almirah mirrors
- LiteLLM config map (`kubectl -n litellm get cm litellm-config -o yaml`) for the model routing
- `brand/BRAND_GUIDE.md` for the aesthetic invariants
