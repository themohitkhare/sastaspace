# SastaSpace redesign — agent handoff plan

**Goal:** Apply the SastaSpace brand system to the `projects/landing` Next.js app so `sastaspace.com` ships as a lab — not a generic "project bank" shell. The mockup has already been designed in `brand/landing-mockup.html`; this plan turns that mockup into the real Next app.

**Owner:** Next agent picking this up. You will have no prior chat history — everything you need is in `brand/` and in the paths below. Read the **Reference** section first.

---

## 0. Reference — read these before you write code

1. `brand/BRAND_GUIDE.md` — canonical brand rules. Positioning, voice, color, type, logo, visual vocabulary, don'ts.
2. `brand/landing-mockup.html` — **the pixel target**. Open it in a browser. Your job is to make the live Next app render this, minus the inline styles (move them to Tailwind tokens) and plus the real project data.
3. `brand/bio.md` — all the ready-to-paste copy (hero, about, project cards, 404, footer).
4. `brand/tokens.css` — reference colors and fonts, but do NOT import this file directly. The landing app uses Tailwind v4 CSS-first theming; you'll port tokens into `globals.css` instead (see Task 1).
5. `brand/logo-*.svg` — logo assets. Copy into `projects/landing/web/public/brand/`.
6. `CLAUDE.md` (repo root) — architectural context. Don't break conventions described there.

Key brand rules that will bite you if you miss them:
- Sentence case everywhere. No ALL CAPS, no Title Case in UI.
- Two font weights only: 400 regular, 500 medium. Never 600 or 700.
- No gradients, no drop shadows, no glows. Flat surfaces only.
- Paper (`#f5f1e8`) is the page background, not white.
- Sasta orange (`#c05621`) is for accents — links, the brand dot, status chips, eyebrows. Never body text.
- The bilingual motif is required. Every major section gets a Devanagari sub-line.
- **No specific resume metrics anywhere.** The brand is idea-level; metrics stay on the resume.

---

## 1. Current state — what's already in the repo

Path: `projects/landing/web/` (Next.js 16 + React 19 + Tailwind v4 + shadcn/ui)

- `src/app/layout.tsx` — root layout. Already wires Inter via `next/font/google` and a shadcn `ThemeProvider` (dark/light toggle via `next-themes`).
- `src/app/page.tsx` — current landing page. Generic "Project Bank" badge, "Small projects, built and shipped." hero, shadcn `Card`/`Badge`/`Button` components. Fetches live projects from PostgREST at `${POSTGREST_URL}/projects?live_at=not.is.null`.
- `src/app/globals.css` — Tailwind v4 `@theme inline` block with OKLCH tokens (`--background`, `--foreground`, `--primary`, etc.) for both light and dark mode. Radius token `--radius: 0.625rem`.
- `src/components/layout/app-shell.tsx` — the nav/shell wrapper. Takes `projectName` prop.
- `src/components/ui/*` — shadcn primitives (button, card, badge, etc.). Don't rip these out; restyle via tokens.
- `src/app/contact/page.tsx` — existing contact page with form + Turnstile. Keep behavior, restyle surface.

Data model (from PostgREST call in `page.tsx`):
```ts
type Project = {
  id: number;
  slug: string;         // subdomain, e.g. "notes"
  name: string;         // "Notes"
  url: string;          // "https://notes.sastaspace.com"
  description: string;
  live_at: string | null;
};
```

Target URL: `https://sastaspace.com` (already routed by the Cloudflare tunnel in `infra/k8s`).

---

## 2. Target state — what "done" looks like

The live site should match `brand/landing-mockup.html` in layout and feel, with these differences from the mockup:

1. Projects grid is populated from the real PostgREST query (keep the existing fetch logic).
2. Dark mode works and maps brand colors sensibly (paper → ink-deep; ink → paper).
3. Dev-server build passes, lint passes, types pass.
4. New projects scaffolded via `make new p=<name>` inherit the brand because `_template` gets the same tokens/fonts and a `<BrandFooter />` (see Task 8).

**Non-goals for this pass** — explicitly out of scope so you don't scope-creep:
- No backend changes. Use the existing `projects` table and PostgREST query.
- No auth changes. The landing page is anonymous; don't touch Supabase integration.
- No writing blog posts. `/notes` is a placeholder list only.
- No handwritten illustration asset. The "workshop marks" visual in the brand guide is a future enhancement.
- No new projects. Placeholder cards are the mockup's job; the real site shows whatever's in the DB.

---

## 3. Task breakdown — do these in order

### Task 1 — Port brand tokens into `globals.css` (Tailwind v4 style)

**Files:** `projects/landing/web/src/app/globals.css`

Replace the existing OKLCH palette with the SastaSpace brand tokens in the same `@theme inline` pattern, plus explicit dark-mode overrides. Add the `--brand-*` primitives *and* remap the shadcn semantic tokens (`--background`, `--foreground`, `--primary`, `--accent`, `--border`, `--muted-foreground`, etc.) so existing shadcn components pick up the brand automatically.

Light mode mapping:
- `--background` → `#f5f1e8` (paper)
- `--foreground` → `#1a1917` (ink)
- `--card` → `#fbf8f0` (paper slightly lifted)
- `--muted-foreground` → `#6b6458`
- `--border` → `rgba(168, 161, 150, 0.45)` (dust-line)
- `--primary` → ink / `--primary-foreground` → paper
- `--accent` → sasta `#c05621` / `--accent-foreground` → paper
- `--destructive` → `#8a3d14` (rust)
- `--radius` → `0.875rem` (14px — matches the mockup's card radius)

Dark mode (`.dark` block): flip — ink becomes background, paper becomes foreground, sasta stays sasta (already readable on both).

Keep the `@theme inline` block shape so Tailwind v4 continues to generate utilities.

### Task 2 — Wire fonts in `layout.tsx`

**Files:** `projects/landing/web/src/app/layout.tsx`

Import three fonts from `next/font/google`:
- `Inter` (already there) → `--font-sans`, weights `[400, 500]`
- `JetBrains_Mono` → `--font-mono`, weights `[400, 500]`
- `Noto_Sans_Devanagari` → `--font-deva`, weights `[400, 500]` (substitute for IBM Plex Sans Devanagari since `next/font` ships Noto reliably and they're near-indistinguishable at UI sizes)

Apply all three variables on the `<html>` element. Add matching CSS variables in `globals.css`:
```css
--font-sans: var(--font-inter), ui-sans-serif, system-ui, sans-serif;
--font-mono: var(--font-jetbrains-mono), ui-monospace, SFMono-Regular, Menlo, monospace;
--font-deva: var(--font-noto-deva), var(--font-inter), sans-serif;
```

Update `<Metadata>`:
- `title: "sastaspace — a sasta lab for the things I want to build"`
- `description: "A lab on the open internet. Small projects, built cheap, shared openly."`

### Task 3 — Copy brand assets into `public/`

**Files:** new folder `projects/landing/web/public/brand/`

Copy from `brand/`:
- `logo-sastaspace.svg`
- `logo-mark.svg`
- `logo-monogram.svg`

Then in `public/` also add `favicon.svg` — a copy of `logo-monogram.svg` sized 32×32 (or use `logo-mark.svg`). Reference it in `layout.tsx` metadata via the `icons` field.

### Task 4 — Rebuild `AppShell` nav to match the mockup

**Files:** `projects/landing/web/src/components/layout/app-shell.tsx` (and any subfiles)

The mockup nav: inline brand mark + "sastaspace." wordmark on the left, `[the lab, projects, notes, about]` links on the right in JetBrains Mono at 13px. Remove the dark/light toggle from the primary nav (push it into the footer or keep it keyboard-only via `⌘K` later — out of scope now). Keep the shell responsive: links collapse into a mobile menu below 820px.

Nav links for now:
- `the lab` → `#lab`
- `projects` → `#projects`
- `notes` → `#notes`
- `about` → `#about`

All are in-page anchors; no separate routes yet except `/contact` which stays reachable from the footer.

### Task 5 — Rewrite `page.tsx` to match the mockup sections

**Files:** `projects/landing/web/src/app/page.tsx`

Sections, in order, as in the mockup:

1. **Hero** — terminal prompt (`~/mohit · sastaspace.com`), h1 with inline sasta-colored "sasta", Devanagari sub, lede paragraph, two CTAs (`see the lab →` scrolls to `#projects`; `about the idea` scrolls to `#about`).
2. **The idea** (`id="lab"`) — eyebrow "the idea", h2 "Not a portfolio. A lab.", Devanagari sub, lede, three principle cards in a grid.
3. **Projects** (`id="projects"`) — header "What's on the bench." with a count line. Below it, the grid of project cards fetched from PostgREST. Empty state: use `bio.md`'s copy — `The workshop's quiet today. Come back soon.`
4. **Notes** (`id="notes"`) — eyebrow "workshop notes", h2, lede, a list of three placeholder entries with date `· coming soon` (literal text — no fake dates). Once there's a real blog, swap this for a `fetch()` against a `notes` table.
5. **About** (`id="about"`) — two-column about block, with the "the lab, in one line" stat card on the right.
6. **Footer** — sig line (`Built sasta. Shared openly. © Mohit Khare, 2026.`), links, Hindi mark.

Pull exact copy from `brand/bio.md`. Do not paraphrase — the voice is calibrated.

Project card (`src/components/projects/project-card.tsx` — new file):
```tsx
// props: project: Project + a status chip value
<a href={project.url} className="group card ...">
  <div className="slug">{project.slug}.sastaspace.com</div>
  <h3>{project.name}</h3>
  <p>{project.description}</p>
  <div className="card-meta">
    <StatusChip value={project.live_at ? "live" : "wip"} />
    <div className="tags">{/* optional — skip if no tech tags in schema */}</div>
  </div>
</a>
```

The existing schema doesn't have a status or tech-tags column. Choice: derive `status` as `live_at ? "live" : "wip"` for now. Schema extension is Task 9 (optional).

### Task 6 — Build the `StatusChip` component

**Files:** new `projects/landing/web/src/components/ui/status-chip.tsx`

Accepts `value: "live" | "wip" | "paused" | "archived" | "open source"` and renders the pill per the mockup (see `.chip` styles in `brand/landing-mockup.html`). Implement with Tailwind + `cva` so future variants are easy. Keep it flat — no shadows.

Accessibility: chip must have `aria-label` like "status: live" since the color indicator is decorative.

### Task 7 — Contact page restyle

**Files:** `projects/landing/web/src/app/contact/page.tsx`

Keep the form logic and Turnstile integration. Restyle the surface to match the brand — paper background, ink text, sasta-colored submit button with hover to rust. Form inputs: flat, 1px dust border, no shadows, 10px radius. Title: "Say hi." Sub (Devanagari): "नमस्ते कहो."

### Task 8 — Bring `_template` up to brand

**Files:** `projects/_template/web/src/app/globals.css`, `.../layout.tsx`, and a new shared `<BrandFooter />` component

New projects scaffolded via `make new p=<name>` currently inherit the generic shadcn theme. Port the same token changes from Task 1 and the font wiring from Task 2 into `_template` so every future project starts on-brand. Also add a small `<BrandFooter />` component (exported from `_template`) that renders the standard sig + link back to `sastaspace.com`. Document the backport in `design-log/003-brand-rollout.md` (see Task 10).

### Task 9 — (Optional, recommended) Extend the `projects` schema

**Files:** `db/migrations/<next-number>_projects_brand_fields.sql`

Add nullable columns so status chips and tech tags can be per-project instead of derived:
```sql
alter table public.projects
  add column status text check (status in ('live','wip','paused','archived','open_source')),
  add column tags text[] default '{}';
```

Update the PostgREST fetch and `ProjectCard` to use these when present. Keep the fallback logic (`live_at ? "live" : "wip"`) so existing rows don't break.

If time is tight, skip this task — derived status works fine.

### Task 10 — Design log entry

**Files:** new `design-log/003-brand-rollout.md`

Short entry (≤1 page) documenting what was done, why, and any decisions you made mid-task (esp. around tokens, fonts, schema). The repo convention in `CLAUDE.md` is design-log-first for significant changes; this lands post-hoc but is still required. Link to `brand/BRAND_GUIDE.md` and `brand/landing-mockup.html` as the inputs.

---

## 4. Acceptance criteria

Before marking this done, verify:

- [ ] `cd projects/landing/web && npm run build` passes with zero errors.
- [ ] `npx eslint .` passes with zero errors.
- [ ] `npm run dev` renders a page that matches `brand/landing-mockup.html` layout (screenshot-compare at 1440px and 375px).
- [ ] Toggle dark mode: every text/background pair stays readable. No invisible text.
- [ ] All sections from the mockup are present in order: hero, lab, projects, notes, about, footer.
- [ ] Projects grid fetches from PostgREST and renders a card per row; empty state uses the exact copy from `bio.md`.
- [ ] StatusChip renders all five variants without visual bugs.
- [ ] Brand guide rules respected: no gradients, no Title Case, no bold weights above 500, no specific metrics anywhere in the copy.
- [ ] `_template` builds and inherits the same tokens and fonts.
- [ ] `design-log/003-brand-rollout.md` exists.

Quick manual smoke test:
```bash
cd projects/landing/web
npm run dev
# open http://localhost:3000
# eyeball against brand/landing-mockup.html side by side
npm run build && npm run lint
```

---

## 5. Gotchas

- **Next 16 uses `proxy.ts`, not `middleware.ts`.** The landing app already has this at `src/proxy.ts`. Don't rename or try to reinstate `middleware.ts`.
- **Tailwind v4 is CSS-first.** Tokens live in `globals.css` inside `@theme inline`, not in `tailwind.config.js` (there is no config file). Add new utilities via `@theme inline` entries.
- **shadcn components read from semantic tokens.** If you remap `--background`/`--foreground`/`--primary`/`--accent` correctly in Task 1, most existing components (Button, Card, Badge) will re-skin themselves for free. Don't edit the shadcn primitives directly — fix the tokens.
- **Do NOT install new font packages.** `next/font/google` ships Inter, JetBrains Mono, and Noto Sans Devanagari. No extra deps needed.
- **Hindi text:** copy from `bio.md` character-for-character. Don't retype — IME autocorrect eats matras.
- **Links from emails or docs** are out of scope; this is a static marketing surface with one internal form. No external link-fetching required.
- **Don't commit secrets.** Keep `POSTGREST_URL` and any Supabase keys in `.env` (convention in `CLAUDE.md`); only `.env.example` goes in git.
- **Deployment:** CI on push to `main` handles build + k8s apply (self-hosted runner on 192.168.0.37). You don't need to SSH anywhere. Just merge.

---

## 6. Suggested order of operations for the next agent

1. Read `BRAND_GUIDE.md` and open `landing-mockup.html` in a browser. Spend 5 minutes absorbing.
2. Skim `projects/landing/web/src/` — especially `app/page.tsx`, `app/globals.css`, `app/layout.tsx`, `components/layout/app-shell.tsx`.
3. Port tokens (Task 1) + fonts (Task 2) + assets (Task 3). Boot dev server; the existing page should already start feeling different.
4. Rebuild the nav (Task 4) and the landing page (Task 5) section by section. Commit per section.
5. Add `StatusChip` (Task 6).
6. Restyle contact (Task 7).
7. Backport to `_template` (Task 8).
8. Schema extension (Task 9 — optional).
9. Design log (Task 10). Ship.

Estimate: a focused afternoon for Tasks 1–7, another hour for 8 + 10, skip 9 unless you feel like it.

---

## 7. When to stop and ask

Ping the owner in the following cases — don't guess:

- You want to deviate from the mockup for a reason that isn't purely technical.
- You want to add a new page/route (e.g. `/now`, `/uses`) beyond the mockup.
- You find yourself wanting to install a UI library (framer-motion beyond what's already there, headlessui, etc.).
- The Hindi copy needs to change. It's been picked deliberately; escalate any edit.
- You want to change the color palette. Answer is almost always no.

Everything else — ship it.
