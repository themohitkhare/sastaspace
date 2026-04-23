# __NAME__

Project scaffold generated from the SastaSpace project-bank template.

Deploys to `https://__NAME__.sastaspace.com`.

## What's included

- **web/** — Next.js 16 + TypeScript + Tailwind v4 + shadcn/ui
  - Layout shell (Topbar / Sidebar / Footer)
  - Dark mode via `next-themes` with a Light / Dark / System toggle
  - Full shadcn component set (button, input, label, card, form, dialog, dropdown-menu, sheet, tabs, navigation-menu, toast (sonner), skeleton, badge, avatar, separator, table, data-table)
  - Supabase auth wired via `@supabase/ssr` (sign-in, sign-up, forgot-password, OAuth callback, sign-out route)
  - Gated `/admin` area (checks `public.admins` allowlist)
  - `motion` available for tasteful animations
  - Contact form with optional Cloudflare Turnstile + Resend
- **api/** — Go + chi + pgx + sqlc starter (optional; remove if the project is frontend-only)
- **db/migrations/** — per-project schema bootstrap (`0001_init.sql`)
- **Dockerfile.web / Dockerfile.api** — multi-stage production images
- **k8s.yaml** — Deployment + Service + Ingress (`__NAME__.sastaspace.com`)

## Local development

1. From repo root, bring up shared services:
   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```
2. Apply project migrations (once):
   ```bash
   docker exec -i sastaspace-postgres psql -U postgres -d sastaspace \
     < projects/__NAME__/db/migrations/0001_init.sql
   ```
3. Run the web app:
   ```bash
   cd projects/__NAME__/web && npm install && npm run dev
   ```

## Environment

Copy the project's `.env.example` to `.env.local` and set at least:

- `NEXT_PUBLIC_SUPABASE_URL` — usually `http://localhost:9999` in dev, `https://auth.sastaspace.com` in prod
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — signed anon JWT (see design-log/002)

## Customising the look

The design tokens live in `web/src/app/globals.css`. Override `--primary`, `--accent`, etc. to brand the project without touching the template-shared shadcn components.

## Removing the admin area

If this project doesn't need auth, delete:

- `web/src/app/(auth)/`
- `web/src/app/(admin)/`
- `web/src/app/auth/`
- `web/src/components/auth/`
- `web/src/lib/supabase/`
- `web/src/proxy.ts`

...and drop `@supabase/ssr` + `@supabase/supabase-js` from `package.json`.
