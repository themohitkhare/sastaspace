# Engineering Audit — `develop`

- **Auditor:** engineering
- **Branch:** `develop`
- **Date:** 2026-04-23
- **HEAD:** `422e2ca4b74d78c2bcb522e15c3da0000259d4ae`
- **Scope:** code quality, types, build/lint/typecheck health, test coverage, perf on `projects/landing/web` + `projects/_template/web`

> **Team-lead note (inserted 2026-04-23):** Auditor-claimed finding P1 "lucide-react pinned to `^1.8.0` — the wrong/stale package" has been verified and is **incorrect**. `npm view lucide-react versions` returns 1.0.0–1.9.0 (latest 1.9.0 published 2026-04-23) under the canonical `lucide-icons/lucide` repo with maintainer `ericfennis`. The `^1.8.0` pin is current. This finding is preserved below for fidelity to the auditor's report but is **withdrawn** in the consolidated `BRAND_REDESIGN_AUDIT.md` (see its P2-4).

## Commands run

| Command | Exit | Notes |
|---|---|---|
| `projects/landing/web $ npx tsc --noEmit` | 0 | Clean, no output. |
| `projects/_template/web $ npx tsc --noEmit` | 0 | Clean, no output. |
| `projects/landing/web $ npx eslint .` | 0 | 0 errors, 2 warnings (postcss anon-default-export; react-hooks/incompatible-library on `data-table.tsx:42` from `useReactTable`). |
| `projects/_template/web $ npx eslint .` | 0 | Same 2 warnings as landing. |
| `projects/landing/web $ npm run build` | 0 | Next 16.2.1 / Turbopack, compiled 1.85s, TS 1.29s. 11 routes (`/`, `/contact`, auth + admin). |
| `projects/_template/web $ npm run build` | 0 | Compiled 1.79s. 12 routes. |

## Files reviewed

Landing (`/Users/mkhare/Development/sastaspace/projects/landing/web/src/**`):
- App routes: `app/layout.tsx`, `app/page.tsx`, `app/globals.css`, `app/contact/page.tsx`, `app/(auth)/*`, `app/(admin)/admin/*`, `app/api/contact/route.ts`, `app/auth/callback/route.ts`, `app/auth/sign-out/route.ts`.
- Components: `components/layout/{topbar,footer,app-shell,sidebar}.tsx`, `components/theme/*`, `components/auth/*`, `components/contact-form.tsx`, `components/projects/project-card.tsx`, `components/ui/status-chip.tsx`, `components/ui/data-table.tsx`, `components/ui/sonner.tsx`.
- Lib: `lib/supabase/{server,client,middleware,cookies,auth-helpers}.ts`, `lib/utils.ts`, `proxy.ts`.
- Config: `package.json`, `tsconfig.json`, `eslint.config.mjs`, `next.config.ts`, `postcss.config.mjs`, `components.json`.

Template (`/Users/mkhare/Development/sastaspace/projects/_template/web/src/**`): parity set of the above + `components/layout/brand-footer.tsx`. Same configs.

`/Users/mkhare/Development/sastaspace/.github/workflows/deploy.yml` — CI calls `npm run build` through `projects/_template/Dockerfile.web`; the script name matches both projects' `package.json`.

## Deliberately skipped

- Brand invariants (palette, type weights, sasta-orange placement) — `brand-security`'s remit. Noted overlap only where relevant to perf (font weights).
- A11y, copy, aria semantics — `ux`'s remit.
- Supabase auth contract correctness and SSR session refresh logic — `brand-security`'s remit.
- Go API in `projects/<name>/api/` (none present in landing/template today).

## Findings

### P0

None. Build, lint, typecheck all green on both projects.

### P1

#### [P1] Turnstile dep without matching client widget — latent `/api/contact` regression the moment `TURNSTILE_SECRET_KEY` is set
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/package.json:13`, `/Users/mkhare/Development/sastaspace/projects/_template/web/package.json:13`; see also `/Users/mkhare/Development/sastaspace/projects/landing/web/src/app/api/contact/route.ts:57` and `/Users/mkhare/Development/sastaspace/projects/landing/web/src/components/contact-form.tsx:20`.
- **justification**: `@marsidev/react-turnstile` is declared but `grep -rn "Turnstile\|@marsidev"` finds no import in any src file. `ContactForm` reads `formData.get("cf-turnstile-response")` from a field that is never rendered, so the token is always empty. `route.ts:57` bails with 400 `Missing verification token` whenever `TURNSTILE_SECRET_KEY` is populated — meaning the moment the prod env gets the secret, every contact submission will 400. The server-side verify block itself is correct; the client widget is missing.
- **suggested fix**: choose one:
  - (a) render `<Turnstile siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!} />` inside `ContactForm` (the SDK injects `cf-turnstile-response` into the form), or
  - (b) drop `@marsidev/react-turnstile` from both manifests and delete the `turnstileToken` path from `route.ts` + `contact-form.tsx`.

#### [P1] Zero automated test coverage — `vitest` is the repo convention but not wired up anywhere
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/package.json`, `/Users/mkhare/Development/sastaspace/projects/_template/web/package.json`
- **justification**: `CLAUDE.md` §"Testing conventions" mandates vitest + colocated `*.test.ts`. Neither manifest declares `vitest`, `@vitest/coverage-v8`, a `test` script, nor any `*.test.*` files under `src/`. Critical paths with non-trivial logic and zero tests: `src/app/api/contact/route.ts` (honeypot short-circuit + Turnstile verify + Resend delivery), `src/lib/supabase/middleware.ts` (session refresh cookie propagation), `src/app/(admin)/admin/layout.tsx` (two-step `getSessionUser` → `isCurrentUserAdmin` gate), `src/components/projects/project-card.tsx` `deriveStatus()` (live/wip fallback), `src/components/ui/status-chip.tsx` (variant → label map).
- **suggested fix**: add to both `package.json`: `"scripts": { "test": "vitest run", "test:watch": "vitest" }` and `"devDependencies": { "vitest": "^2.1.0", "@vitest/coverage-v8": "^2.1.0" }`. First tests to land: `project-card.test.tsx` (deriveStatus table-driven), `route.test.ts` for `/api/contact` (honeypot / missing fields / missing token), `status-chip.test.tsx` (label + aria-label per variant).

#### [P1] ~~`lucide-react` pinned to `^1.8.0` — the wrong/stale package~~ *(withdrawn — see team-lead note at top of file)*
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/package.json:28`, `/Users/mkhare/Development/sastaspace/projects/_template/web/package.json:28`
- **justification**: ~~canonical `lucide-react` is currently at `^0.4xx`. `node_modules/lucide-react/package.json` reports `"version": "1.8.0"` — either a squatted/stale fork or a years-old cut. Build happens to pass because the icon set used (Check, ChevronDown, ChevronRight, Circle, X, Moon, Sun, LogOut, Shield, User, LayoutDashboard, Users, ArrowRight) all exist in the stale version, but the app is missing years of icons and security fixes.~~ **Verification (team-lead): the `lucide-react` package at `^1.8.0` IS the canonical one** — `lucide-icons/lucide` repo, maintainer `ericfennis`, latest version 1.9.0 published 2026-04-23. Pin is current; no action.
- **suggested fix**: no change.

#### [P1] Unused `motion@12.38.0` dep in both manifests
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/package.json:29`, `/Users/mkhare/Development/sastaspace/projects/_template/web/package.json:29`
- **justification**: `grep -rn '"motion"' src/` — no import. The only `motion` token found in `src/` is a Tailwind selector `data-[motion^=from-]` in `ui/navigation-menu.tsx`, which is a Radix data-attr, unrelated to the `motion` package. `npm ls motion` confirms it's a direct dep. Dead weight in CI install + dev images.
- **suggested fix**: `npm uninstall motion` in both projects.

#### [P1] `@tanstack/react-table` + `components/ui/data-table.tsx` shipped unused
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/src/components/ui/data-table.tsx`, `/Users/mkhare/Development/sastaspace/projects/_template/web/src/components/ui/data-table.tsx`, plus `@tanstack/react-table` in both `package.json:25`
- **justification**: `grep -rln "@tanstack/react-table\|DataTable" src/` returns only the component itself — no caller. `/admin/users/page.tsx` uses the low-level `Table` primitives directly. This is the source of the one remaining lint warning (`react-hooks/incompatible-library`) and ~30KB of shipping dead code.
- **suggested fix**: delete `src/components/ui/data-table.tsx` and remove `@tanstack/react-table` from both manifests. Re-scaffold via shadcn CLI the first time a project needs it.

#### [P1] Landing page opts into `force-dynamic` + `cache: "no-store"` — every hit is an uncached server render
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/src/app/page.tsx:5-11`
- **justification**: `export const dynamic = "force-dynamic"; export const revalidate = 0;` combined with `fetch(..., { cache: "no-store" })` burns a PostgREST roundtrip on every page view of the homepage. For a marketing site whose project list changes on weekly timescales this is Lighthouse-visible TTFB cost with no upside.
- **suggested fix**:
  ```ts
  export const revalidate = 300; // 5 min
  // drop: export const dynamic = "force-dynamic";
  // change fetch to: fetch(..., { next: { revalidate: 300 } })
  ```
  Use `revalidatePath("/")` for on-demand invalidation later.

#### [P1] `(auth)/layout.tsx` still ships pre-brand chrome + orphaned ThemeToggle
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/src/app/(auth)/layout.tsx:9-14`, `/Users/mkhare/Development/sastaspace/projects/_template/web/src/app/(auth)/layout.tsx`
- **justification**: design log 003 dropped `ThemeToggle` from primary nav "per plan §T4," but the `(auth)` layout still imports it and renders a generic `<span class="h-2 w-2 rounded-full bg-primary" />` dot + plain "SastaSpace" text rather than the `BrandMark` SVG used in `layout/topbar.tsx`. `/sign-in`, `/sign-up`, `/forgot-password` therefore ship with different top-chrome than `/` and `/contact`. Root cause is stale imports surviving the brand cut — engineering drift, not brand copy.
- **suggested fix**: rewrite `app/(auth)/layout.tsx` to reuse the brand `Topbar` (or a stripped variant showing BrandMark + wordmark only, no nav). Remove the `ThemeToggle` import. Same change in `_template`.

#### [P1] Global `font-feature-settings: "ss01", "cv11"` on body — undocumented Inter-specific feature leaking onto mono + Devanagari
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/src/app/globals.css:124`, `/Users/mkhare/Development/sastaspace/projects/_template/web/src/app/globals.css` (same line).
- **justification**: `cv11` on Inter enables the single-story "a" — a strong stylistic choice not called for in `brand/BRAND_GUIDE.md` §5. The body rule applies it to `JetBrains Mono` and `Noto Sans Devanagari` too, where it's either a no-op or unpredictable. Flagging because the brand guide specifies tracking only and shipping font-feature-settings you didn't consciously pick is technical debt.
- **suggested fix**: delete the line unless the single-story "a" is a deliberate brand choice — confirm with owner.

### P2

#### [P2] `AppShell.projectName` prop is dead on landing — kept "for API stability"
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/src/components/layout/app-shell.tsx:9`
- **justification**: the prop is documented as "Reserved for future per-project branding. Currently unused on sastaspace.com itself." Preserving unused props for hypothetical future consumers is the exact backwards-compat hack CLAUDE.md guidance rejects.
- **suggested fix**: drop the `projectName` prop from the landing `AppShell` signature. Template already has its own copy.

#### [P2] `data-table.tsx` pollutes every `eslint .` with the same warning in both projects
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/src/components/ui/data-table.tsx:42`, `/Users/mkhare/Development/sastaspace/projects/_template/web/src/components/ui/data-table.tsx:42`
- **justification**: warning resolved automatically once the P1 deletion lands; flagged P2 separately in case the deletion is deferred.
- **suggested fix**: falls out of the P1 deletion.

#### [P2] `postcss.config.mjs` anonymous-default-export warning — one-line fix
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/postcss.config.mjs:1`, `/Users/mkhare/Development/sastaspace/projects/_template/web/postcss.config.mjs:1`
- **justification**: lint warning `import/no-anonymous-default-export`. Purely cosmetic, but affects both projects.
- **suggested fix**:
  ```js
  const config = { plugins: { "@tailwindcss/postcss": {} } };
  export default config;
  ```

#### [P2] Landing `Footer` hardcodes `https://github.com/themohitkhare` and `https://linkedin.com/in/themohitkhare` inline
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/src/components/layout/footer.tsx:15,26`
- **justification**: duplicated in `_template/web/src/components/layout/brand-footer.tsx:37`. Two edit points if a handle changes. Small cost; flag for completeness.
- **suggested fix**: extract to `src/lib/links.ts` `SOCIAL_LINKS` const, or accept the duplication.

#### [P2] `/admin/page.tsx` calls `getSessionUser()` after the layout has already fetched the user
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/src/app/(admin)/admin/page.tsx:7`, template same.
- **justification**: `AdminLayout` already calls `getSessionUser()` and redirects if null. Child page calls it again just to read `user.email`. May be request-cached by `@supabase/ssr`; worth confirming.
- **suggested fix**: verify caching behavior; if duplicate network fetches occur, thread `user` through React context or move the email display into the layout.

#### [P2] `components/theme/theme-provider.tsx` is a pass-through wrapper that adds no value
- **file**: `/Users/mkhare/Development/sastaspace/projects/landing/web/src/components/theme/theme-provider.tsx`
- **justification**: re-exports `ThemeProvider` from `next-themes` verbatim, adding a client-boundary shim for no reason.
- **suggested fix**: delete; import `ThemeProvider` from `next-themes` directly in `app/layout.tsx`.

#### [P2] `_template` Topbar default `projectName="__NAME__"` relies on `scripts/new-project.sh` sed pass
- **file**: `/Users/mkhare/Development/sastaspace/projects/_template/web/src/components/layout/topbar.tsx:5`, `/Users/mkhare/Development/sastaspace/projects/_template/web/src/app/(admin)/admin/layout.tsx:14`
- **justification**: if a project is scaffolded via the manual fallback documented in `CLAUDE.md` and the sed pass is skipped, defaults degrade to the literal string `__NAME__`.
- **suggested fix**: leave as-is (template-only risk, documented) or default to a generic `"project"` string.

## Merge verdict

`develop` is **mergeable from an engineering-health standpoint** — build + typecheck + lint are all green on both projects and no P0s. However, the Turnstile contract is a latent regression (will 400 every contact submission once the secret is populated in prod) and should resolve before any launch announcement. The test-coverage gap and zombie deps (`motion`, `@tanstack/react-table`, ~~stale `lucide-react`~~) are pre-launch cleanup work. P2s are non-blocking.

Counts: P0 = 0, P1 = 8 *(7 after lucide-react withdrawal)*, P2 = 7.
