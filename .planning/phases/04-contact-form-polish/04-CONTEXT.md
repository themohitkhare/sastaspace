# Phase 4: Contact Form + Polish - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a contact form to the result page so visitors can express hiring interest, wire it to Resend for email delivery, protect it from spam with Cloudflare Turnstile (invisible) + honeypot, and do a mobile polish pass across all three pages (landing, progress, result).

</domain>

<decisions>
## Implementation Decisions

### Contact form placement
- **D-01:** Form lives in `result-view.tsx` below the existing content, separated by a `<hr>` divider and ~48px of vertical spacing
- **D-02:** Headline: "Like what you see? Let's build the real thing." (CONTACT-01 locked) — rendered as `h2`, same size hierarchy as the page's existing text
- **D-03:** Form width: `max-w-xl`, centered, consistent with `url-input-form.tsx` — fits within the existing `max-w-3xl` column
- **D-04:** Fields: Name (`type="text"`), Email (`type="email"`), Message (`<textarea>` with `rows={4}`). All use existing shadcn `Input` and `Label` components. Message uses a plain `textarea` styled to match.
- **D-05:** Submit button: full-width, same style as the landing page's "Redesign My Site" button (`bg-primary`)

### Success state
- **D-06:** On successful submit, swap the form out for a thank-you message using `AnimatePresence` — form fades out, message fades in (consistent with `app-flow.tsx` pattern)
- **D-07:** Thank-you copy: "Thanks, I'll be in touch." — single line, centered, muted subtext: "I typically reply within 24 hours."
- **D-08:** No toast, no banner, no redirect — inline swap only (CONTACT-05)

### Spam protection
- **D-09:** Cloudflare Turnstile in **invisible mode** — no visible widget on the form, runs silently in the background, only challenges suspicious visitors. Token attached to form submission payload.
- **D-10:** Honeypot: a hidden `<input name="website" tabIndex={-1} autoComplete="off" />` — if non-empty, reject server-side without calling Resend
- **D-11:** Turnstile widget rendered via `@marsidev/react-turnstile` package (lightweight, no iframe flash)

### API endpoint
- **D-12:** Next.js Route Handler at `web/src/app/api/contact/route.ts` (`POST`) — keeps frontend self-contained, no FastAPI changes needed
- **D-13:** Server-side flow: verify honeypot empty → verify Turnstile token with Cloudflare API → send email via Resend SDK → return `{ ok: true }`
- **D-14:** Rate limit: none in Phase 4 — Turnstile + honeypot is sufficient for now. FastAPI already has rate limiting for the redesign endpoint.

### Email content
- **D-15:** HTML email sent to owner via Resend. Subject: `New inquiry from {name} — SastaSpace`
- **D-16:** Email body includes: name, email (as `reply-to` so owner can hit reply directly), message, and the subdomain they were viewing (e.g. "Was viewing: acme-corp → acme.corp")
- **D-17:** `from` address: `noreply@sastaspace.com` (or whatever domain is configured in Resend). Owner's email in `to` field comes from env var `OWNER_EMAIL`.

### Environment variables (new)
- **D-18:** Add to `web/.env.local` (and `.env.example`):
  - `RESEND_API_KEY=re_...`
  - `OWNER_EMAIL=owner@example.com`
  - `NEXT_PUBLIC_TURNSTILE_SITE_KEY=...`
  - `TURNSTILE_SECRET_KEY=...`

### Mobile polish scope
- **D-19:** Fix scope: targeted mobile QA pass — not a visual redesign. Check all three pages at 375px:
  - Landing: URL input + button layout (already responsive per Phase 3, verify in browser)
  - Progress: step indicators at narrow width
  - Result: iframe aspect ratio, contact form fields stack correctly
- **D-20:** Fix any `overflow-x` issues (common with full-width elements on narrow viewports)
- **D-21:** No new animations, typography changes, or color changes — polish means "nothing looks broken or cramped"

### Claude's Discretion
- Exact Tailwind spacing values between form sections
- Error message copy for individual fields (name required, invalid email, message too short)
- Textarea resize behavior (`resize-none`)
- Loading state on submit button ("Sending..." with spinner using existing `motion` package)

</decisions>

<specifics>
## Specific Ideas

- The form should feel like a natural extension of the result page — not a jarring marketing section. Subdued, confident.
- Invisible Turnstile means zero friction for real users — they never see a "click the checkbox" step.
- Reply-to set to submitter's email is critical UX for the owner — they can just hit reply in Gmail.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing result page
- `web/src/components/result/result-view.tsx` — Where the form attaches; current layout, motion patterns, className conventions

### Existing form patterns
- `web/src/components/landing/url-input-form.tsx` — Established form state pattern (useState, handleSubmit, error display)
- `web/src/components/ui/input.tsx` — Reuse for Name and Email fields
- `web/src/components/ui/label.tsx` — Reuse for field labels
- `web/src/components/ui/button.tsx` — Reuse for submit button

### Animation patterns
- `web/src/components/app-flow.tsx` — AnimatePresence mode="wait" pattern for view swapping (use same approach for form → success state swap)

### Requirements
- `.planning/REQUIREMENTS.md` §CONTACT-01 through CONTACT-06 — all locked requirements for this phase

### State (decisions log)
- `.planning/STATE.md` — Project decisions and current position

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Input`, `Label`, `Button` from `web/src/components/ui/` — use directly, no new shadcn installs needed for form fields
- `AnimatePresence` + `motion.div` from `motion/react` — already in package.json, use for form/success swap
- `ResultView` component — form is added inline at the bottom of the existing JSX, before the closing `</motion.div>`

### Established Patterns
- Form state: `useState` for each field + `useState<"idle" | "submitting" | "success" | "error">` for submit state (mirrors `use-redesign.ts` pattern)
- Error display: `<p className="text-sm text-destructive mt-2">` (same as `url-input-form.tsx`)
- Max-width container: `max-w-3xl` at page level, `max-w-xl` for form — already used in existing components

### Integration Points
- `result-view.tsx` receives `subdomain` prop — pass it through to the contact form / API call so the email includes which redesign was viewed
- New API route at `web/src/app/api/contact/route.ts` — no changes to FastAPI needed
- New env vars needed in `web/.env.local` (see D-18)

</code_context>

<deferred>
## Deferred Ideas

- Rate limiting on the contact endpoint — sufficient protection from Turnstile + honeypot for v1
- Email confirmation to the submitter — owner's workflow doesn't need it yet
- Storing submissions in a database — email-to-inbox is sufficient for lead-gen volume
- OG tags / social preview images (DIFF-02) — v2 backlog

</deferred>

---

*Phase: 04-contact-form-polish*
*Context gathered: 2026-03-21 — all decisions made by Claude (user delegated)*
