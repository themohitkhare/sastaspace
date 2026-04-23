---
auditor: ux
branch: develop
date: 2026-04-23
commit: 422e2ca4b74d78c2bcb522e15c3da0000259d4ae
scope: projects/landing/web — voice, copy, a11y, WCAG 2.1 AA, keyboard/SR reachability
verdict: DO-NOT-MERGE
counts: P0=6, P1=6, P2=4
---

# UX audit — SastaSpace landing

Read-only audit. No source changes proposed as patches; suggested fixes are exact copy / attribute recommendations.

## Contrast table — every fg/bg pair the app actually uses

Computed via WCAG 2.1 relative-luminance formula against the hex values in `brand/tokens.css` and `projects/landing/web/src/app/globals.css`. Alpha blends (Tailwind `text-foreground/85` etc.) resolved against the underlying bg before ratio-ing.

Body threshold: 4.5:1. Large-text threshold (≥18pt regular / 14pt bold ≈ ≥24px / ≥18.66px @500): 3:1.

### Light mode (bg = paper `#f5f1e8`, card = paper-lifted `#fbf8f0`)

| fg | bg | ratio | body (4.5) | large (3.0) | notes |
|---|---|---|---|---|---|
| Ink `#1a1917` | Paper `#f5f1e8` | 15.59:1 | ✓ AAA | ✓ AAA | body, headings |
| Ink | Paper-lifted `#fbf8f0` | 16.55:1 | ✓ AAA | ✓ AAA | cards |
| Ink @ 90% | Paper | 11.88:1 | ✓ | ✓ | `text-foreground/90` |
| Ink @ 85% | Paper | 10.21:1 | ✓ | ✓ | `text-foreground/85` |
| Ink @ 80% | Paper | 8.61:1 | ✓ | ✓ | `text-foreground/80` |
| brand-muted `#6b6458` | Paper | 5.19:1 | ✓ AA | ✓ | `muted-foreground` light |
| brand-muted | Paper-lifted | 5.51:1 | ✓ AA | ✓ | card sub-text |
| **Sasta `#c05621`** | **Paper** | **4.05:1** | **✗ FAIL** | ✓ | **BRAND_GUIDE §4 claims 5.3:1 — the real ratio is 4.05:1** |
| Sasta | Paper-lifted | 4.31:1 | ✗ FAIL | ✓ | ProjectCard hostname |
| **Paper** | **Sasta** | **4.05:1** | **✗ FAIL** | ✓ | StatusChip `wip` text at 11px |
| Paper | Rust `#8a3d14` | 6.75:1 | ✓ | ✓ | button hover |
| Paper | Ink (primary btn bg) | 15.59:1 | ✓ AAA | ✓ | primary btn text |
| Ink (secondary btn) | `#efeade` | 14.64:1 | ✓ | ✓ | secondary surfaces |
| Dust `#a8a196` | Paper | 2.27:1 | ✗ | ✗ | metadata-only per §4 — app uses it for dividers and a single hero `·` separator, no body text |
| border dust@45% | Paper | ~1.46:1 | — | — | 0.5px decorative border |

### Dark mode (bg = ink `#1a1917`, card = `#252320`)

| fg | bg | ratio | body | large | notes |
|---|---|---|---|---|---|
| Paper | Ink | 15.59:1 | ✓ AAA | ✓ | body |
| Paper @ 85% | Ink | 11.51:1 | ✓ | ✓ | |
| Dust `#a8a196` | Ink | 6.86:1 | ✓ | ✓ | |
| `#a29d92` dark muted-fg | Ink | 6.50:1 | ✓ | ✓ | `--muted-foreground` dark |
| `#a29d92` | `#252320` | 5.80:1 | ✓ | ✓ | card sub-text |
| **Sasta** | **Ink** | **3.84:1** | **✗ FAIL** | ✓ | `--accent` body-size text in dark |
| **Sasta** | **`#252320`** | **3.43:1** | **✗ FAIL** | ✓ | ProjectCard hostname in dark |
| Paper | Sasta | 4.05:1 | ✗ FAIL | ✓ | StatusChip `wip` — same as light |
| Paper (live status bg) | Ink | 15.59:1 | ✓ | ✓ | StatusChip `live` in dark |
| `#8cc67a` (live dot) | Ink | 8.76:1 | — | — | decorative dot; non-text UI ≥3:1 ✓ |
| `#d97444` destructive bg / Ink text | — | 5.46:1 | ✓ | ✓ | |

Border dust contrast < 3:1 on both modes. Non-text-UI AA (WCAG 1.4.11) requires 3:1 only for "essential" components; these borders are decorative (text-vs-card-bg is 15:1+), so noted here but not raised as a separate finding.

## Files reviewed

- `src/app/layout.tsx`
- `src/app/page.tsx`
- `src/app/contact/page.tsx`
- `src/components/contact-form.tsx`
- `src/app/(auth)/layout.tsx`
- `src/app/(auth)/sign-in/page.tsx`
- `src/app/(auth)/sign-up/page.tsx`
- `src/app/(auth)/forgot-password/page.tsx`
- `src/components/auth/sign-in-form.tsx`
- `src/components/auth/sign-up-form.tsx`
- `src/components/auth/forgot-password-form.tsx`
- `src/components/auth/user-menu.tsx`
- `src/app/(admin)/admin/layout.tsx`
- `src/app/(admin)/admin/page.tsx`
- `src/app/(admin)/admin/users/page.tsx`
- `src/components/layout/topbar.tsx`
- `src/components/layout/footer.tsx`
- `src/components/layout/app-shell.tsx`
- `src/components/layout/sidebar.tsx`
- `src/components/projects/project-card.tsx`
- `src/components/ui/status-chip.tsx`
- `src/components/ui/button.tsx`
- `src/components/ui/input.tsx`
- `src/components/ui/label.tsx`
- `src/components/theme/theme-toggle.tsx`
- `src/app/globals.css`
- `src/app/api/contact/route.ts` (for user-visible error strings only)

## Deliberately skipped

- Brand palette/font-weight violations (e.g. `font-semibold` = 600 on auth-page h1s, violates §5's 400/500 cap) — owned by `brand-security`.
- TS strictness / builds / bundle weight / code architecture — owned by `engineering`.
- `udaan` project — out of scope per charter.
- `_template/web` — mirrors the landing slice; any fix here should be mirrored there but isn't separately enumerated.
- Cloudflare Turnstile iframe copy (third-party).

---

## Findings

### P0 — blocks merge

---

### [P0] No custom 404 page — Next default "Page not found." ships
- **file**: `projects/landing/web/src/app/` (missing `not-found.tsx`)
- **justification**: BRAND_GUIDE §8 voice table mandates `"यहाँ कुछ नहीं है. Nothing here. Try the homepage."` (also in `bio.md` §"404 / empty states"). With no `not-found.tsx` at any segment, Next 16 serves its built-in fallback "404 · This page could not be found." — the exact pre-brand copy the guide forbids.
- **suggested fix**: create `projects/landing/web/src/app/not-found.tsx`:
  ```tsx
  import Link from "next/link";
  import { AppShell } from "@/components/layout/app-shell";

  export default function NotFound() {
    return (
      <AppShell>
        <section className="mx-auto max-w-2xl px-6 pb-24 pt-20 sm:px-8">
          <div className="font-mono text-xs tracking-[0.08em] text-muted-foreground">
            404 · nothing here
          </div>
          <p lang="hi" className="mt-5 font-deva text-[32px] leading-[1.1] tracking-[-0.02em] sm:text-[42px]">
            यहाँ कुछ नहीं है.
          </p>
          <h1 className="mt-2 text-[32px] leading-[1.1] tracking-[-0.02em] sm:text-[42px]">
            Nothing here.
          </h1>
          <p className="mt-6 text-[17px] leading-relaxed text-foreground/85">
            Try the{" "}
            <Link href="/" className="text-[var(--brand-rust)] underline-offset-4 hover:underline">
              homepage
            </Link>.
          </p>
        </section>
      </AppShell>
    );
  }
  ```

---

### [P0] StatusChip `wip` variant fails WCAG AA body contrast (Paper on Sasta, 11px)
- **file**: `projects/landing/web/src/components/ui/status-chip.tsx:18`
- **justification**: `wip` styles are `bg-[var(--brand-sasta)] text-[var(--brand-paper)]` at `text-[11px]` (chipStyles line 11). Paper `#f5f1e8` on Sasta `#c05621` = **4.05:1** — below the 4.5 body threshold. BRAND_GUIDE §4: *"Paper on Sasta — 3.9:1 ✓ AA large only (use for buttons/badges, not body)"*; §10: *"sasta orange used for emphasis, not for body copy."* At 11px the chip is body-sized.
- **suggested fix**: outlined Rust-on-paper-lifted (Rust on paper-lifted = 7.44:1 ✓):
  ```ts
  wip: "bg-[var(--brand-paper-lifted)] text-[var(--brand-rust)] border border-[var(--brand-rust)] before:bg-[var(--brand-rust)]",
  ```

---

### [P0] BRAND_GUIDE §4 claims "Sasta on Paper — 5.3:1" but the real ratio is 4.05:1; ~8 body-sized sasta text usages fail AA
- **file**: doc error at `brand/BRAND_GUIDE.md:110` + concrete app usages:
  - `projects/landing/web/src/app/page.tsx:99` section label "the idea"
  - `projects/landing/web/src/app/page.tsx:120` per-principle label "01 / sasta" etc.
  - `projects/landing/web/src/app/page.tsx:144` "projects"
  - `projects/landing/web/src/app/page.tsx:190` "workshop notes"
  - `projects/landing/web/src/app/page.tsx:228` "about"
  - `projects/landing/web/src/app/page.tsx:257` 17px inline anchor "the notes"
  - `projects/landing/web/src/app/page.tsx:264` 17px inline anchor "RSS feed"
  - `projects/landing/web/src/app/contact/page.tsx:13` `~/mohit · contact` at 12px
  - `projects/landing/web/src/components/projects/project-card.tsx:33` hostname at 11px on paper-lifted = 4.31:1 (also fail)
- **justification**: WCAG 2.1 SC 1.4.3 requires 4.5:1 for normal text. Measured Sasta on Paper = 4.05:1; on Paper-lifted = 4.31:1. BRAND_GUIDE §4 claims 5.3:1 — doc error. §10 pledges *"all text hits WCAG AA"*; currently it does not.
- **suggested fix**: introduce a body-size variant in `globals.css`:
  ```css
  :root  { --brand-sasta-text: var(--brand-rust); }   /* Rust on Paper = 8.13:1 */
  .dark  { --brand-sasta-text: #e98654; }             /* on Ink = 6.03:1 (see next finding) */
  ```
  Swap every body-size `text-[var(--brand-sasta)]` → `text-[var(--brand-sasta-text)]` in:
  - `src/app/page.tsx:99,120,144,190,228,257,264`
  - `src/app/contact/page.tsx:13`
  - `src/components/projects/project-card.tsx:33`
  Keep raw `--brand-sasta` for (a) hero H1 `<span>sasta</span>` at 44–68px (large, 3:1 ✓), (b) topbar period (decorative), (c) button backgrounds. Also update `brand/BRAND_GUIDE.md:110` — replace the 5.3:1 line with `"Sasta on Paper — 4.05:1 ✓ AA large only; use Rust / --brand-sasta-text for body emphasis."`

---

### [P0] Dark-mode Sasta links fail AA against Ink and card-dark
- **file**: `projects/landing/web/src/app/globals.css:108` (`--accent: var(--brand-sasta)` in `.dark`) + all call sites listed above.
- **justification**: In `.dark`, Sasta on Ink = 3.84:1; Sasta on card `#252320` = 3.43:1. Same text runs that fail in light mode fail worse in dark.
- **suggested fix**: fold into the `--brand-sasta-text` remap above. Dark remap must go **brighter** — Rust on Ink = 2.12:1 (worse). `#e98654` on Ink = 6.03:1, on `#252320` = 5.29:1, both clear body AA.

---

### [P0] Auth pages ship pre-brand generic copy with zero Devanagari
- **files**:
  - `projects/landing/web/src/app/(auth)/sign-in/page.tsx:10-13` — `<h1>Welcome back</h1>` + `"Sign in to continue to SastaSpace."`
  - `projects/landing/web/src/app/(auth)/sign-up/page.tsx:9-11` — `<h1>Create your account</h1>` + `"Sign up to access SastaSpace."`
  - `projects/landing/web/src/app/(auth)/forgot-password/page.tsx:9-12` — `<h1>Forgot your password?</h1>` + `"Enter your email and we'll send you a reset link."`
- **justification**: BRAND_GUIDE §8 row lists *"Welcome to..."* as the avoid-column; §9: *"Not monolingual. Removing the Devanagari removes half the idea. Keep the bilingual motif even on English-only pages"*; §10 checklist: every page carries a Devanagari counterpart. None of the three auth pages do.
- **suggested fix**:
  - sign-in/page.tsx:8-14:
    ```tsx
    <div>
      <h1 className="text-[32px] font-medium leading-[1.1] tracking-[-0.02em]">Sign in.</h1>
      <p lang="hi" className="mt-1 font-deva text-base text-muted-foreground">वापसी पर स्वागत है.</p>
      <p className="mt-3 text-sm text-muted-foreground">Back into the lab.</p>
    </div>
    ```
  - sign-up/page.tsx:7-12:
    ```tsx
    <div>
      <h1 className="text-[32px] font-medium leading-[1.1] tracking-[-0.02em]">Make an account.</h1>
      <p lang="hi" className="mt-1 font-deva text-base text-muted-foreground">खाता बनाओ.</p>
      <p className="mt-3 text-sm text-muted-foreground">Needed for the admin-only corners of the lab.</p>
    </div>
    ```
  - forgot-password/page.tsx:7-13:
    ```tsx
    <div>
      <h1 className="text-[32px] font-medium leading-[1.1] tracking-[-0.02em]">Reset the password.</h1>
      <p lang="hi" className="mt-1 font-deva text-base text-muted-foreground">पासवर्ड भूल गए?</p>
      <p className="mt-3 text-sm text-muted-foreground">Drop the email, grab the link from your inbox.</p>
    </div>
    ```

---

### [P0] Admin pages ship pre-brand generic copy and generic empty-state
- **files**: `projects/landing/web/src/app/(admin)/admin/page.tsx:11-13`, `projects/landing/web/src/app/(admin)/admin/users/page.tsx:31-34,47-50`
- **justification**: `<h1>Admin</h1>` + `"Signed in as {email}"` and `<h1>Admins</h1>` + `"Emails in this list can access..."`. Empty-state is literal `"No admins found. Run migrations to seed."` — §8 row "No projects yet! → The workshop's quiet today. Come back soon." is the canonical shape; this row violates it. §9 invariant applies even on English-only admin pages; zero Devanagari present.
- **suggested fix**:
  - admin/page.tsx:11-13:
    ```tsx
    <h1 className="text-3xl font-medium tracking-tight">The back room.</h1>
    <p lang="hi" className="mt-1 font-deva text-base text-muted-foreground">पिछला कमरा.</p>
    <p className="mt-3 text-sm text-muted-foreground">Signed in as {user?.email}.</p>
    ```
  - admin/users/page.tsx:31-34:
    ```tsx
    <h1 className="text-2xl font-medium tracking-tight">Keyholders.</h1>
    <p lang="hi" className="mt-1 font-deva text-sm text-muted-foreground">चाबी वाले.</p>
    <p className="mt-2 text-sm text-muted-foreground">
      Anyone here can poke around <code>/admin</code>. Add or drop names from Studio.
    </p>
    ```
  - admin/users/page.tsx:47-50 empty-state:
    ```tsx
    <TableCell colSpan={3} className="h-20 text-center text-muted-foreground">
      No one&apos;s been let in yet. Seed via <code>make migrate</code>.
    </TableCell>
    ```

---

### P1 — before launch

---

### [P1] Contact form has no inline error linkage — server errors surface only via sonner toast
- **file**: `projects/landing/web/src/components/contact-form.tsx:37,41-72`
- **justification**: WCAG 2.1 SC 3.3.1 (Error Identification). Server returns `"Missing required fields"` / `"Missing verification token"` / `"Verification failed"` / `"Email delivery failed"` / `"Unexpected server error"` (`src/app/api/contact/route.ts:53,58,65,92,98`) — relayed only via `toast.error(body.error ?? "Failed to send message")`. No `aria-invalid` / `aria-describedby` on inputs; toast is ephemeral.
- **suggested fix**:
  ```tsx
  const [error, setError] = useState<string | null>(null);
  // on failure branch:
  setError(body.error ?? "Something broke. Try again, or email me.");
  // render above Button:
  {error && (
    <p id="form-error" role="alert" className="text-sm text-[var(--brand-rust)]">
      <span lang="hi">कुछ गड़बड़.</span> {error}
    </p>
  )}
  <Button type="submit" disabled={status === "submitting"} aria-describedby={error ? "form-error" : undefined}>
  ```

---

### [P1] Focus ring is 1px — fails WCAG 2.2 SC 2.4.11 thickness minimum
- **files**:
  - `projects/landing/web/src/components/ui/button.tsx:7` (`focus-visible:ring-1`)
  - `projects/landing/web/src/components/ui/input.tsx:10` (same)
  - `projects/landing/web/src/components/contact-form.tsx:58` (textarea, same)
- **justification**: WCAG 2.2 SC 2.4.11 (Focus Appearance, AA) requires focus indicator ≥2px thick with 3:1 contrast. Ring colour (Sasta on Paper) = 4.05:1 passes contrast but the thickness prong fails at 1px. Inconsistent with sibling components (`ui/tabs.tsx:31,46`, `ui/sheet.tsx:64`, `ui/dialog.tsx:43`, `ui/badge.tsx:6`) which already use `ring-2`.
- **suggested fix**: change `focus-visible:ring-1` → `focus-visible:ring-2` in all three files. Optional: add `focus-visible:ring-offset-2 focus-visible:ring-offset-background`.

---

### [P1] No `prefers-reduced-motion` CSS
- **file**: `projects/landing/web/src/app/globals.css` (end of file)
- **justification**: WCAG 2.1 SC 2.3.3 + charter explicitly flags it. ProjectCard uses `transition-all hover:-translate-y-[1px]` (`project-card.tsx:31`); Tailwind `transition-colors` on every hover Link. No `@media (prefers-reduced-motion: reduce)` block anywhere.
- **suggested fix**: append to `globals.css`:
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
  ```

---

### [P1] Devanagari snippets lack `lang="hi"`
- **files**: every `<p className="… font-deva …">` with Devanagari:
  - `src/app/page.tsx:47` `जो बनाना है, बनाओ.`
  - `src/app/page.tsx:106` `पोर्टफोलियो नहीं, एक प्रयोगशाला.`
  - `src/app/page.tsx:164` `आज कार्यशाला शांत है.`
  - `src/app/page.tsx:234` `नमस्ते, मैं मोहित हूँ.`
  - `src/app/contact/page.tsx:20` `नमस्ते कहो.`
  - `src/components/layout/footer.tsx:52` `जो बनाना है, बनाओ.`
- **justification**: `<html lang="en">` (`layout.tsx:41`). WCAG 2.1 SC 3.1.2 (Language of Parts, AA). Without `lang="hi"`, VoiceOver / NVDA read Devanagari character-by-character with an English voice. Brand §9 commitment to the bilingual motif extends to a11y.
- **suggested fix**: add `lang="hi"` to each `<p className="font-deva …">`. Example (`page.tsx:47`):
  ```tsx
  <p lang="hi" className="mt-4 font-deva text-base text-muted-foreground sm:text-lg">
    जो बनाना है, बनाओ.
    <span className="px-2 text-[var(--brand-dust)]">·</span>
    <span className="font-sans" lang="en">build what you want to build.</span>
  </p>
  ```

---

### [P1] AuthLayout home-link uses pre-brand capitalised wordmark + fake dot, no BrandMark
- **file**: `projects/landing/web/src/app/(auth)/layout.tsx:9-13`
- **justification**: BRAND_GUIDE §3.1: *"`sastaspace` set in Inter Medium, letterspacing -0.02em, all lowercase. The terminal period `.` is always in sasta orange."* AuthLayout ships `<span>SastaSpace</span>` (capitalised, no period) with a fake round `<span class="h-2 w-2 rounded-full bg-primary" />` dot. `components/layout/topbar.tsx:16-25` gets this right.
- **suggested fix**: lift `BrandMark` out of `topbar.tsx` (e.g. to `src/components/brand/brand-mark.tsx`) and replace `(auth)/layout.tsx:9-13` anchor body:
  ```tsx
  <Link href="/" className="flex items-center gap-3 text-foreground" aria-label="sastaspace home">
    <BrandMark />
    <span className="text-lg font-medium tracking-tight">
      sastaspace<span className="text-[var(--brand-sasta)]">.</span>
    </span>
  </Link>
  ```

---

### [P1] No skip-to-content link; `<main>` has no `id`
- **files**: `projects/landing/web/src/components/layout/app-shell.tsx:12-17`, `projects/landing/web/src/app/(admin)/admin/layout.tsx:13-26`
- **justification**: WCAG 2.1 SC 2.4.1 (Bypass Blocks, A). Sticky topbar + (admin) sidebar stack multiple link blocks before `<main>`. No skip link present.
- **suggested fix** — in AppShell before `<Topbar />`:
  ```tsx
  <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-[var(--brand-ink)] focus:px-3 focus:py-2 focus:text-[var(--brand-paper)]">
    Skip to content
  </a>
  ```
  Add `id="main"` to `<main className="flex-1">` in `app-shell.tsx:14` and to the content `<div className="flex-1 p-6">` in `(admin)/admin/layout.tsx:23`.

---

### [P1] Contact form success state leaves form live — no inline success panel
- **file**: `projects/landing/web/src/components/contact-form.tsx:31,68-70`
- **justification**: On `status === "success"`, only the button label flips to `"Sent"` and a toast fires; form inputs stay enabled and populated. `sign-up-form.tsx:35-44` and `forgot-password-form.tsx:32-40` correctly replace the form with a success panel; ContactForm breaks that established pattern.
- **suggested fix**:
  ```tsx
  if (status === "success") {
    return (
      <div role="status" className="rounded-[var(--radius-lg)] border border-border bg-card p-6">
        <p className="font-medium">Sent.</p>
        <p lang="hi" className="mt-1 font-deva text-sm text-muted-foreground">भेज दिया.</p>
        <p className="mt-3 text-sm text-muted-foreground">
          I read everything. Reply comes from my own email.
        </p>
      </div>
    );
  }
  ```

---

### P2 — nice-to-have

---

### [P2] ProjectCard link opens in new tab without accessible annotation
- **file**: `projects/landing/web/src/components/projects/project-card.tsx:27-32`
- **justification**: WCAG SC 2.4.4 (Link Purpose). `<a target="_blank" rel="noreferrer">` wraps the whole card with no accessible name describing destination or new-tab behaviour.
- **suggested fix**: add `aria-label={`${project.name} — ${hostname} (opens in new tab)`}` on the `<a>`.

---

### [P2] Hero uses `→` glyph on one CTA but not the other — inconsistent arrow motif
- **file**: `projects/landing/web/src/app/page.tsx:62`
- **justification**: BRAND_GUIDE §6.5: handwritten arrows are *"the optional sasta-orange arrow / hand-drawn accent … Use sparingly; one per page maximum."* Hero pairs `"see the lab →"` with `"about the idea"` (no arrow) — two conventions side-by-side. Not a WCAG issue.
- **suggested fix**: drop the `→` from the primary CTA, OR apply a decorative sasta-orange hand-drawn arrow as a `::after` element to match §6.5.

---

### [P2] `<html lang="en">` — consider `"en-IN"` for Hinglish audience
- **file**: `projects/landing/web/src/app/layout.tsx:41`
- **justification**: Not a WCAG fail. `en-IN` better matches a Bengaluru-based lab and nudges some TTS engines toward Indic-English voices and Hindi fallback when inline `lang="hi"` is added (P1 above).
- **suggested fix**: `<html lang="en-IN" ...>`.

---

### [P2] `StatusChip` aria-label is redundant to visible text
- **file**: `projects/landing/web/src/components/ui/status-chip.tsx:51`
- **justification**: Chip renders `{LABELS[value]}` as visible text and sets `aria-label="status: {value}"`. ARIA name overrides the accessible name, so SR users hear `"status: live"` instead of `"live"` — defensible (adds role prefix). Charter asked to verify; current wording is acceptable.
- **suggested fix**: leave as-is. Reconsider only if the chip is ever used standalone outside a project-card context.

---

## Appendix — invariants that passed

- Footer sig line exactly matches §8: `Built sasta. Shared openly. © Mohit Khare, {year}.` (`footer.tsx:8-11`) ✓
- Footer Devanagari `जो बनाना है, बनाओ.` present (`footer.tsx:52`) ✓ (missing `lang="hi"` — see P1).
- Projects-section empty state matches `bio.md` verbatim: `The workshop's quiet today. Come back soon.` (`page.tsx:161`) + Devanagari sibling `आज कार्यशाला शांत है.` (`page.tsx:164`) ✓
- Hero H1 matches §8 verbatim: `A sasta lab for the things I want to build.` ✓
- Hero sub-line matches §8 verbatim: `जो बनाना है, बनाओ.` ✓
- About paragraph (`page.tsx:239-251`) is a close stylistic match to `bio.md` Bio-long + "One-paragraph hero" — within §2 latitude.
- Topbar nav labels lowercase mono per §5 ✓
- BrandMark in topbar `aria-hidden="true"` + anchor `aria-label="sastaspace home"` (`topbar.tsx:19,58`) ✓
- `<nav aria-label="primary">` (`topbar.tsx:26`) ✓
- One `<h1>` per page on every audited route ✓
- Radix `<Label htmlFor=…>` linkage on all form inputs ✓
- UserMenu trigger `aria-label="Account menu"` (`user-menu.tsx:38`) ✓; sign-out is `<form method="post">` ✓
- ThemeToggle `aria-label="Toggle theme"` + `<span className="sr-only">Toggle theme</span>` ✓
- Honeypot `<input name="company" hidden tabIndex={-1} aria-hidden="true">` (`contact-form.tsx:61-67`) ✓
- Hero CTAs resolve to existing section ids ✓
- `<html suppressHydrationWarning>` present (`layout.tsx:42`) — required for next-themes
