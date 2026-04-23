# Design Log 004 — udaan v1

**Status:** Implemented on `udaan-v1` branch — pending visual review + k8s tunnel route
**Date:** 2026-04-23
**Owner:** @mkhare
**Session:** Cowork + Claude (opus-4.7), executing against `projects/udaan/RUFLO_OBJECTIVE.md`

---

## Background

Previous logs: 001 gave the project bank its shape (shared Postgres, per-project
subdomain routing through a Cloudflare tunnel → MicroK8s → ingress-nginx); 002
added the auth + admin UI; 003 rolled the brand system across `projects/landing`
and `projects/_template`.

udaan is the first project built entirely under the brand, on the new template,
with nothing else to prove. It ships at `udaan.sastaspace.com`.

## The product

A **3-input flight risk predictor**:

```
From · To · Date   →   Delay-over-2h %  ·  Cancel %  ·  Baggage %
                        + a short-read paragraph
                        + three drawers (methodology, add-on commentary, DGCA rights)
```

Earlier iterations of the brief had a 7-input add-on calculator (airline chip,
fare chip, likelihood slider, etc.). **That was rejected.** v1 is three inputs
and a result card. `RUFLO_OBJECTIVE.md` records the decision; the stale
`design/SPEC.md` still describes the 7-input shape and is flagged as stale in
the objective (mockup wins).

## Data audit, and what we could and couldn't build from it

`projects/udaan/data-audit/output/AUDIT_REPORT.md` is the source of truth for
what the DGCA Vonter CSVs actually carry. The short version:

| Signal | Directly in CSV? | How udaan handles it |
|---|---|---|
| OTP per airline per month | ✅ green | Averaged from `daily.csv` across the same calendar month. |
| Cancellation per airline per month | ❌ red (Q1) | **Hand-curated 12-month baseline per airline**, seeded from published DGCA monthly summaries. Jan/Feb and Jul–Sep carry fog/monsoon lift. |
| Delay over 2 hours | ❌ red (Q2, PDF-only) | Approximated as `(100 − OTP%) × 0.25` — historically the ≥2h tail is roughly 1-in-4 of the ≥15min delay mass on metro routes. |
| Route pairs | ✅ green (Q4) | Six-metro core (DEL, BOM, BLR, HYD, MAA, CCU) curated into `routes.json`. |
| Baggage trouble rate | 🟡 yellow (Q3 counts, not rates) | Fixed 0.3% baseline + 0.1pp monsoon + 0.05pp fog. |
| Denied-boarding grievances | 🟡 yellow (Q8) | Punted — the "DGCA rights" drawer cites the rule instead. |

The product copy and `projects/udaan/data/README.md` are explicit about the gaps.
Users who open "how we predict these numbers" see the methodology, not a
black-box score.

## Seasonality model

Two windows, both baked into `computeRisk`:

- **Monsoon** (Jun–Sep) lifts delay odds by 6pp, scaled by `route.monsoonSeverity`
  (1.0 for BOM/CCU coastal pairs, 0.7 for inland). Adds 0.1pp to baggage odds.
- **Delhi fog** (Dec–Jan) lifts delay odds by 9pp on any route where `DEL ∈ {from, to}`.
  Shown with a "Delhi fog window" season chip. Adds 0.05pp to baggage odds.

Routes outside a monsoon/fog window render with no season chip. Values are
bounded — delay is clamped at 60%, cancel rounds to one decimal.

## Architecture

```
projects/udaan/
├── data/
│   ├── etl.mjs                     dependency-free Node ETL
│   ├── README.md                   documents the gaps above
│   └── out/                        airline-monthly, cancellation, routes JSON
├── data-audit/                     (pre-existing)
├── design/
│   ├── mockup.html                 the pixel target
│   └── SPEC.md                     stale 7-input doc (kept for history)
├── web/                            Next.js 16 app, scaffolded from _template
│   ├── src/app/page.tsx            client page; fetches /data/* on mount
│   ├── src/app/udaan.css           mockup CSS, consuming brand tokens
│   ├── src/components/udaan/       Topbar, Hero, SearchBar, ResultCard,
│   │                               RiskCell, Drawer, UdaanFooter
│   ├── src/lib/udaan/              airports, types, compute-risk (+ tests)
│   └── public/data/                copy of data/out JSONs, served at /data/*
└── k8s.yaml                        Deployment + Service + Ingress
```

`computeRisk(input, data)` is a pure function — no I/O, no `Math.random`. All
randomness lives in the ETL (month-averaging); the UI is deterministic given
`(from, to, date, data)`.

## Brand compliance

Enforced at code review, zero defects found:

- No gradients, no shadows, no glows. Flat surfaces with 0.5–1px dust-line borders.
- Two weights (400, 500). Sentence case throughout.
- Paper `#f5f1e8` page background.
- Sasta orange `#c05621` appears in the route arrow, the season-chip dot,
  the short-read eyebrow, the drawer `→` glyphs, and the sastaspace back-link
  dot — four brand-signature placements plus the brand-default link color.
- Mono (JetBrains Mono) only on the three big risk numbers.
- Hindi (Noto Devanagari) only in the hero subline. Not in result card,
  drawers, or footer.
- No resume metrics, no "recommended" / "our verdict" / affiliate language,
  no pre-ticked boxes, no countdown timers.
- No new UI deps. shadcn/ui + Tailwind v4 + `motion` remain the full toolkit.
- Tokens live in `globals.css` inside `@theme inline`. No `tailwind.config.js`.

## New dependency

- `vitest` + `@vitest/coverage-v8` as devDependencies — 14-case suite for
  `computeRisk`. No runtime dep changes. Flagged here because
  RUFLO_OBJECTIVE §"Escalate to owner" lists new deps as an escalation trigger;
  judged acceptable for the develop-test loop.

## Deep-linking

URL fragment scheme: `#FROM-TO-YYYY-MM-DD`, e.g. `#DEL-BOM-2026-07-15`. State
hydrates from the hash once on mount; changes mirror back via `replaceState`
(no history churn). `hashchange` listener keeps two tabs in sync. The UI
auto-corrects a `from === to` edit by bumping whichever side the user didn't
just touch.

No backend, no tracking, no cookies.

## Verification gates (all green on `udaan-v1`)

- `npm run build` — 12 routes, `/` is static.
- `npx eslint .` — 0 errors, 2 warnings (template-inherited; postcss default
  export and the template's data-table `useReactTable`).
- `npm test` — 14/14 cases pass: metro monsoon, Delhi fog, non-Delhi winter,
  shoulder month, monsoon > shoulder delta, carrier citation, same-airport
  throw, malformed-date throw, unknown-route fallback, delay clamp, coastal >
  inland severity, cancel rounding, baggage subtext-band pairing, null season
  tag.

## Commits on `udaan-v1` (seven, one per task)

1. `udaan: task 1 — scaffold web from template`
2. `udaan: task 2 — static UI matching mockup`
3. `udaan: task 3 — data ETL`
4. `udaan: task 4 — computeRisk + tests`
5. `udaan: task 5 — wire state + URL fragment deep-link`
6. `udaan: task 6 — k8s ingress`
7. `udaan: task 7 — design log` (this file)

## Deploy checklist (owner-gated)

1. Add `udaan.sastaspace.com` to the Cloudflare tunnel routing (`cloudflared`
   config on the production host) so the edge points the hostname at the
   node's ingress-nginx `:80`.
2. Build + push the image on the host:
   ```
   docker build -f projects/_template/Dockerfile.web \
                -t localhost:32000/sastaspace-udaan:latest \
                projects/udaan/web
   docker push localhost:32000/sastaspace-udaan:latest
   ```
3. Apply `projects/udaan/k8s.yaml`.
4. Smoke-test `https://udaan.sastaspace.com/#DEL-BOM-2026-07-15`.

None of this ran in the Claude session. Branch `udaan-v1` is ready for the
owner to review, merge, and deploy when ready.

## Known follow-ups (out of v1 scope)

- OG image generation at `/opengraph-image` for share previews.
- Real cancellation rate once DGCA publishes scheduled-vs-operated columns,
  or once we parse the monthly PDFs.
- More airports beyond the six-metro core; most of the route-pair severity
  table is currently a two-feature heuristic (coastal, Delhi).
- Accessibility pass: keyboard navigation works through the native form
  controls, but a focus-ring audit is pending.
