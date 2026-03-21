# Phase 4: Contact Form + Polish - Research

**Researched:** 2026-03-21
**Domain:** Contact form (Resend email + Cloudflare Turnstile spam protection), mobile polish
**Confidence:** HIGH

## Summary

Phase 4 adds a contact form to the result page, wires it to Resend for email delivery, protects it with Cloudflare Turnstile (invisible mode) plus a honeypot field, and performs a targeted mobile polish pass across all three pages.

The technical surface is straightforward: a single Next.js Route Handler (`POST /api/contact`) that validates a honeypot, verifies a Turnstile token against Cloudflare's siteverify API, and sends an HTML email via the Resend SDK. The frontend form uses existing shadcn UI components (`Input`, `Label`, `Button`) and existing motion patterns (`AnimatePresence`) for the form-to-success-state transition. Two new npm packages are needed: `resend` and `@marsidev/react-turnstile`.

**Primary recommendation:** Build the API route first (testable in isolation with curl), then the form component, then the mobile polish pass. Keep the form component as a standalone `ContactForm` extracted from `ResultView` to maintain single-responsibility.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Form lives in `result-view.tsx` below existing content, separated by `<hr>` + ~48px spacing
- D-02: Headline: "Like what you see? Let's build the real thing." as h2
- D-03: Form width: `max-w-xl`, centered
- D-04: Fields: Name (text), Email (email), Message (textarea rows=4). Use existing shadcn Input/Label. Textarea styled to match.
- D-05: Submit button: full-width, bg-primary style
- D-06: On success, swap form for thank-you using AnimatePresence (fade out/in)
- D-07: Thank-you copy: "Thanks, I'll be in touch." + subtext "I typically reply within 24 hours."
- D-08: No toast, no banner, no redirect -- inline swap only
- D-09: Turnstile in invisible mode -- no visible widget
- D-10: Honeypot: hidden input name="website" tabIndex={-1} autoComplete="off"
- D-11: Turnstile widget via `@marsidev/react-turnstile`
- D-12: Next.js Route Handler at `web/src/app/api/contact/route.ts` (POST)
- D-13: Server flow: honeypot check -> Turnstile verify -> Resend send -> return { ok: true }
- D-14: No rate limiting in Phase 4
- D-15: HTML email, subject: "New inquiry from {name} -- SastaSpace"
- D-16: Email body: name, email (as reply-to), message, subdomain viewed
- D-17: from: noreply@sastaspace.com, to: OWNER_EMAIL env var
- D-18: New env vars: RESEND_API_KEY, OWNER_EMAIL, NEXT_PUBLIC_TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY
- D-19: Mobile QA: targeted pass at 375px, not a redesign
- D-20: Fix overflow-x issues
- D-21: No new animations, typography, or color changes

### Claude's Discretion
- Exact Tailwind spacing between form sections
- Error message copy for individual fields
- Textarea resize behavior (resize-none)
- Loading state on submit button ("Sending..." with spinner using existing motion package)

### Deferred Ideas (OUT OF SCOPE)
- Rate limiting on contact endpoint
- Email confirmation to submitter
- Storing submissions in database
- OG tags / social preview images (DIFF-02)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONTACT-01 | Contact form on result page with headline "Like what you see? Let's build the real thing." | Form component in result-view.tsx, existing shadcn components |
| CONTACT-02 | 3 fields only: Name, Email, Message | Input/Label/textarea -- all available in current UI kit |
| CONTACT-03 | Cloudflare Turnstile widget + honeypot field for spam protection | @marsidev/react-turnstile invisible mode + hidden input honeypot pattern |
| CONTACT-04 | Form submission sends email via Resend to owner's inbox | Resend SDK `emails.send()` in Next.js Route Handler, reply-to pattern |
| CONTACT-05 | Success state confirms submission without leaving result page | AnimatePresence swap pattern (same as app-flow.tsx) |
| CONTACT-06 | No phone number field | Form only renders Name, Email, Message -- enforced by component design |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| resend | 6.9.4 | Email delivery SDK | Official Resend SDK; simple `emails.send()` API, first-class Next.js support |
| @marsidev/react-turnstile | 1.4.2 | Cloudflare Turnstile React wrapper | Lightweight, ref-based API, supports invisible mode, recommended by Cloudflare community resources |

### Already Installed (reuse)
| Library | Version | Purpose |
|---------|---------|---------|
| motion | ^12.38.0 | AnimatePresence for form/success swap |
| lucide-react | ^0.577.0 | Icons (Loader2 for spinner) |
| next | 16.2.1 | Route Handlers for API endpoint |
| shadcn UI components | 4.1.0 | Input, Label, Button |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @marsidev/react-turnstile | react-turnstile | @marsidev version has better TypeScript types, ref methods, and invisible mode support |
| Resend SDK | nodemailer + SMTP | Resend is simpler (3 lines of code), no SMTP config, built for transactional email |
| Honeypot | reCAPTCHA v3 | Honeypot is zero-dependency, zero-friction; combined with Turnstile it's sufficient |

**Installation:**
```bash
cd web && npm install resend @marsidev/react-turnstile
```

## Architecture Patterns

### New Files
```
web/src/
├── app/api/contact/
│   └── route.ts           # POST handler: honeypot -> turnstile -> resend -> response
├── components/result/
│   ├── result-view.tsx     # MODIFIED: add ContactForm below iframe
│   └── contact-form.tsx    # NEW: form + success state component
└── .env.example            # NEW: document required env vars
```

### Pattern 1: Next.js Route Handler (POST)
**What:** Server-side API endpoint using Next.js App Router conventions
**When to use:** Processing form submissions that need server-side secrets
**Example:**
```typescript
// Source: Resend official docs + Cloudflare Turnstile docs
import { Resend } from "resend";
import { NextRequest } from "next/server";

const resend = new Resend(process.env.RESEND_API_KEY);

export async function POST(request: NextRequest) {
  const body = await request.json();

  // 1. Honeypot check
  if (body.website) {
    // Bot filled the hidden field -- return 200 to not reveal detection
    return Response.json({ ok: true });
  }

  // 2. Turnstile verification
  const turnstileRes = await fetch(
    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        secret: process.env.TURNSTILE_SECRET_KEY,
        response: body.turnstileToken,
      }),
    }
  );
  const turnstileData = await turnstileRes.json();
  if (!turnstileData.success) {
    return Response.json({ error: "Verification failed" }, { status: 400 });
  }

  // 3. Send email via Resend
  const { error } = await resend.emails.send({
    from: `SastaSpace <noreply@sastaspace.com>`,
    to: [process.env.OWNER_EMAIL!],
    replyTo: body.email,
    subject: `New inquiry from ${body.name} — SastaSpace`,
    html: `<p><strong>From:</strong> ${body.name} (${body.email})</p>
           <p><strong>Was viewing:</strong> ${body.subdomain}</p>
           <hr/>
           <p>${body.message}</p>`,
  });

  if (error) {
    return Response.json({ error: "Failed to send" }, { status: 500 });
  }

  return Response.json({ ok: true });
}
```

### Pattern 2: Invisible Turnstile with Token Retrieval
**What:** Render Turnstile widget invisibly, get token via ref before form submit
**When to use:** Spam protection without user-facing CAPTCHA
**Example:**
```typescript
// Source: @marsidev/react-turnstile docs
import { Turnstile, type TurnstileInstance } from "@marsidev/react-turnstile";
import { useRef, useState } from "react";

const turnstileRef = useRef<TurnstileInstance>(null);
const [token, setToken] = useState<string | null>(null);

// In JSX:
<Turnstile
  ref={turnstileRef}
  siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!}
  onSuccess={setToken}
  onExpire={() => {
    setToken(null);
    turnstileRef.current?.reset();
  }}
  options={{ size: "invisible" }}
/>

// On form submit, include token in the payload
// After successful submit, call turnstileRef.current?.reset()
```

### Pattern 3: Form State Machine (matches existing codebase)
**What:** useState-based form status tracking
**When to use:** Simple forms without complex validation needs
**Example:**
```typescript
// Matches use-redesign.ts pattern from Phase 3
type FormStatus = "idle" | "submitting" | "success" | "error";
const [status, setStatus] = useState<FormStatus>("idle");
```

### Pattern 4: AnimatePresence Swap (matches app-flow.tsx)
**What:** Animate between form and success state
**When to use:** Inline state transitions without page navigation
**Example:**
```typescript
// Source: existing app-flow.tsx pattern
<AnimatePresence mode="wait">
  {status !== "success" ? (
    <motion.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      {/* form fields */}
    </motion.div>
  ) : (
    <motion.div key="thanks" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      {/* thank you message */}
    </motion.div>
  )}
</AnimatePresence>
```

### Anti-Patterns to Avoid
- **Exposing TURNSTILE_SECRET_KEY client-side:** The secret key must only exist in the Route Handler (server-side). Only NEXT_PUBLIC_TURNSTILE_SITE_KEY goes to the browser.
- **Revealing honeypot detection to bots:** Always return `{ ok: true }` when honeypot triggers -- never return an error that reveals the detection mechanism.
- **Using `resend` in client components:** Resend SDK uses the API key and must only run server-side in Route Handlers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Email delivery | Custom SMTP/nodemailer setup | Resend SDK | 3-line integration, handles retries, deliverability, bounce tracking |
| CAPTCHA/bot protection | Custom challenge system | Cloudflare Turnstile (invisible) | Free, privacy-friendly, maintained by Cloudflare, invisible mode = zero friction |
| Turnstile React binding | Manual script injection + window.turnstile | @marsidev/react-turnstile | Handles script loading, cleanup, SSR safety, ref methods for token retrieval |
| HTML email sanitization | String concatenation | Template literal with explicit escaping | Prevent XSS in email body from user-submitted name/message |

**Key insight:** The contact form is a standard pattern with well-established library support. The only custom code needed is the glue: the Route Handler that chains honeypot check -> Turnstile verify -> Resend send.

## Common Pitfalls

### Pitfall 1: Turnstile Token Expiration
**What goes wrong:** User opens result page, waits 5+ minutes, then fills form -- token has expired
**Why it happens:** Turnstile tokens expire after 300 seconds (5 minutes)
**How to avoid:** Use `onExpire` callback to reset the widget and clear the stored token. Disable submit button when token is null. Use `refreshExpired: "auto"` option (default).
**Warning signs:** Server returns `timeout-or-duplicate` error code

### Pitfall 2: Honeypot Return Value Leaks Detection
**What goes wrong:** Returning a 400/422 error when honeypot triggers tells bots they were caught
**Why it happens:** Developer treats honeypot like validation error
**How to avoid:** Always return `{ ok: true }` with status 200 -- make the bot think submission succeeded
**Warning signs:** Bot operators adapt their scrapers to avoid the honeypot field

### Pitfall 3: Missing reply-to on Resend Email
**What goes wrong:** Owner receives inquiry email but can't hit "Reply" to respond to the lead
**Why it happens:** Developer puts submitter email in `to` or `cc` instead of `replyTo`
**How to avoid:** Set `replyTo: body.email` in Resend's `emails.send()` config
**Warning signs:** Owner has to manually copy-paste email address to reply

### Pitfall 4: XSS in Email HTML Body
**What goes wrong:** Malicious user submits `<script>` tags in name/message fields, which render in the HTML email
**Why it happens:** Direct string interpolation of user input into HTML email template
**How to avoid:** Escape HTML entities in user-provided fields before inserting into the email body, or use plain text email
**Warning signs:** Any user input appearing unescaped in HTML template

### Pitfall 5: Turnstile Widget in "use client" vs Server Component
**What goes wrong:** Turnstile component renders on server and crashes (needs browser APIs)
**Why it happens:** @marsidev/react-turnstile requires DOM access
**How to avoid:** Ensure ContactForm component has `"use client"` directive. ResultView already has it.
**Warning signs:** Hydration errors, "window is not defined" errors

### Pitfall 6: Textarea Not Matching Input Styling
**What goes wrong:** Native textarea looks different from shadcn Input components (border, focus ring, colors)
**Why it happens:** shadcn does not ship a Textarea component in the current setup; native textarea has different defaults
**How to avoid:** Apply matching Tailwind classes: same border, rounded-lg, focus-visible ring, bg-background, text-foreground, px-3 py-2
**Warning signs:** Visual inconsistency between input fields and textarea

### Pitfall 7: NEXT_PUBLIC_ Prefix Requirement
**What goes wrong:** Turnstile site key is undefined in client component
**Why it happens:** Next.js only exposes env vars with `NEXT_PUBLIC_` prefix to client bundles
**How to avoid:** Name the var `NEXT_PUBLIC_TURNSTILE_SITE_KEY` (already specified in D-18)
**Warning signs:** `undefined` value in browser console, Turnstile fails to render

## Code Examples

### Contact API Route Handler (complete)
```typescript
// web/src/app/api/contact/route.ts
// Source: Resend docs + Cloudflare Turnstile docs
import { NextRequest } from "next/server";
import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, email, message, website, turnstileToken, subdomain } = body;

    // 1. Honeypot -- return success to not reveal detection
    if (website) {
      return Response.json({ ok: true });
    }

    // 2. Basic server-side validation
    if (!name?.trim() || !email?.trim() || !message?.trim()) {
      return Response.json({ error: "All fields are required" }, { status: 400 });
    }

    // 3. Turnstile verification
    const turnstileRes = await fetch(
      "https://challenges.cloudflare.com/turnstile/v0/siteverify",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          secret: process.env.TURNSTILE_SECRET_KEY,
          response: turnstileToken,
        }),
      }
    );
    const turnstileData = await turnstileRes.json();
    if (!turnstileData.success) {
      return Response.json({ error: "Verification failed" }, { status: 400 });
    }

    // 4. Send email
    const domain = subdomain?.replace(/-/g, ".") || "unknown";
    const { error } = await resend.emails.send({
      from: `SastaSpace <noreply@sastaspace.com>`,
      to: [process.env.OWNER_EMAIL!],
      replyTo: email,
      subject: `New inquiry from ${escapeHtml(name)} — SastaSpace`,
      html: `
        <h2>New inquiry from SastaSpace</h2>
        <p><strong>Name:</strong> ${escapeHtml(name)}</p>
        <p><strong>Email:</strong> ${escapeHtml(email)}</p>
        <p><strong>Was viewing:</strong> ${escapeHtml(domain)}</p>
        <hr />
        <p>${escapeHtml(message).replace(/\n/g, "<br />")}</p>
      `,
    });

    if (error) {
      console.error("Resend error:", error);
      return Response.json({ error: "Failed to send message" }, { status: 500 });
    }

    return Response.json({ ok: true });
  } catch {
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}
```

### Invisible Turnstile Integration
```typescript
// Inside ContactForm component
import { Turnstile, type TurnstileInstance } from "@marsidev/react-turnstile";

const turnstileRef = useRef<TurnstileInstance>(null);
const [turnstileToken, setTurnstileToken] = useState<string | null>(null);

// In JSX (renders nothing visible in invisible mode):
<Turnstile
  ref={turnstileRef}
  siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!}
  onSuccess={setTurnstileToken}
  onExpire={() => {
    setTurnstileToken(null);
    turnstileRef.current?.reset();
  }}
  options={{ size: "invisible" }}
/>

// On submit: include turnstileToken in fetch body
// After submit: turnstileRef.current?.reset()
```

### Textarea Styled to Match shadcn Input
```typescript
// Match the Input component's visual style
<textarea
  id="message"
  name="message"
  rows={4}
  required
  value={message}
  onChange={(e) => setMessage(e.target.value)}
  className="flex w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground shadow-xs placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 outline-none resize-none"
  placeholder="Tell me about your project..."
/>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| reCAPTCHA v2 (checkbox) | Cloudflare Turnstile (invisible) | 2022+ | Zero-friction, privacy-friendly, free |
| nodemailer + SMTP | Resend SDK | 2023+ | 3-line setup, no SMTP config needed |
| Google reCAPTCHA v3 | Cloudflare Turnstile | 2023+ | No Google dependency, better privacy story |

**Deprecated/outdated:**
- `@cloudflare/turnstile` package does not exist -- use `@marsidev/react-turnstile` (community-maintained, Cloudflare-recommended)
- `resend.sendEmail()` is deprecated -- use `resend.emails.send()` (current API)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None currently installed |
| Config file | none -- Wave 0 must set up |
| Quick run command | `cd web && npx vitest run --reporter=verbose` |
| Full suite command | `cd web && npx vitest run` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONTACT-01 | Form renders with correct headline below result content | manual-only | Visual check at /[subdomain] page | N/A |
| CONTACT-02 | Form has exactly 3 fields: Name, Email, Message | manual-only | Visual check | N/A |
| CONTACT-03 | Honeypot rejection + Turnstile token verification | unit | `npx vitest run src/app/api/contact/route.test.ts` | No -- Wave 0 |
| CONTACT-04 | Successful email delivery via Resend | unit (mocked) | `npx vitest run src/app/api/contact/route.test.ts` | No -- Wave 0 |
| CONTACT-05 | Inline success state without page navigation | manual-only | Visual check -- submit form, verify swap | N/A |
| CONTACT-06 | No phone number field exists | manual-only | Visual check | N/A |

### Sampling Rate
- **Per task commit:** Visual check in browser (form render, submit, success state)
- **Per wave merge:** Full browser walkthrough of result page + contact flow
- **Phase gate:** Manual QA at 375px width on all 3 pages + API route unit tests (if set up)

### Wave 0 Gaps
- [ ] Test framework (vitest) not yet installed -- install only if unit tests for API route are planned
- [ ] `web/src/app/api/contact/route.test.ts` -- covers CONTACT-03, CONTACT-04
- [ ] Most requirements are UI/visual and best verified manually at this project scale

## Open Questions

1. **Resend domain verification**
   - What we know: Resend requires domain verification to send from custom domains (noreply@sastaspace.com)
   - What's unclear: Whether the domain is already configured in Resend dashboard
   - Recommendation: First task should include env var setup instructions; use `onboarding@resend.dev` as fallback during development

2. **Cloudflare Turnstile site setup**
   - What we know: Need to create a Turnstile widget in Cloudflare dashboard to get site key + secret key
   - What's unclear: Whether the Cloudflare account already has a Turnstile widget configured
   - Recommendation: Document Turnstile setup steps in env var task; use test keys for development (`1x00000000000000000000AA` / `1x0000000000000000000000000000000AA`)

3. **Invisible Turnstile behavior on result page**
   - What we know: Invisible mode runs silently with no visible widget; `size: "invisible"` in options
   - What's unclear: Whether invisible mode is set per-widget in Cloudflare dashboard or via component props
   - Recommendation: Widget type (managed/invisible) is set in Cloudflare dashboard when creating the site key. The `options.size` prop controls the visual rendering. For true invisible behavior, create the widget as "Invisible" type in the dashboard AND set `size: "invisible"` in props.

## Sources

### Primary (HIGH confidence)
- [Resend Next.js docs](https://resend.com/docs/send-with-nextjs) -- emails.send() API, Route Handler pattern
- [Cloudflare Turnstile server-side validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/) -- siteverify endpoint, token handling
- [@marsidev/react-turnstile docs](https://docs.page/marsidev/react-turnstile) -- props, ref methods, invisible mode
- Existing codebase: result-view.tsx, url-input-form.tsx, app-flow.tsx -- established patterns

### Secondary (MEDIUM confidence)
- [npm registry](https://www.npmjs.com/package/resend) -- resend v6.9.4 verified current
- [npm registry](https://www.npmjs.com/package/@marsidev/react-turnstile) -- v1.4.2 verified current

### Tertiary (LOW confidence)
- None -- all findings verified against official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- both packages well-documented, versions verified against npm registry
- Architecture: HIGH -- follows established codebase patterns exactly (AnimatePresence, useState state machine, shadcn components)
- Pitfalls: HIGH -- all pitfalls sourced from official docs (token expiration, NEXT_PUBLIC prefix, server-only secrets)

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable libraries, unlikely to change)
