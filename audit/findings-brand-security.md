# Audit — brand-security

- **Auditor:** `brand-security`
- **Branch:** `develop`
- **Date:** 2026-04-23
- **Commit SHA:** `422e2ca4b74d78c2bcb522e15c3da0000259d4ae`

## Files reviewed

Brand (all .tsx / .css under `projects/{landing,_template}/web/src/`):
- `projects/landing/web/src/app/globals.css`
- `projects/landing/web/src/app/layout.tsx`
- `projects/landing/web/src/app/page.tsx`
- `projects/landing/web/src/app/contact/page.tsx`
- `projects/landing/web/src/app/(auth)/layout.tsx`
- `projects/landing/web/src/app/(auth)/sign-in/page.tsx`
- `projects/landing/web/src/app/(auth)/sign-up/page.tsx`
- `projects/landing/web/src/app/(auth)/forgot-password/page.tsx`
- `projects/landing/web/src/app/(admin)/admin/layout.tsx`
- `projects/landing/web/src/app/(admin)/admin/page.tsx`
- `projects/landing/web/src/app/(admin)/admin/users/page.tsx`
- `projects/landing/web/src/components/layout/{topbar,footer,app-shell,sidebar}.tsx`
- `projects/landing/web/src/components/projects/project-card.tsx`
- `projects/landing/web/src/components/ui/{status-chip,button,card,badge,dialog,dropdown-menu,input,sheet,sonner}.tsx`
- `projects/landing/web/src/components/auth/{sign-in-form,sign-up-form,forgot-password-form,user-menu}.tsx`
- `projects/landing/web/src/components/contact-form.tsx`
- `projects/landing/web/src/components/theme/theme-toggle.tsx`
- equivalent files in `projects/_template/web/src/`

Security:
- `projects/landing/web/src/proxy.ts`
- `projects/landing/web/src/lib/supabase/{middleware,auth-helpers,client,server,cookies}.ts`
- `projects/landing/web/src/app/api/contact/route.ts`
- `projects/landing/web/src/app/auth/{callback,sign-out}/route.ts`
- `projects/landing/web/package.json`
- `infra/k8s/secrets.yaml.template`, `.gitignore`
- recent git log (last 3 months) for secret-shaped blobs
- `db/migrations/0004_admins_and_helpers.sql`, `0005_fix_anon_grants_and_is_admin.sql`

## Files deliberately skipped

- `.env.example` — read access denied by the harness sandbox. `.gitignore` excludes `.env*` except `.env.example`, so it IS in-repo; flagging for manual eyeball.
- `infra/k8s/secrets.yaml` — confirmed in `.gitignore:10` and NOT tracked (`git ls-files` returns only `secrets.yaml.template`).
- Go API, `db/` SQL except admin-gate migrations, `scripts/`, `.github/workflows/` — engineering scope.
- Public-asset SVGs under `public/brand/` — pure vector markup.
- a11y / copy — `ux` scope; only flagged where it crosses §5 sentence-case or §9 invariants.

---

## P0 — blocks merge

### [P0] Admin & auth pages ship `font-semibold` (weight 600) headings — brand §5 invariant violation
- **file**: `projects/landing/web/src/app/(admin)/admin/page.tsx:11`
- **justification**: §5 "Weights used: 400 (regular), 500 (medium). Nothing heavier." `font-semibold` maps to `font-weight: 600` and is a higher-specificity utility that overrides the `@layer base { h1 { font-weight: 500 } }` rule in `globals.css`. Every admin + auth page renders a 600-weight H1 in production.
- **suggested fix**: Replace `font-semibold` with `font-medium` on the H1s at `admin/page.tsx:11`, `admin/users/page.tsx:31`, `(auth)/sign-in/page.tsx:10`, `(auth)/sign-up/page.tsx:9`, `(auth)/forgot-password/page.tsx:9`. Same sweep in `_template`.

### [P0] `_template` landing + contact + auth-layout ship `font-semibold` — new projects inherit off-brand type
- **file**: `projects/_template/web/src/app/page.tsx:16`
- **justification**: Same §5 invariant. `_template` is what `make new p=<name>` copies, so every future project starts with a 600-weight hero headline.
- **suggested fix**: `text-4xl font-semibold tracking-tight sm:text-5xl` → `text-4xl font-medium tracking-tight sm:text-5xl` at `_template/app/page.tsx:16`, `_template/app/contact/page.tsx:12`, `_template/app/(auth)/layout.tsx:9`, and `landing/app/(auth)/layout.tsx:9`.

### [P0] Default `Button` variants apply `shadow`/`shadow-sm` — brand §4 invariant violation on every CTA
- **file**: `projects/landing/web/src/components/ui/button.tsx:11`
- **justification**: §4 "Gradients, shadows, glows. None. Ever. Flat surfaces only." and §7 "Borders over shadows." Line 11 default ships `shadow`; lines 13, 15, 17 (destructive / outline / secondary) ship `shadow-sm`. Every Button (contact submit, all auth forms, user-menu, admin nav) paints a drop shadow.
- **suggested fix**: Strip `shadow` / `shadow-sm` from `button.tsx:11,13,15,17`. Mirror in `_template/web/src/components/ui/button.tsx`.

### [P0] `Input` and contact-form `textarea` apply `shadow-sm` — brand §4 invariant violation
- **file**: `projects/landing/web/src/components/ui/input.tsx:10`
- **justification**: Same §4 invariant. `Input` is across auth + contact; `textarea` duplicates the class list.
- **suggested fix**: Remove `shadow-sm` from `input.tsx:10` and `contact-form.tsx:58`. Mirror in `_template`.

### [P0] `Dialog` / `Sheet` / `DropdownMenu` / `Sonner` pop-overs apply `shadow-lg`/`shadow-md` — brand §4 violation
- **file**: `projects/landing/web/src/components/ui/dialog.tsx:37`
- **justification**: Same §4/§7. `shadow-lg` at `dialog.tsx:37`, `sheet.tsx:30`, `dropdown-menu.tsx:43` and `:60` (shadow-md), `sonner.tsx:16`. User-menu dropdown on admin + every contact-form toast ships this today.
- **suggested fix**: Delete the shadow tokens; rely on the `border border-border` each surface already carries. Mirror in `_template`.

### [P0] `Topbar` uses `backdrop-blur-md` — brand §4 invariant violation (blur effect)
- **file**: `projects/landing/web/src/components/layout/topbar.tsx:14`
- **justification**: §4 and charter call `backdrop-blur` zero-tolerance. §9 contrasts lab vs Linear/Vercel-clone aesthetic. Visible on every page.
- **suggested fix**: Drop `backdrop-blur-md` and `bg-background/85` → `bg-background` at `topbar.tsx:14`. Same at `_template/web/src/components/layout/topbar.tsx:7`.

### [P0] `Badge` / `CardTitle` / `DialogTitle` / `SheetTitle` / `DropdownMenuLabel` hardcode `font-semibold`
- **file**: `projects/landing/web/src/components/ui/badge.tsx:6`
- **justification**: §5. `Badge` base CVA line 6 sets `font-semibold`; `card.tsx:29`, `dialog.tsx:71`, `sheet.tsx:95`, `dropdown-menu.tsx:140` do the same. `Card` is used on `admin/page.tsx`; `UserMenu` uses `DropdownMenuLabel`. All render at 600.
- **suggested fix**: Replace `font-semibold` with `font-medium` in `badge.tsx:6`, `card.tsx:29`, `dialog.tsx:71`, `sheet.tsx:95`, `dropdown-menu.tsx:140`. Mirror in `_template`.

### [P0] Contact form never renders a Turnstile widget — submit can never carry a real token
- **file**: `projects/landing/web/src/components/contact-form.tsx:42`
- **justification**: Form posts `turnstileToken: String(formData.get("cf-turnstile-response") || "")` (line 20), but JSX contains only name / email / message / honeypot — no `<Turnstile />` widget, no hidden input. `package.json:14` pulls `@marsidev/react-turnstile` but it is never imported. When `TURNSTILE_SECRET_KEY` is set (`infra/k8s/secrets.yaml.template:87`), `route.ts:57-58` returns `"Missing verification token"` for every real submission — form is bricked. When secret is unset, `route.ts:17-18` silently skips verification — open to unlimited automated abuse; honeypot alone is trivially bypassable. Same gap at `_template/…contact-form.tsx:42`.
- **suggested fix**: Import `Turnstile` from `@marsidev/react-turnstile` and render `<Turnstile siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!} />` inside the `<form>`. Fail the handler closed (HTTP 503) if `TURNSTILE_SECRET_KEY` is unset in production, instead of skipping verification.

### [P0] Contact → Resend email built by HTML string interpolation of user input — XSS in the admin inbox
- **file**: `projects/landing/web/src/app/api/contact/route.ts:79`
- **justification**: `html: \`<p><strong>Name:</strong> ${body.name}</p><p><strong>Email:</strong> ${body.email}</p><p>${body.message}</p>\`` embeds un-escaped visitor input. Any submitter can inject `<script>` / `<img onerror>` / `<a href=javascript:…>` into the owner's inbox; rendering varies by mail client. Same code path at `_template/…/route.ts:79`.
- **suggested fix**: Escape before embedding. Inline helper: `const esc = (s:string) => s.replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]!));` — then `${esc(body.name)}` etc. Also include `text:` in the Resend payload.

---

## P1 — before launch

### [P1] `Sidebar` admin-heading uses `uppercase tracking-wider` — brand §5 "sentence case only"
- **file**: `projects/landing/web/src/components/layout/sidebar.tsx:30`
- **justification**: §5 sentence-case-only; §6 uppercase only for mono stat labels and status chips. Sidebar `title` renders uppercase sans-serif; admin passes `title="Admin"` → renders "ADMIN". Same line in `_template`.
- **suggested fix**: Drop `uppercase tracking-wider`. If visual separation is wanted, use the mono face (`font-mono text-[11px] tracking-[0.06em]`).

### [P1] Auth layout wordmark uses a pill-dot + `font-semibold` text — inconsistent with §3 "Never re-typeset the wordmark"
- **file**: `projects/landing/web/src/app/(auth)/layout.tsx:11`
- **justification**: Landing topbar uses the custom `BrandMark` SVG at `topbar.tsx:52`, but auth layout falls back to "● SastaSpace" with a hard-coded dot and `font-semibold`. §3 requires the SVG wordmark be used.
- **suggested fix**: Render the same `BrandMark` + lowercase `sastaspace.` wordmark as in `topbar.tsx:22-25`. Same in `_template`.

### [P1] Title-cased `SastaSpace` in page titles / body copy — §3.1 wordmark is lowercase `sastaspace`
- **file**: `projects/landing/web/src/app/(auth)/sign-up/page.tsx:11`
- **justification**: §3.1 lowercase, §5 sentence-case-only. "SastaSpace" appears in metadata titles at `sign-in/page.tsx:5`, `sign-up/page.tsx:3`, `forgot-password/page.tsx:3`, `admin/page.tsx:4`, `admin/users/page.tsx:11`, and body copy "Sign in to continue to SastaSpace." / "Sign up to access SastaSpace."
- **suggested fix**: Replace `SastaSpace` → `sastaspace` in the six metadata titles and two body strings.

### [P1] Contact `POST /api/contact` has no `Origin` / CSRF check — Turnstile is the only mitigation, and currently absent
- **file**: `projects/landing/web/src/app/api/contact/route.ts:44`
- **justification**: Handler accepts any cross-origin JSON POST. Browsers pre-flight JSON, so cross-origin abuse is limited, but no `Origin` check means a compromised subdomain sharing the zone could POST on a user's behalf. Combined with P0 Turnstile absence, the route is effectively unauth'd.
- **suggested fix**: Once Turnstile is wired, add `Origin` check: reject unless `origin === "https://sastaspace.com"` or `origin.endsWith(".sastaspace.com")`.

### [P1] `lucide-react` pinned at `^1.8.0` — ancient major, pre-dates the current icon-set API
- **file**: `projects/landing/web/package.json:28`
- **justification**: *(Team-lead note: verified against npm registry — canonical `lucide-react` maintained by `lucide-icons/lucide` is at 1.9.0 as of 2026-04-23. The `^1.8.0` pin IS current. This finding is withdrawn.)* Original auditor reasoning preserved: current `lucide-react` is 0.4xx after rename; `^1.8.0` is 2020-era. Known peer-dep mismatch against React 19.2.4 (line 32). TS passes but tree-shaken exports differ from current docs.
- **suggested fix**: ~~`npm i lucide-react@latest`~~ — no change. Withdrawn.

---

## P2 — nice-to-have

### [P2] `Topbar` brand-mark SVG uses `fontFamily="var(--font-inter), sans-serif"` — CSS var doesn't resolve in an SVG text attribute
- **file**: `projects/landing/web/src/components/layout/topbar.tsx:73`
- **justification**: SVG `font-family` attribute doesn't resolve CSS vars in most engines; the "स/S" monogram falls back to system UI instead of Inter (§3.2).
- **suggested fix**: Use a `<style>` block inside the SVG or hardcode `fontFamily="Inter, system-ui, sans-serif"`.

### [P2] `StatusChip` "live" variant uses hardcoded `#8cc67a` — color not in the §4 palette
- **file**: `projects/landing/web/src/components/ui/status-chip.tsx:17`
- **justification**: §4 enumerates five colours, no green. Tiny decorative dot but un-documented colour.
- **suggested fix**: Use `var(--brand-sasta)` / `var(--brand-paper)`, or introduce `--brand-live: #8cc67a` in `globals.css:60-68` and document in §4.

### [P2] `brand/tokens.css:20` defines `--color-surface: #ffffff` — conflicts with §4's paper-not-white rule
- **file**: `brand/tokens.css:20`
- **justification**: `tokens.css` is the canonical reference for non-Next consumers per `design-log/003`. Pins `#ffffff` while §4 says paper (`#f5f1e8`). Next apps ignore it (they use `--card: var(--brand-paper-lifted)`), so no runtime effect today, but any external consumer reading tokens.css renders white cards.
- **suggested fix**: `--color-surface: var(--brand-paper-lifted, #fbf8f0);` in `tokens.css:20`. Add `--brand-paper-lifted` as a primitive.

### [P2] `_template/app/page.tsx` ships without a Devanagari mark and with off-brand "Project Bank" label
- **file**: `projects/_template/web/src/app/page.tsx:13`
- **justification**: §9 "Not monolingual. Removing the Devanagari removes half the idea." Template landing has no `font-deva` sub-line. "Project Bank" Badge is off-brand vs "sasta lab" (§1).
- **suggested fix**: Add `<p className="mt-2 font-deva text-base text-muted-foreground">__NAME__ · जो बनाना है, बनाओ.</p>` and replace "Project Bank" with terminal-prompt anchor `~/mohit · __NAME__.sastaspace.com` per §10 checklist 3.

---

## Cross-references (NOT findings in my scope)

- **Engineering**: `@supabase/ssr` 0.8.0, `next@16.2.1`, `react@19.2.4` current. ~~`lucide-react@^1.8.0` (P1) is the dep-bump risk.~~ *(withdrawn — see team-lead note)*
- **Engineering**: `_template/…/app-shell.tsx:9` accepts `projectName` but `landing/app-shell.tsx` no longer does — drift per design-log/003.
- **UX**: auth-page copy ("Welcome back", "Forgot your password?", "Continue with Google"/"…GitHub") is standard SaaS — per §2 owner may want lowercase-branded variants.

---

## Summary

- **P0: 9 · P1: 5 *(4 after lucide-react withdrawal)* · P2: 4**
- Top finding: Contact form never renders a Turnstile widget AND server silently skips verification when `TURNSTILE_SECRET_KEY` unset — unauth'd, unmitigated public endpoint. Second: unescaped HTML interpolation in Resend email body → XSS in owner's inbox.
- **Merge verdict: BLOCK.** Re-audit after Button/Input/Dialog/Sheet/Dropdown/Sonner shadow strip, Topbar blur removal, font-weight sweep (admin + auth + `_template`), Turnstile widget wiring + fail-closed server guard, and HTML-escape in `api/contact/route.ts`.
