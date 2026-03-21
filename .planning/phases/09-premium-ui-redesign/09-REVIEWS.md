---
phase: 9
reviewers: [claude-independent]
reviewed_at: 2026-03-21T12:45:00Z
plans_reviewed: [09-01-PLAN.md, 09-02-PLAN.md]
---

# Cross-AI Plan Review — Phase 9: Premium UI Redesign

> Note: Codex was unavailable (rate-limited until Mar 26), Gemini not installed.
> Review performed by an independent Claude agent session.

---

## Claude Independent Review

### Summary

The phase delivers a coherent, well-executed design system upgrade. The typography pairing (Instrument Serif + Space Grotesk), the warm oklch palette, and the vertical editorial how-it-works layout together push the site meaningfully away from the generic AI-tool template. The implementation is technically clean: next/font/google usage is idiomatic, the FlickeringGrid component shows good engineering discipline with IntersectionObserver and DPR-aware canvas rendering, and every user-facing heading now consistently uses `font-heading`. The phase achieves its stated goal. However, four issues require attention before the site can be considered truly production-ready, and one of them is a visual regression that actively contradicts the premium goal.

---

### Strengths

- Font loading handled correctly via `next/font/google` with `display: "swap"` — no render-blocking requests
- `font-heading` applied consistently to every `h1`/`h2` across all five redesigned components — no drift
- FlickeringGrid is well-engineered: `devicePixelRatio`-aware canvas, `IntersectionObserver` pauses animation off-screen, `ResizeObserver` handles viewport changes, correct cleanup
- Warm oklch palette is internally consistent (all hue angles 50–80), dark mode preserves warmth throughout
- Gold accent (`oklch(0.72 0.12 75)`) applied to all CTAs via a single token — future changes are one-line edits
- `text-accent/40` on how-it-works step numbers is a strong editorial choice — hierarchy without clutter
- Hero's `max-w-2xl` inside `max-w-6xl` creates genuine asymmetry on wide viewports
- All business logic, validation, Turnstile, and state management untouched — disciplined scoping
- Staggered entrance animation (0.1/0.2/0.3s delays, 16px y-offset, 0.4s) within spec

---

### Concerns

**HIGH — `text-accent` on cream background fails WCAG AA for large text**

Gold text (`oklch(0.72 0.12 75)`) against cream background (`oklch(0.98 0.005 80)`) yields ~1.9:1 contrast. WCAG AA requires 3:1 minimum for large text. The `"reimagined"` accent word is the visual anchor of the hero — invisible to users with low-contrast sensitivity or in bright environments.

- File: `web/src/components/landing/hero-section.tsx` line 26
- Fix: Darken gold to `oklch(0.55 0.12 75)` in `globals.css`

**HIGH — `opengraph-image.tsx` is visually inconsistent with new design system**

OG image uses pure black background, Inter font, and indigo/purple gradients — the exact aesthetic Phase 9 was designed to eliminate. Every social share displays this card, directly contradicting the warm gold/amber identity.

- File: `web/src/app/opengraph-image.tsx`
- Fix: Rebuild with warm charcoal background, remove all purple elements, use gold accent

**MEDIUM — `muted-foreground` contrast borderline for body text**

`oklch(0.50 0.01 50)` on cream approximates to ~3.8:1. WCAG AA requires 4.5:1 for normal text at 18px (hero subtitle is `text-lg`). Borderline contrast at minimum size is a liability on mobile/bright light.

- File: `web/src/app/globals.css` line 63
- Fix: Darken to `oklch(0.40 0.01 50)`

**MEDIUM — No `prefers-reduced-motion` support on any animated component**

FlickeringGrid runs `requestAnimationFrame` unconditionally — continuous 60fps canvas repaint on battery-constrained devices. Framer Motion components also animate regardless of OS reduce-motion setting.

- File: `web/src/components/backgrounds/flickering-grid.tsx` lines 136–153
- Fix: Read `window.matchMedia('(prefers-reduced-motion: reduce)')`, draw once and stop if true

**MEDIUM — oklch not supported in Safari < 15.4 (March 2022)**

Devices on iOS 15.3 or earlier receive no color — background transparent, accent invisible, buttons lose background. No fallbacks defined.

- File: `web/src/app/globals.css`
- Fix: Add hex fallback line before each oklch declaration

**LOW — `--font-mono: var(--font-geist-mono)` is an orphaned reference**

Geist Mono is never imported in `layout.tsx`, so `--font-mono` resolves to empty string.

- File: `web/src/app/globals.css` line 11

**LOW — `size="lg"` Button variant conflict with `h-12` className override**

Both `size="lg"` (applies `h-9`) and `className="h-12"` are passed — `size` prop is a no-op, misleading for future developers.

- File: `web/src/components/landing/url-input-form.tsx` lines 102–108

**LOW — FlickeringGrid canvas initializes at 0×0 causing brief layout shift**

`canvasSize` starts at `{ width: 0, height: 0 }` — canvas snaps to full size after `ResizeObserver` fires.

- File: `web/src/components/backgrounds/flickering-grid.tsx` lines 35, 182–192

**LOW — Human visual checkpoint was auto-approved**

Plan 02 Task 5 was `gate="blocking"` / `type="checkpoint:human-verify"` but was auto-approved. The contrast and OG image issues found here are exactly what a human check should catch.

---

### Suggestions

1. **Fix gold text contrast** — Change `--accent` to `oklch(0.55 0.12 75)` in `globals.css`. Test accent-foreground on accent at new lightness.

2. **Rebuild OG image** — Warm charcoal background (`#3a3228`), remove all indigo/purple, gold accent stripe at bottom. Use `"Georgia", serif` fallback stack since `next/og` doesn't support Google Fonts natively.

3. **Add `prefers-reduced-motion` to FlickeringGrid** — Check `window.matchMedia('(prefers-reduced-motion: reduce)').matches`, draw one static frame if true, skip the loop.

4. **Add oklch hex fallbacks** for at minimum `--background`, `--foreground`, `--accent`, `--primary`:
   ```css
   --background: #f9f6f0;
   --background: oklch(0.98 0.005 80);
   ```

5. **Fix orphaned `--font-mono`** — Remove the line or import Geist Mono in `layout.tsx`.

6. **Note deferred components explicitly** — `magnetic-button`, `text-reveal`, `HeroBadge` were evaluated and not used; document this decision in the phase summary.

---

### Risk Assessment

**MEDIUM**

Core redesign goal is met — the site looks significantly more premium. But two HIGH findings prevent LOW: the gold text contrast fails accessibility audits and is perceptible without tools, and the OG image's purple-on-black aesthetic actively undermines the brand positioning this phase was built to establish. Both are straightforward fixes.

---

## Consensus Summary

Only one reviewer was available. Key takeaways for the planner:

### Agreed Strengths
- Typography system (Instrument Serif + Space Grotesk) is well-implemented and consistent
- FlickeringGrid component engineering is solid
- Design scoping discipline — business logic untouched

### Agreed Concerns (Priority Order)
1. **OG image still uses old purple/dark aesthetic** — high visibility, contradicts rebrand
2. **Gold accent text fails WCAG AA contrast** — accessibility risk
3. **No `prefers-reduced-motion` support** — performance + accessibility gap
4. **No oklch fallbacks for Safari < 15.4** — color system breaks on older Safari

### Recommended Follow-up
To address HIGH findings before shipping:
- Fix `--accent` lightness in `globals.css`
- Rebuild `opengraph-image.tsx`
- Add oklch hex fallbacks
- Add `prefers-reduced-motion` guard to FlickeringGrid
