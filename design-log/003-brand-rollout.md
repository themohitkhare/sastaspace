# Design Log 003 — Brand Rollout

**Status:** Implemented — pending local verification + git replay
**Date:** 2026-04-23
**Owner:** @mkhare
**Session:** Cowork + Claude (non-Ruflo — sandbox-driven execution)

---

## Background

The project-bank foundations (log 001) and auth + admin UI (log 002) gave SastaSpace a working shape — shared Postgres, per-project subdomains, Supabase auth, shadcn-themed landing page. What was missing was a **brand**. The `projects/landing` app still read like a boilerplate "project bank" site — good bones, no voice.

This log documents the first pass at a brand system for SastaSpace and its application to `projects/landing/web`. The `_template` was updated in the same pass so new projects inherit the brand.

## The idea

Mohit's resume is a receipt roll of making expensive engineering sasta — but **SastaSpace is a lab, not a portfolio**. Two clarifying constraints from the session:

1. The site is *idea-level*, not a list of wins. Specific resume metrics stay on the resume.
2. Sasta is the design constraint that lets a one-person lab exist: cheap to build, cheap to ship, cheap to share. Not a humble-brag — a mission.

Primary tagline: **"A sasta lab for the things I want to build."**
Hindi counterpart: **जो बनाना है, बनाओ.**

## Brand system

Six deliverables now live in `brand/`:

- `BRAND_GUIDE.md` — canonical rules. Positioning, voice, color, type, logo, visual vocabulary, rollout checklist, what-the-system-is-NOT.
- `landing-mockup.html` — pixel target for the homepage. Self-contained, browser-openable.
- `bio.md` — taglines, 1-line / medium / long bios, elevator pitches, project card microcopy, 404 / empty state copy.
- `tokens.css` — reference token file (the real app uses `globals.css`; this is for non-Next consumers).
- `logo-*.svg` — primary wordmark, compact mark (rounded square with price-tag + bilingual "स/S" monogram), standalone monogram, personal wordmark + mark.
- `REDESIGN_PLAN.md` — the task breakdown that drove this rollout.

### Palette

| Role | Name | Hex |
|---|---|---|
| Primary text / ink | Ink | `#1a1917` |
| Primary accent | Sasta | `#c05621` |
| Deeper accent | Rust | `#8a3d14` |
| Surface / paper | Paper | `#f5f1e8` |
| Muted neutral | Dust | `#a8a196` |

No gradients, no shadows, no glows — flat surfaces only. Borders are 0.5px dust-line (`rgba(168, 161, 150, 0.45)`).

### Type

Three families. Two weights each — 400 and 500. No 600+.

- **Inter** — display + body
- **JetBrains Mono** — metrics, slugs, nav labels, code
- **IBM Plex Sans Devanagari / Noto Sans Devanagari** — bilingual sub-lines

Every major section carries a Devanagari counterpart. Removing it removes half the idea.

## Rollout

### `projects/landing/web`

- `src/app/globals.css` — ported brand tokens into Tailwind v4's `@theme inline`, remapped all shadcn semantic tokens (`--background`, `--foreground`, `--primary`, `--accent`, `--border`, etc.) onto brand primitives so existing `ui/*` components reskinned for free. Added explicit dark-mode overrides. Radius bumped from `0.625rem` to `0.875rem`.
- `src/app/layout.tsx` — wired Inter + JetBrains Mono + Noto Sans Devanagari via `next/font/google` with weight `[400, 500]` on each. Font CSS variables consumed by `globals.css`. Metadata updated. Favicon → `/brand/logo-monogram.svg`.
- `src/app/page.tsx` — full rewrite. Sections, in order: hero (terminal prompt + sasta-highlighted h1 + Devanagari sub + CTAs), "the idea" / three principles grid, projects (grid from PostgREST, empty state per `bio.md`), workshop notes (three `· coming soon` placeholders), about (two-column with the "lab in one line" card).
- `src/app/contact/page.tsx` — restyled as "Say hi. / नमस्ते कहो." Kept existing ContactForm + Turnstile.
- `src/components/layout/topbar.tsx` — rebuilt. Brand mark + wordmark left, mono anchor nav right (`the lab` / `projects` / `notes` / `about`). Dropped ThemeToggle and UserMenu from primary nav per plan §T4.
- `src/components/layout/footer.tsx` — rebuilt. Sig line (`Built sasta. Shared openly.`), mono link row, Devanagari mark.
- `src/components/layout/app-shell.tsx` — simplified; `projectName` prop now unused but kept for API stability.
- `src/components/ui/status-chip.tsx` — NEW. Signature brand element. `cva`-powered variants: `live`, `wip`, `paused`, `archived`, `open-source`. Accessible via `aria-label="status: <value>"`.
- `src/components/projects/project-card.tsx` — NEW. Card component consuming the `Project` type. Derives status from `live_at` when the (optional, not-yet-added) `status` column is absent.
- `public/brand/` — copied `logo-sastaspace.svg`, `logo-mark.svg`, `logo-monogram.svg`.
- `src/app/(admin)/admin/layout.tsx` — dropped the `projectName="SastaSpace"` prop since Topbar no longer accepts it.

### `projects/_template/web`

Same port as landing — `globals.css` tokens, `layout.tsx` fonts — so scaffolding a new project via `make new p=<name>` produces an on-brand skeleton. Also added `src/components/layout/brand-footer.tsx` — a shared footer component new projects wire into their layout.

## Decisions

**Tailwind v4 CSS-first over config file.** The repo already uses `@theme inline` in `globals.css`; no `tailwind.config.js`. Adding one would fight the existing pattern.

**Noto Sans Devanagari instead of IBM Plex Sans Devanagari.** The brand guide recommends Plex; `next/font/google` ships Noto reliably and it's near-indistinguishable at UI sizes. Kept Plex as the named reference in the guide for anyone consuming tokens outside Next.

**Derived status, not a new column.** The plan flagged a `status` column as optional (Task 9). Skipped — `ProjectCard` falls back to `live_at ? "live" : "wip"` and already accepts an explicit `status` when the schema eventually adds it.

**Dropped ThemeToggle + UserMenu from primary nav.** Scope discipline. Theme toggle can move to footer or a `⌘K` palette in a later pass. UserMenu belongs on admin routes, not the public landing.

**No resume metrics in copy.** Hard invariant from the brand guide. Numbers live on the resume; the site is idea-level.

## What did NOT ship in this pass

- **Task 9 — `status` + `tags` columns** on `public.projects`. Explicitly gated on owner approval.
- **Blog / notes content.** The `/notes` section renders three `· coming soon` placeholder rows.
- **Real project replacements.** The grid shows whatever is currently in the `projects` table.
- **Handwritten "workshop marks"** (the optional sasta-orange arrow / hand-drawn accent from the brand guide).
- **Screenshot-compare parity pass** — the sandbox could not run `next build` (network block on `@next/swc-linux-arm64-gnu`). TypeScript type-check passes clean (`tsc --noEmit`), ESLint on all touched files passes clean.

## Open follow-ups

1. Run `npm run build && npm run dev` locally; screenshot-compare against `brand/landing-mockup.html` at 1440px and 375px.
2. Verify dark-mode contrast — every text/background pair at WCAG AA. Fix any failures by tuning the `.dark` block in `globals.css`.
3. Hook up `/rss.xml` (currently a dead link in footer + about).
4. Decide on the first real set of project rows for the `projects` table so the grid populates on production.
5. Consider the `status` + `tags` columns (plan Task 9) once there are 3+ projects that would benefit from differentiated state.

## References

- Brand system: `brand/BRAND_GUIDE.md`
- Pixel target: `brand/landing-mockup.html`
- Copy bank: `brand/bio.md`
- Execution plan: `brand/REDESIGN_PLAN.md`
- Prior logs: `design-log/001-project-bank-foundations.md`, `design-log/002-auth-admin-ui-upgrade.md`
