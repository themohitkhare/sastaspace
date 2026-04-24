# Design Log 004 — Almirah: a personal ethnic-aware wardrobe at almirah.sastaspace.com

**Status:** Design — pending UI pass + implementation plan
**Date:** 2026-04-24
**Owner:** @mkhare
**Session:** Brainstorm via Claude (superpowers:brainstorming), multi-persona PM + designer + user team

---

## Background

Two reference apps inspired this: [Armadio / Digital Wardrobe](https://play.google.com/store/apps/details?id=com.amird.armadio) (AmirD — simple, solo) and [Acloset](https://play.google.com/store/apps/details?id=com.looko.acloset) (Korean, ~7M users, AI-driven). Both are built for western wardrobes — top + bottom + shoes, calendar-centric, optimised for daily outfit assembly.

The Indian wardrobe breaks that model. A saree is a compound unit (saree + blouse + petticoat + optional fall, often paired with a specific dupatta and jewellery set). Salwar-kameez-dupatta, lehenga-choli-dupatta, kurta-churidar, sherwani, dhoti all pair-logic their way through an occasion. Planning is occasion-first (Diwali, wedding sangeet, Karva Chauth, office-ethnic Friday) rather than calendar-first. Family sharing is routine, not an edge case. Repeat-anxiety ("who saw me in what at which wedding?") is real.

Almirah is a personal-scope tool — no marketplace, no public launch, no acquisition. Goal: ship a useful wardrobe for one household, iterate weekly, and let it compound.

## Problems we're solving

1. **"I can't see what I own."** Crowded almirah across multiple locations → forget what's in there → re-buy duplicates or leave things unworn.
2. **"I don't know what to wear."** Occasion-aware outfit suggestions — wedding, Diwali, office day, trip — pulled from *my actual catalogue*, not generic Pinterest.
3. **"I can't remember what I wore where."** Repeat-anxiety log; tags each outfit with the event it went to and who was there.

Secondary but explicit: **household sharing** (Nisha ↔ daughter, Rohan ↔ Meera), and **unisex** — kurta-sherwani-dhoti are first-class alongside saree-lehenga-kurti.

## Personas

| Persona | Profile | Primary pain |
|---|---|---|
| Priya (29, Bangalore, PM) | 80/20 western-office / weekend-ethnic; 3 weddings/year | "What did I wear to Ananya's sangeet?" |
| Arjun (32, Gurgaon, SWE) | Mostly western; 3 kurtas + 1 sherwani | "Don't wear the same shirt to two company events" |
| Nisha (58, Delhi, mother) | 40+ sarees, deep jewellery; lends to daughter | "Who has my red Kanjivaram?" |
| Rohan + Meera (34/32, Mumbai, couple) | Shared closet; coordinate for weddings | "What saree colour so we match at the reception?" |

## Scope — Approach 2, "Personal Almirah" (v1, ~2–3 weeks)

### In scope (v1)

- **Auth + household.** Supabase GoTrue (shared infra). One household = 1..N members. Member invite by link/code.
- **Photo ingest from what you already own.** Upload from phone camera roll, Google Drive folder, or drag-drop on desktop. Batch processing. No manual per-item capture required to get started.
- **AI outfit-level tagging.** For each uploaded photo we extract: style_family (western-casual / western-formal / ethnic-festive / ethnic-daily / sports / sleepwear), dominant colours, items visible (flat unisex taxonomy — kurta / sherwani / saree / blouse / dupatta / lehenga / kurti / shirt / blazer / jeans / trousers / dhoti / jewellery / shoes / juttis / bag), occasion hint, fabric hints where visible, and people count.
- **Catalogue browse.** Grid view of all household outfits with quick filters: person, style family, occasion, dominant colour, date range. Default sort: newest first.
- **Outfit detail.** Large photo, editable tag chips, wear log, worn-by attribution, privacy toggle, delete.
- **Search.** Free-text search that hits tags, colours, occasion hints, notes — plus semantic "outfits like this one" using pgvector embeddings.
- **Wear log.** Each outfit has 0..N wear events (auto-seeded from photo EXIF date, manually addable). Each event can carry event name, event type, attendees (free-text names), notes.
- **Occasion planner.** User enters: event name, date, type, formality, dress-code notes, attendees. App ranks candidate outfits from the household catalogue and Claude Opus 4.7 vision picks the top 3 with 1-line reasoning each. Flags repeat-risk: "you wore this to Karan's wedding; Meera will be at both."
- **Repeat-risk flagging.** When planning, surface any candidate outfit where a named attendee overlaps with a past wear event's attendees.
- **Unisex design.** No gender toggle in UI. Onboarding asks primary styling lean (western-heavy / ethnic-heavy / mixed) purely to tune default filter chips. Every feature works identically for male and female users.
- **PWA-installable.** This is a phone-first app; it must install to the home screen.

### Out of scope (deferred to v2+)

- **Item-level catalogue.** Segmentation + dedup + mix-match outfit builder. Pipeline will ingest outfit-level tags that *mention* items, but we will not try to deduplicate "is this the same red kurta as that one?" in v1.
- Cost-per-wear, price tracking, receipt import.
- Care reminders (silk dry-clean, zari storage).
- Jewellery sets as linked entities.
- Couple-coordinate mode (Rohan+Meera colour-match view).
- Marketplace / resell.
- Social feed / follow other users.
- Stylist chat / open-ended "what goes with this?" conversation.

## Core user flows

### 1. First-run onboarding
1. Land at `almirah.sastaspace.com` → sign in (email or Google via Supabase GoTrue).
2. Prompt: *Create a new household* or *Join via invite code*.
3. If create: name the household (default "Khare Almirah"), pick primary lean (ethnic-heavy / western-heavy / mixed).
4. Empty-state dashboard invites: "Add some photos to get started — upload from your phone, your camera roll, or a Google Drive folder."

### 2. Ingest
1. User triggers upload: drag-drop, mobile camera-roll picker, or Google Drive folder connector.
2. Photos upload to Supabase Storage; one row per photo inserted into `outfits` with status=`queued`.
3. Async worker picks up each photo:
   - EXIF parse (date, GPS if present).
   - Haiku 4.5 vision *filter pass*: is this an outfit photo (person visible, wearing something)? Else mark `filtered_out` + stop.
   - Opus 4.7 vision *tag pass*: returns the structured JSON described in scope.
   - Generate multi-modal embedding (store in `outfits.embedding` as pgvector).
   - Status → `ready`.
4. Dashboard streams progress: "47 of 120 processed — peek while we work."

### 3. Browse & search
- Grid defaults to newest first; sticky filter row: *person · style · occasion · colour · year*.
- Tap an outfit → detail view.
- Search box: free-text (weighted search over tags + notes) with a *"similar outfits"* affordance on any outfit that re-ranks the grid by embedding similarity.

### 4. Outfit detail
- Hero photo, swipe for other angles if multiple.
- Tag chips: style family, colours, items, occasion — editable in place.
- *Worn by:* defaults to uploader; change to any household member.
- *Privacy:* shared with household (default) or private to owner.
- *Wear log:* list of (date, event, attendees, notes). "Log a wear" button.
- *Delete / archive.*

### 5. Occasion planner
1. "Plan an event" button in the header.
2. Form: event name, date, type (wedding / office / casual / puja / festival / party / travel), formality (1–4), dress-code notes (free text), attendees (free text, comma-separated).
3. Server: filter catalogue by style family appropriate to type+formality; rank by embedding similarity to a generated "event-prompt" embedding; fetch last-wear metadata per candidate; pass top ~15 to Opus 4.7 vision.
4. Opus returns top 3 picks with one-line reasoning each. Any pick with attendee overlap against past wears is flagged: "⚠ Meera will be at this event and saw this outfit at Karan's reception."
5. User can accept a pick → outfit gets pre-created wear entry for the event date.

## Architecture

### Tech stack
- **Web:** Next.js 16 (App Router), TypeScript, Tailwind v4, shadcn/ui — per repo convention. PWA-installable (manifest + service worker).
- **API:** Next.js Route Handlers for synchronous calls. A lightweight Go API (`projects/almirah/api`) for heavier background work (ingest pipeline, embedding generation, occasion-ranking) — `chi` + `pgx`, per repo convention.
- **Database:** Shared Supabase Postgres (schema `project_almirah`). pgvector for embeddings. RLS policies enforce household boundaries.
- **Auth:** Shared Supabase GoTrue at `auth.sastaspace.com`. `@supabase/ssr` in Next.
- **Storage:** Supabase Storage bucket `almirah-photos` (household-scoped paths, RLS-mirrored).
- **AI:** Anthropic SDK. Claude Haiku 4.5 for cheap filter passes, Claude Opus 4.7 for tag extraction + occasion planning. Embedding via a multimodal embedding model (Voyage multimodal or equivalent — decide at implementation time, abstract behind an interface).
- **Deploy:** MicroK8s on 192.168.0.37. Per-project manifest at `projects/almirah/k8s.yaml`. Cloudflare tunnel + DNS + ingress per existing recipe.

### Service boundaries
```
Browser
  ├── Next.js web (UI + auth-gated route handlers for CRUD)
  │    └── Supabase Postgres (RLS)
  │    └── Supabase Storage
  └── Go ingest-api (triggered by web, reads a work queue in Postgres)
       ├── Anthropic Claude (Haiku filter, Opus tag)
       ├── Embedding provider
       └── Supabase Storage (read photos, write thumbnails)
```

Occasion-planner ranking lives in the Go service too; the web hands it an event spec, gets back ranked candidates, then the web makes the final Opus call itself so the JSON is streamed to the user.

### Data model (core tables, `project_almirah` schema)

- `households (id, name, primary_lean, created_at)`
- `household_members (household_id, user_id, display_name, role, joined_at)`
- `outfits (id, household_id, uploaded_by, worn_by_user_id, photo_path, thumb_path, taken_at, geo jsonb, style_family, occasion_hint, colours text[], items_visible text[], ai_tags jsonb, embedding vector(N), is_private, status, created_at)` — `N` pinned to the chosen embedding model (see open questions)
- `outfit_wears (id, outfit_id, worn_at, event_name, event_type, attendees text[], notes)`
- `events (id, household_id, name, starts_at, type, formality, attendees text[], notes)`
- `planner_runs (id, household_id, event_id, candidate_outfit_ids uuid[], picks jsonb, created_at)`

RLS: every table scoped by membership in `household_members`. `outfits.is_private` narrows to `uploaded_by` when true.

### AI cost envelope
- Filter pass (Haiku 4.5, one image): pennies per 100 photos.
- Tag pass (Opus 4.7, one image): order of cents per photo at typical sizes — the dominant cost line.
- Embedding: well under a cent per photo.
- Occasion planner (one Opus call with ~15 thumbnails): low tens of cents per plan.
- A 500-photo seed run sits in the low tens of dollars. Acceptable for a personal tool. Haiku stays the default gate — Opus only runs when Haiku says "yes, outfit." Confirm exact numbers against current Anthropic pricing at implementation time.

### Shared infra opt-in
Almirah opts into **Postgres + GoTrue + Storage** (all three). It does not need PostgREST (web talks to Postgres directly via Go / Next route handlers). Admin surface isn't needed — Studio on `studio.sastaspace.com` covers any ops.

## Screens to design (hand-off to Claude Design)

Target aesthetic: brand `BRAND_GUIDE.md` — paper background `#f5f1e8`, orange `#e85d2f` used sparingly (primary CTA + selected-state only), no gradients/shadows/glows, 400/500 font weights only, `Noto Sans Devanagari` as per the template. Mobile-first, dense outfit grid, generous whitespace on detail screens.

1. **Sign-in.** Email + Google OAuth. Minimal, brand-consistent.
2. **Household create/join.** Two-option screen → either a name field + lean chooser, or a 6-char invite code.
3. **Empty dashboard.** Hero illustration + "Add photos" CTA. Three input paths: camera roll picker (mobile), file drag-drop (desktop), Google Drive folder.
4. **Upload progress.** Stream of thumbnails with per-item status chips (*queued · filtering · tagging · done · skipped*).
5. **Browse grid.** Sticky filter row across the top; 3-up grid on mobile, 5-up on desktop. Each card = outfit thumb + 1-2 key tag chips.
6. **Outfit detail.** Photo first, metadata below. Wear-log feed at the bottom. Edit-in-place tag chips.
7. **Search.** Single input; results re-lay into the browse grid with a "similar to X" pill when a semantic search is active.
8. **Occasion planner — form.** Event metadata form; attendee chips; submit.
9. **Occasion planner — result.** 3 stacked outfit cards with reasoning under each; repeat-risk warning inline; accept/reject.
10. **Household settings.** Members list + invite link + lean setting.
11. **Profile preferences.** Primary lean, display name in household.

## Verification / success signals

- *Week 1 after seeding:* the owner opens it at least 3 times without prompting.
- *Before the next wedding / Diwali / office-ethnic day:* the owner uses occasion planner and actually wears one of the picks.
- *Qualitative:* the owner sends the invite link to at least one family member unprompted.

## Open questions (for implementation plan to resolve)

1. **Embedding provider choice.** Voyage multimodal vs. image-to-text → text-embedding? Defer to plan, abstract behind interface.
2. **Google Drive connector scope.** Full Drive OAuth + folder picker, or start with "share folder → public URL" and revisit?
3. **Face-detection policy.** Auto-attendee inference from face detection would help repeat-risk, but it's a privacy cliff. v1 ships with manual attendee entry only; face-embedding is out of scope unless explicitly re-scoped.
4. **Private vs shared default.** Currently default-shared with per-outfit private toggle. Worth prototyping the reverse (default-private, opt-in share per outfit) with a small user first.
5. **Thumbnail generation.** In Go worker with `vips`/`imaging` at upload time, or lazy via Next Image? Probably at upload time to keep Storage egress predictable.
6. **Multi-photo outfits.** Many events have multiple angles of the same outfit. v1 treats one photo = one outfit entry; a future *merge* action links duplicates. Don't solve upfront.

## Next steps

1. Hand this doc to Claude frontend-design for screen-by-screen mockups against the brand guide — 11 screens listed above. Expected output: a self-contained HTML mockup per screen (like `brand/landing-mockup.html`) plus a shared tokens pass.
2. Review mockups → iterate if needed.
3. Invoke `superpowers:writing-plans` to produce a task-by-task implementation plan against this design + the approved mockups.
4. Scaffold via `make new p=almirah`, then execute the plan.

## References
- Brand guide: `brand/BRAND_GUIDE.md`
- Foundation log: `design-log/001-project-bank-foundations.md`
- Auth log: `design-log/002-auth-admin-ui-upgrade.md`
- Brand rollout: `design-log/003-brand-rollout.md`
- Reference apps: Armadio / Digital Wardrobe, Acloset, Indyx, Whering
