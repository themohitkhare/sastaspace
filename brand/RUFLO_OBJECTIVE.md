# Objective — execute the SastaSpace brand redesign

You are the strategic queen of a hierarchical hive-mind swarm. Your job is to execute a pre-written redesign plan, not to re-plan it. The plan is the contract. Read it first, route work to specialists, verify, and ship.

## Inputs — read before routing any work

1. `brand/REDESIGN_PLAN.md` — authoritative task list. 10 numbered tasks, explicit file paths, acceptance criteria, gotchas. This is your spec. Do not deviate from it.
2. `brand/BRAND_GUIDE.md` — positioning, color, type, voice, visual vocabulary, don'ts. Workers must respect these rules.
3. `brand/landing-mockup.html` — pixel target. Open it mentally and match it.
4. `brand/bio.md` — ready-to-paste copy (hero, about, project cards, 404s, footer). Do not paraphrase; the voice is calibrated.
5. `brand/tokens.css`, `brand/logo-*.svg` — design tokens and logo assets.
6. `CLAUDE.md` (repo root) — stack, conventions, repo layout. Next.js 16 + Tailwind v4 + shadcn/ui + Supabase. `proxy.ts` not `middleware.ts`.

## Deliverable

A pull request on branch `brand-redesign` against `main` that makes `projects/landing/web` render the brand system — matching `brand/landing-mockup.html` in layout and voice — and backports the same tokens/fonts into `projects/_template/web` so future projects inherit the brand.

## Execution contract

- **Order is fixed.** Tasks 1 → 7 first. Pause. Then 8 → 10. Task 9 (schema migration) is optional; only execute it if the owner explicitly approves.
- **Commit per task.** Message format: `brand: task <n> — <short description>`. Do not squash until PR review.
- **Branch:** `brand-redesign`. Create it from `main` at head.
- **No scope creep.** If a worker wants to add a page, library, or visual element not in the plan, the queen must escalate — do not approve silently.
- **Respect the brand rules as invariants.** These are must-nots, enforced at code review:
  - No gradients, drop shadows, glows, or neon effects.
  - No ALL CAPS or Title Case in UI. Sentence case everywhere.
  - Two font weights only: 400 regular, 500 medium.
  - No specific resume metrics in copy. Idea-level only.
  - Paper (`#f5f1e8`) is the page background, not white.
  - Sasta orange (`#c05621`) accents only — never body text.
  - Devanagari sub-lines required on every major section.
- **Stack constraints:** Tailwind v4 is CSS-first (no `tailwind.config.js`, use `@theme inline` in `globals.css`). Do not install new font packages — use `next/font/google`. Do not swap shadcn for a different UI library.

## Routing — suggested specialist assignments

- `architect` — pre-flight read of REDESIGN_PLAN.md + repo; confirms no missed dependency; produces a one-page execution map; then steps back.
- `css-tokens-specialist` — Task 1 (port tokens into `globals.css`), Task 2 (font wiring), Task 3 (static assets in `public/brand/`).
- `next-specialist` + `frontend-coder` (pair) — Task 4 (AppShell rebuild), Task 5 (landing page sections), Task 7 (contact page restyle).
- `frontend-coder` — Task 6 (StatusChip component with cva variants + aria-label).
- `css-tokens-specialist` again — Task 8 (backport tokens + fonts + `<BrandFooter />` into `_template`).
- `tester` — runs acceptance criteria from REDESIGN_PLAN.md §4 after Tasks 1–7 and again after 8/10. Reports pass/fail per criterion.
- `code-reviewer` — enforces brand invariants before every commit. Blocks commits that violate them.
- `tech-writer` — Task 10 (`design-log/003-brand-rollout.md`).

## Checkpoints — the queen must pause here

1. **After the architect's pre-flight.** Report: "Plan reviewed. Execution map: [bulleted list of which worker takes which task]. Confirmed no missed dependency. Proceeding to Task 1." Do not proceed if the architect flags a blocker.
2. **After Task 7, before Task 8.** Report what's shipped, run the Task 7 acceptance criteria, attach a screenshot comparison of the dev server vs. `landing-mockup.html` at 1440px and 375px. Wait for owner approval before continuing.
3. **Before opening the PR.** Post the full PR description (summary + test plan) to the channel, including the acceptance-criteria checklist with pass marks. Wait for owner approval to push.

## Acceptance criteria — copied verbatim from REDESIGN_PLAN.md §4

- `cd projects/landing/web && npm run build` passes with zero errors.
- `npx eslint .` passes with zero errors.
- `npm run dev` renders a page that matches `brand/landing-mockup.html` layout. Screenshot-compare at 1440px and 375px.
- Dark mode toggled: every text/background pair stays readable. No invisible text.
- All sections present in order: hero, lab, projects, notes, about, footer.
- Projects grid fetches from PostgREST and renders a card per row. Empty state uses `bio.md`'s exact copy.
- StatusChip renders all five variants (`live`, `wip`, `paused`, `archived`, `open source`) without visual bugs.
- Brand guide invariants respected across all files.
- `projects/_template/web` builds and inherits the same tokens + fonts.
- `design-log/003-brand-rollout.md` exists.

## Escalate to owner — do not silently decide

- Tailwind v4 token remap breaks a shadcn primitive that can't be fixed at the token layer.
- A Hindi string needs to change.
- The mockup deviates from what the PostgREST data can render (e.g., schema can't cleanly express a status).
- Dark-mode contrast fails WCAG AA on any text pair.
- An external dependency needs to be added.
- Test or build infrastructure needs to change.

## Out of scope — do not attempt

- Backend or auth changes.
- New routes beyond the mockup (no `/now`, `/uses`, `/blog`, etc.).
- Actual blog posts. The `/notes` list stays as "coming soon" placeholders.
- Real project replacements — ship with whatever is in the `projects` table.
- Logo redesigns. The SVGs in `brand/` are final.
- Color palette changes. The answer is no.

## Finish line

- Branch `brand-redesign` pushed.
- PR opened against `main` with a description that follows the repo's conventions (`gh pr create` with Summary + Test plan sections).
- Acceptance checklist in the PR body, all checked.
- CI (self-hosted runner at 192.168.0.37) passes the build step.
- Hive queen posts a final report: "Done. PR #<n>. Tests <status>. Owner review requested."

Ship sasta. Ship shared. Ship small.
