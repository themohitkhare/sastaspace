# Phase 3: Core UI -- Landing + Progress + Result - Research

**Researched:** 2026-03-21
**Domain:** Next.js 16 App Router, SSE client, Motion animations, component library integration
**Confidence:** HIGH

## Summary

Phase 3 replaces the placeholder page with the complete user-facing flow: a polished landing page with an animated hero and center-stage URL input, a real-time progress experience consuming SSE events from FastAPI, and a result page with a blurred iframe teaser and shareable URL. The flow uses a single-page state machine at `/` (landing and progress share the same route) with `router.push` to `/<subdomain>/` on completion for shareability.

The project already has `motion` v12.38.0 installed (the rebranded framer-motion), Next.js 16.2.1 with App Router, shadcn v4 (base-nova style with oklch zinc tokens), and `@base-ui/react` + `lucide-react`. The component library at `components/` provides ready-made building blocks that need adaptation -- the Spotlight (aceternity) background uses `motion` with zero extra dependencies and provides subtle animated beams, and the Progress component (sean0205) provides Radix-based linear and circular progress bars.

**Primary recommendation:** Build three client components (LandingView, ProgressView, ResultView) orchestrated by a state machine in the root page component. Use `fetch()` + `ReadableStream` + `TextDecoderStream` for SSE. Use `aceternity/spotlight-new` as the hero background (depends only on `motion`, already installed). Use `sean0205/progress` for step progress bars (depends on `radix-ui`, already installed). Create `web/src/app/[subdomain]/page.tsx` as a server component that renders the ResultView.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Hero has subtle background motion/animation (dynamic and alive) -- not static
- **D-02:** URL input is center-stage dominant -- the entire hero is built around the input field (v0.dev / Perplexity pattern), not secondary to a headline
- **D-03:** "How it works" section uses a horizontal timeline with connected steps (3 steps: Enter URL -> AI Redesigns -> See Result)
- **D-04:** Tone is approachable and service-oriented -- targets non-technical business owners, not developers
- **D-05:** Single focused status line (not a vertical step list) -- one line of text updates with each SSE event
- **D-06:** Per-step progress indicators -- each of the 3 steps (crawling, redesigning, deploying) has its own visual loader/bar that activates and completes in sequence
- **D-07:** No time estimate -- PROG-05 is intentionally omitted
- **D-08:** Plain English step labels personalized to the submitted domain
- **D-09:** Technical SSE event names never shown to the user
- **D-10:** Blurred/obscured teaser of the redesigned site shown on the result page with "Take me to the future" button overlaid
- **D-11:** Clicking "Take me to the future" navigates to deployed redesign URL in same tab (full page navigation to `/<subdomain>/`)
- **D-12:** Sandboxed iframe serves as blurred teaser source
- **D-13:** Result page header: "Your new [domain] is ready" + teaser + CTA button + "View original site" link
- **D-14:** No contact form placeholder in Phase 3
- **D-15:** Shareable result URL (`/<subdomain>/`) shows adapted copy ("acme.com has been redesigned" vs "Your new acme.com is ready")
- **D-16:** Claude's discretion on all transition animations
- **D-17:** URL updates during flow: `/` (landing) -> `/` during progress -> `/<subdomain>/` on result
- **D-18:** Back button from result -> landing page (clean restart)
- **D-19:** Progress view lives at `/` as a state overlay -- no separate route, no history entry pushed

### Claude's Discretion
- Exact transition animation style and timing (landing -> progress -> result)
- Background effect choice from the component library (subtle motion, not overwhelming)
- Blur/overlay implementation for the result teaser
- Step loader animation style (per-step indicators)
- Exact domain name extraction logic from submitted URL

### Deferred Ideas (OUT OF SCOPE)
- Before/after interactive slider (DIFF-01) -- v2
- Shareable OG preview tags (DIFF-02) -- v2
- Contact form on result page -- Phase 4 (CONTACT-01 through CONTACT-06)
- Countdown timer / time estimate -- explicitly excluded per D-07
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LAND-01 | Hero section with large headline, subheadline, and URL input form | Spotlight background + custom URL input with favicon detection; center-stage layout |
| LAND-02 | URL input validates format before submission | Client-side URL validation using `new URL()` constructor + regex pattern |
| LAND-03 | "How it works" section (3 steps) | Custom horizontal timeline with connected step indicators, built with Tailwind |
| LAND-04 | Professional, high-design visual | Spotlight animation (motion), oklch zinc tokens, Inter typography, component library patterns |
| LAND-05 | Fully mobile responsive | Tailwind responsive breakpoints, mobile-first layout, touch targets >= 44px |
| PROG-01 | Page transitions to progress view (no full page reload) | React state machine at `/`, AnimatePresence for transitions |
| PROG-02 | SSE client connects via fetch() + ReadableStream | Verified pattern: POST fetch with ReadableStream + TextDecoderStream, parse SSE manually |
| PROG-03 | Named step display: each SSE event updates visible step indicator | Map SSE event names to plain English labels with domain personalization |
| PROG-04 | Animated progress bar advances through steps | Radix Progress primitives from sean0205/progress component, determinate per-step bars |
| PROG-05 | Estimated time remaining | INTENTIONALLY OMITTED per D-07. Requirement acknowledged but excluded by user decision. |
| PROG-06 | Error state handled gracefully with retry option | Error SSE event triggers error state with retry button that resubmits the URL |
| RESULT-01 | Redesigned HTML displayed in sandboxed iframe | `<iframe sandbox="allow-scripts" src="/<subdomain>/">` with CSS blur overlay |
| RESULT-02 | "View original site" link opens in new tab | `<a href={originalUrl} target="_blank" rel="noopener noreferrer">` |
| RESULT-03 | Result page is shareable (URL contains subdomain slug) | Dynamic route `web/src/app/[subdomain]/page.tsx` with `params: Promise<{ subdomain: string }>` |
| RESULT-04 | Page title updates | `generateMetadata` in `[subdomain]/page.tsx` returns dynamic title |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 16.2.1 | App Router framework | Already installed, project foundation |
| react | 19.2.4 | UI library | Already installed |
| motion | 12.38.0 | Page transitions, AnimatePresence, hero animation | Already installed, import from `motion/react` |
| @base-ui/react | ^1.3.0 | Base primitives (used by shadcn v4 Button) | Already installed |
| lucide-react | ^0.577.0 | Icons (Globe, ArrowRight, Check, AlertCircle) | Already installed |
| radix-ui | (via shadcn) | Progress primitive for progress bars | Available via shadcn add |
| tailwindcss | ^4 | Styling with oklch tokens | Already installed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| class-variance-authority | ^0.7.1 | Component variant styling | Already installed, use for custom component variants |
| clsx | ^2.1.1 | Conditional class merging | Already installed |
| tailwind-merge | ^3.5.0 | Tailwind class deduplication | Already installed via `cn()` util |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Spotlight (motion only) | Background Gradient Animation (CSS only, no deps) | Gradient is more colorful but sets body CSS vars which conflicts with zinc theme; requires custom keyframe CSS |
| Spotlight (motion only) | Animated Grid Pattern (motion) | Grid is more subtle but less "alive" feeling; good alternative if spotlight feels too bright |
| Spotlight (motion only) | Background Beams (motion) | Beams are elegant but SVG-heavy (50 paths); uses hardcoded brand colors that need zinc adaptation |
| Spotlight (motion only) | Sparkles (@tsparticles) | Sparkles require 3 additional heavy dependencies (@tsparticles/slim, /react, /engine); reject |
| Spotlight (motion only) | AI Input Hero (three, gsap) | Requires three.js + gsap -- far too heavy for this use case; reject |
| Custom progress | shadcn official progress | sean0205/progress provides both linear and circular variants, more flexible for per-step display |

**Installation:**
```bash
cd web && npx shadcn@latest add input label
```

Note: `button` is already installed. The `input` and `label` components are needed for the URL input form. The sean0205 progress component code should be manually placed (it uses `radix-ui` which is available via `@base-ui/react` or can be installed directly).

**Version verification:** All packages are already installed and pinned in `web/package.json`. No new npm packages needed beyond shadcn component additions.

## Architecture Patterns

### Recommended Project Structure
```
web/src/
  app/
    page.tsx                    # Landing page (server component wrapper)
    layout.tsx                  # Root layout (existing)
    globals.css                 # Theme tokens (existing)
    [subdomain]/
      page.tsx                  # Result page (server component, dynamic route)
  components/
    ui/
      button.tsx                # Existing shadcn button
      input.tsx                 # shadcn input (add via CLI)
      label.tsx                 # shadcn label (add via CLI)
      progress.tsx              # Progress bars (from sean0205 component)
    landing/
      hero-section.tsx          # Hero with Spotlight bg + URL input
      how-it-works.tsx          # Horizontal timeline section
      url-input-form.tsx        # URL input with validation + submit
    progress/
      progress-view.tsx         # Progress state container
      step-indicator.tsx        # Per-step progress bar + label
    result/
      result-view.tsx           # Result page content (blurred iframe + CTA)
    backgrounds/
      spotlight.tsx             # Aceternity Spotlight adapted for zinc theme
    app-flow.tsx                # State machine: landing | progress | result
  lib/
    utils.ts                    # Existing cn() utility
    sse-client.ts               # fetch() + ReadableStream SSE parser
    url-utils.ts                # URL validation, domain extraction
  hooks/
    use-redesign.ts             # SSE connection hook, state management
```

### Pattern 1: Single-Page State Machine
**What:** The root `page.tsx` renders a client component `AppFlow` that manages three states: `landing`, `progress`, and `result`. Only `result` has its own route (`/[subdomain]/`).
**When to use:** When multiple "views" share the same route and transitions should be smooth without full page reloads.
**Example:**
```typescript
// web/src/components/app-flow.tsx
"use client";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";

type AppState =
  | { phase: "landing" }
  | { phase: "progress"; url: string; domain: string }
  | { phase: "result"; subdomain: string; originalUrl: string; domain: string };

export function AppFlow() {
  const [state, setState] = useState<AppState>({ phase: "landing" });
  const router = useRouter();

  const handleSubmit = useCallback((url: string) => {
    const domain = extractDomain(url);
    setState({ phase: "progress", url, domain });
  }, []);

  const handleComplete = useCallback((subdomain: string, originalUrl: string, domain: string) => {
    setState({ phase: "result", subdomain, originalUrl, domain });
    // Push to shareable URL, replacing history so back goes to landing
    router.push(`/${subdomain}`);
  }, [router]);

  const handleReset = useCallback(() => {
    setState({ phase: "landing" });
  }, []);

  return (
    <AnimatePresence mode="wait">
      {state.phase === "landing" && (
        <motion.div key="landing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <LandingView onSubmit={handleSubmit} />
        </motion.div>
      )}
      {state.phase === "progress" && (
        <motion.div key="progress" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <ProgressView url={state.url} domain={state.domain} onComplete={handleComplete} onError={handleReset} />
        </motion.div>
      )}
      {/* result state: user is navigated away to /[subdomain]/ */}
    </AnimatePresence>
  );
}
```

### Pattern 2: SSE Client with fetch() + ReadableStream
**What:** POST-based SSE using the Fetch API's streaming body reader, parsing the `event:` / `data:` format manually.
**When to use:** When the SSE endpoint is POST (not GET), which is the case here because Cloudflare buffers GET SSE.
**Example:**
```typescript
// web/src/lib/sse-client.ts
export type SSEEvent = {
  event: string;
  data: Record<string, unknown>;
};

export async function* streamRedesign(
  url: string,
  apiBase: string = "http://localhost:8080"
): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${apiBase}/redesign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.error || `HTTP ${response.status}`);
  }

  const reader = response.body!
    .pipeThrough(new TextDecoderStream())
    .getReader();

  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += value;
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      const lines = part.split("\n");
      let eventName = "";
      let dataStr = "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventName = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          dataStr = line.slice(6);
        }
      }

      if (eventName && dataStr) {
        try {
          yield { event: eventName, data: JSON.parse(dataStr) };
        } catch {
          // skip malformed JSON
        }
      }
    }
  }
}
```

### Pattern 3: Dynamic Route for Shareable Result
**What:** `web/src/app/[subdomain]/page.tsx` renders the result page. It is a server component that receives `params` as a Promise (Next.js 16 pattern).
**When to use:** For the shareable result URL at `/<subdomain>/`.
**Critical Next.js 16 detail:** In Next.js 16, `params` is a `Promise` and MUST be awaited. Use `PageProps<'/[subdomain]'>` for type safety.
**Example:**
```typescript
// web/src/app/[subdomain]/page.tsx
import type { Metadata } from "next";
import { ResultView } from "@/components/result/result-view";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ subdomain: string }>;
}): Promise<Metadata> {
  const { subdomain } = await params;
  const domain = subdomain.replace(/-/g, ".");
  return {
    title: `Your redesign is ready -- SastaSpace`,
    description: `${domain} has been redesigned by AI`,
  };
}

export default async function ResultPage({
  params,
}: {
  params: Promise<{ subdomain: string }>;
}) {
  const { subdomain } = await params;
  return <ResultView subdomain={subdomain} isShareable />;
}
```

### Pattern 4: Blurred Iframe Teaser
**What:** A sandboxed iframe showing the redesigned site with a CSS `backdrop-filter: blur()` overlay. The overlay contains the CTA button.
**When to use:** For the result page teaser before the user clicks "Take me to the future".
**Example:**
```typescript
// Result teaser pattern
<div className="relative w-full aspect-video rounded-xl overflow-hidden border border-border">
  <iframe
    src={`/${subdomain}/`}
    sandbox="allow-scripts"
    className="w-full h-full"
    title="Your redesigned site preview"
  />
  <div className="absolute inset-0 backdrop-blur-md bg-background/30 flex flex-col items-center justify-center gap-4">
    <h2 className="text-2xl font-bold">Your new {domain} is ready</h2>
    <Button size="lg" asChild>
      <a href={`/${subdomain}/`}>Take me to the future</a>
    </Button>
  </div>
</div>
```

### Pattern 5: URL Validation and Domain Extraction
**What:** Client-side URL validation using the URL constructor, with domain extraction for personalized copy.
**Example:**
```typescript
// web/src/lib/url-utils.ts
export function validateUrl(input: string): { valid: boolean; url: string; error?: string } {
  let url = input.trim();

  // Prepend https:// if no protocol
  if (!/^https?:\/\//i.test(url)) {
    url = `https://${url}`;
  }

  try {
    const parsed = new URL(url);
    // Must have a valid hostname with at least one dot
    if (!parsed.hostname.includes(".")) {
      return { valid: false, url: input, error: "Please enter a valid website address" };
    }
    return { valid: true, url: parsed.href };
  } catch {
    return { valid: false, url: input, error: "Please enter a valid website address" };
  }
}

export function extractDomain(url: string): string {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    // Remove www. prefix for cleaner display
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
```

### Anti-Patterns to Avoid
- **EventSource for SSE:** EventSource only works with GET requests. Cloudflare buffers GET SSE. MUST use fetch() + ReadableStream with POST.
- **Synchronous params access:** Next.js 16 `params` is a Promise. Always `await params` or use `use(params)` in client components. Synchronous access is deprecated and will break.
- **iframe without sandbox:** NEVER use `allow-same-origin` in the sandbox attribute -- the iframe loads user-generated (LLM-generated) HTML and must be fully sandboxed.
- **Hardcoding API URL:** The FastAPI URL (`http://localhost:8080`) will differ in production (Cloudflare tunnel). Use an environment variable or derive from `window.location` context.
- **Using `framer-motion` import path:** The package is `motion` v12+. Import from `motion/react`, NOT from `framer-motion`. The spotlight-new component already uses the correct import.
- **Body CSS variable mutation:** The background-gradient-animation component sets CSS vars on `document.body` which would conflict with the oklch zinc theme. Avoid this component.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE text parsing | Custom event parser from scratch | Pattern from architecture section (buffer + split on `\n\n`) | Edge cases: partial chunks, multi-line data, buffered delivery |
| Progress bar | Custom div-based progress animation | Radix Progress primitive (sean0205 component) | Accessibility (aria-valuenow, role=progressbar), smooth CSS transitions |
| URL validation | Complex regex | `new URL()` constructor + hostname check | URL spec is complex, browser native handles edge cases |
| Page transitions | Manual CSS transitions with conditional rendering | Motion `AnimatePresence` with `mode="wait"` | Exit animations, mount/unmount coordination, layout shifts |
| Animated background | Custom canvas/WebGL shader | Spotlight component from aceternity | Subtle, performant, uses only `motion` (already installed) |
| Form input | Raw `<input>` with custom styling | shadcn `Input` + `Label` components | Consistent design tokens, accessibility, focus states |

**Key insight:** The component library has ready-made pieces that use the exact dependencies already installed (`motion`, `radix-ui`, `lucide-react`). Adapting these is faster and more reliable than building from scratch.

## Common Pitfalls

### Pitfall 1: SSE Stream Parsing with Partial Chunks
**What goes wrong:** ReadableStream delivers data in arbitrary chunks, which may split SSE events mid-line. Naive line-by-line parsing misses events or produces invalid JSON.
**Why it happens:** Network buffering, TCP segmentation, proxy behavior.
**How to avoid:** Always buffer incoming text and split on `\n\n` (double newline = event boundary). Only process complete events; keep remainder in buffer for next chunk.
**Warning signs:** Missing events, JSON parse errors in console, events that work locally but fail through Cloudflare tunnel.

### Pitfall 2: Next.js 16 Async Params
**What goes wrong:** Accessing `params.subdomain` directly (without await) returns a Promise object, not a string. Components render `[object Promise]`.
**Why it happens:** Next.js 16 changed params to be a Promise for all route components. This is a breaking change from earlier versions.
**How to avoid:** Always `await params` in server components, use `use(params)` in client components. Type as `params: Promise<{ subdomain: string }>`.
**Warning signs:** Rendered text shows `[object Promise]`, TypeScript errors about Promise types.

### Pitfall 3: iframe Same-Origin Sandbox Escape
**What goes wrong:** Adding `allow-same-origin` to the iframe sandbox lets the embedded HTML access the parent page's DOM, cookies, and JavaScript context.
**Why it happens:** Developer adds `allow-same-origin` to make things "work" when scripts in the iframe try to access parent resources.
**How to avoid:** Use `sandbox="allow-scripts"` ONLY. No `allow-same-origin`. The embedded HTML is LLM-generated and untrusted.
**Warning signs:** iframe content modifying parent page styles, unexpected cookie access.

### Pitfall 4: Motion Import Path
**What goes wrong:** Using `import { motion } from "framer-motion"` fails because the installed package is `motion` v12, not `framer-motion`.
**Why it happens:** Most examples online still reference `framer-motion`. The package was rebranded.
**How to avoid:** Always import from `motion/react`: `import { motion, AnimatePresence } from "motion/react"`.
**Warning signs:** Module not found errors, build failures.

### Pitfall 5: Progress State Desync on Error
**What goes wrong:** SSE stream errors leave the progress UI in a stuck state (loading spinner that never completes).
**Why it happens:** The SSE error event or network failure isn't caught, so the UI never transitions to error state.
**How to avoid:** Wrap the SSE generator consumption in try/catch. Handle both SSE `error` events AND network/fetch errors. Always provide a clear "try again" path.
**Warning signs:** Users see infinite loading with no way to recover.

### Pitfall 6: Cloudflare Tunnel URL for API
**What goes wrong:** Hardcoded `http://localhost:8080` works in dev but breaks in production where the browser should call the same origin (Cloudflare routes `/api/*` to FastAPI).
**Why it happens:** Dev and prod have different API base URLs.
**How to avoid:** Use a configurable API base URL. In dev, use `http://localhost:8080`. In production, use relative `/api/redesign` (after confirming Cloudflare tunnel routes correctly) or the tunnel URL. Consider a `NEXT_PUBLIC_API_URL` environment variable.
**Warning signs:** CORS errors in production, requests going to wrong host.

### Pitfall 7: Back Button Behavior from Result
**What goes wrong:** Pressing back from `/<subdomain>/` navigates to the progress view (broken state with no active SSE stream).
**Why it happens:** The progress view was rendered at `/` and is still in browser history.
**How to avoid:** Per D-19, progress view does NOT push a history entry. Use `router.push` (not replace) when navigating to result. The landing page at `/` is the only entry in history, so back goes straight to landing. Alternatively, detect navigation back to `/` and reset to landing state.
**Warning signs:** Users see a broken progress screen with no active stream.

## Code Examples

### SSE Event Name to User-Facing Copy Mapping
```typescript
// Source: CONTEXT.md D-08, D-09
const stepLabels = {
  crawling: (domain: string) => `Analyzing ${domain}`,
  redesigning: (_domain: string) => "Redesigning your site with AI",
  deploying: (domain: string) => `Preparing your new ${domain}`,
  done: (_domain: string) => "Your redesign is ready!",
} as const;

// SSE progress values from Phase 1 API contract
const stepProgress = {
  crawling: 10,
  redesigning: 40,
  deploying: 80,
  done: 100,
} as const;
```

### Motion AnimatePresence for Page Transitions
```typescript
// Source: motion v12 docs (motion/react)
import { AnimatePresence, motion } from "motion/react";

// Wrap views in AnimatePresence with mode="wait" for sequential exit/enter
<AnimatePresence mode="wait">
  <motion.div
    key={currentPhase}
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -20 }}
    transition={{ duration: 0.3, ease: "easeInOut" }}
  >
    {/* Current view */}
  </motion.div>
</AnimatePresence>
```

### Spotlight Background Adapted for Zinc Theme
```typescript
// Source: aceternity/spotlight-new component, adapted for oklch zinc
// The Spotlight component uses hsla gradients by default.
// For the zinc theme, override gradient props with zinc-compatible values:
<Spotlight
  gradientFirst="radial-gradient(68.54% 68.72% at 55.02% 31.46%, oklch(0.8 0 0 / 0.08) 0, oklch(0.5 0 0 / 0.02) 50%, oklch(0.4 0 0 / 0) 80%)"
  gradientSecond="radial-gradient(50% 50% at 50% 50%, oklch(0.8 0 0 / 0.06) 0, oklch(0.5 0 0 / 0.02) 80%, transparent 100%)"
  gradientThird="radial-gradient(50% 50% at 50% 50%, oklch(0.8 0 0 / 0.04) 0, oklch(0.4 0 0 / 0.02) 80%, transparent 100%)"
/>
```

### Dynamic Metadata in Next.js 16
```typescript
// Source: Next.js 16 docs (node_modules/next/dist/docs)
import type { Metadata } from "next";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ subdomain: string }>;
}): Promise<Metadata> {
  const { subdomain } = await params;
  return {
    title: "Your redesign is ready -- SastaSpace",
  };
}
```

### Client Component with Dynamic Params (Next.js 16)
```typescript
// Source: Next.js 16 dynamic-routes.md
'use client'
import { use } from 'react'

export default function ResultPage({
  params,
}: {
  params: Promise<{ subdomain: string }>
}) {
  const { subdomain } = use(params)
  return <ResultView subdomain={subdomain} />
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `framer-motion` package | `motion` package (v12+) | 2024 | Import from `motion/react`, not `framer-motion` |
| Sync `params` in page components | Async `params` (Promise) | Next.js 15+ | Must await params or use `use()` hook |
| shadcn `new-york` style | shadcn `base-nova` style | shadcn v4.1.0 | Uses `@base-ui/react` instead of `@radix-ui/react` primitives |
| hsl color space | oklch color space | shadcn v4 | All theme variables use oklch format |
| EventSource API for SSE | fetch() + ReadableStream | N/A (project constraint) | POST-based SSE required due to Cloudflare GET buffering |

**Deprecated/outdated:**
- `framer-motion` import path: Use `motion/react` instead
- Synchronous params access: Deprecated in Next.js 16, will be removed
- `@radix-ui/react-*` packages: shadcn v4 base-nova uses `@base-ui/react` primitives (but `radix-ui` package is still usable for Progress)

## Open Questions

1. **API URL in Production**
   - What we know: Dev uses `http://localhost:8080`, Cloudflare tunnel routes `/api/*` to FastAPI
   - What's unclear: Whether the frontend POST to `/redesign` should use a relative path or an env var in production
   - Recommendation: Use `NEXT_PUBLIC_API_BASE` env var, defaulting to `http://localhost:8080` for dev. In production behind Cloudflare, this can be set to empty string (relative) or the tunnel URL.

2. **iframe src for Blurred Teaser**
   - What we know: Deployed HTML lives at `/<subdomain>/` served by FastAPI's static file server
   - What's unclear: In production behind Cloudflare tunnel, whether the iframe src needs the full URL or can use a relative path
   - Recommendation: Use relative path `/${subdomain}/` which will work both in dev (if FastAPI serves it) and in production (Cloudflare routes appropriately). The iframe sandbox prevents same-origin issues.

3. **Progress Component Dependency**
   - What we know: sean0205/progress uses `radix-ui` import (`import { Progress } from 'radix-ui'`), but the project uses `@base-ui/react`
   - What's unclear: Whether the radix-ui progress primitive is included in @base-ui/react or needs separate installation
   - Recommendation: Install the standalone progress primitive via `npx shadcn@latest add progress` which will handle the dependency correctly for the base-nova style. If shadcn v4 doesn't have a progress component, manually create one using the `@base-ui/react` Slider or a simple CSS-animated div.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Manual visual testing + ESLint |
| Config file | `web/eslint.config.js` (via eslint-config-next) |
| Quick run command | `cd web && npm run lint` |
| Full suite command | `cd web && npm run build && npm run lint` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LAND-01 | Hero section renders with headline, subheadline, URL input | smoke | `cd web && npm run build` | N/A (build test) |
| LAND-02 | URL validation rejects invalid, accepts valid | unit | Manual: test `validateUrl()` function directly | Wave 0 |
| LAND-03 | "How it works" section renders 3 steps | smoke | `cd web && npm run build` | N/A |
| LAND-04 | Professional visual appearance | manual-only | Visual inspection in browser | N/A |
| LAND-05 | Mobile responsive | manual-only | Browser dev tools responsive mode (375px) | N/A |
| PROG-01 | State transition from landing to progress | manual-only | Submit URL in browser, observe transition | N/A |
| PROG-02 | SSE client connects via fetch + ReadableStream | unit | Test `streamRedesign()` generator with mock Response | Wave 0 |
| PROG-03 | Step display updates per SSE event | manual-only | Submit URL, observe step labels update | N/A |
| PROG-04 | Progress bar animates through steps | manual-only | Submit URL, observe progress bar advancement | N/A |
| PROG-05 | Time estimate (OMITTED) | N/A | N/A -- intentionally excluded per D-07 | N/A |
| PROG-06 | Error state with retry option | manual-only | Submit invalid URL or kill backend, observe error + retry | N/A |
| RESULT-01 | Sandboxed iframe displays redesign | manual-only | Complete redesign flow, inspect iframe in DevTools | N/A |
| RESULT-02 | "View original site" link opens new tab | manual-only | Click link on result page | N/A |
| RESULT-03 | Result URL is shareable | smoke | Navigate directly to `/test-subdomain/` in browser | N/A |
| RESULT-04 | Page title updates | smoke | `cd web && npm run build` (generateMetadata compiles) | N/A |

### Sampling Rate
- **Per task commit:** `cd web && npm run lint && npm run build`
- **Per wave merge:** `cd web && npm run build` + manual visual check of all three views
- **Phase gate:** Full build green + manual walkthrough of complete flow (submit URL -> progress -> result -> shareable URL)

### Wave 0 Gaps
- [ ] `web/src/lib/__tests__/url-utils.test.ts` -- covers LAND-02 (URL validation logic)
- [ ] `web/src/lib/__tests__/sse-client.test.ts` -- covers PROG-02 (SSE parsing logic)
- [ ] Test framework setup: Consider adding Vitest (`npm install -D vitest @testing-library/react`) for unit tests of pure functions. Optional for Phase 3 given the primarily visual nature of this phase.

*(Note: This phase is primarily UI/visual. Most requirements are verified through build success + manual visual inspection. Unit tests are valuable for the pure logic functions -- URL validation and SSE parsing -- but the visual/interaction requirements are manual-only.)*

## Sources

### Primary (HIGH confidence)
- Next.js 16.2.1 docs at `web/node_modules/next/dist/docs/` -- dynamic routes, params Promise pattern, useRouter, generateMetadata
- `web/package.json` -- verified installed dependency versions
- `web/components.json` -- shadcn v4 base-nova configuration
- `web/src/app/globals.css` -- oklch zinc theme tokens

### Secondary (MEDIUM confidence)
- Component library JSON files at `components/` -- Spotlight, Progress, URL Input, background components reviewed with dependency analysis
- Phase 1 CONTEXT.md -- SSE event payload shape, event names, progress values
- Phase 2 UI-SPEC.md -- design system tokens (spacing, typography, color)

### Tertiary (LOW confidence)
- Motion v12 import paths (`motion/react`) -- verified via package.json exports but not tested at runtime

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages already installed and verified in package.json
- Architecture: HIGH -- Next.js 16 dynamic routes verified against bundled docs, SSE pattern well-understood from Phase 1 API contract
- Pitfalls: HIGH -- async params pattern verified in Next.js 16 docs, motion import path verified in package exports
- Component library: MEDIUM -- components reviewed from JSON files, code quality varies, may need adaptation

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable stack, all deps pinned)
