# Phase 9: Premium UI Redesign - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete visual overhaul of the SastaSpace landing page, result page, and overall design system to eliminate AI-generated aesthetic. Apply research-backed premium design principles using components from @components/ library.

</domain>

<decisions>
## Implementation Decisions

### Typography — Kill Inter
- Replace Inter with a distinctive font pairing: serif display for headlines + clean sans for body
- Use Google Fonts: Instrument Serif for headlines (editorial feel), Space Grotesk for body (modern but not generic)
- Headline sizes: clamp() for fluid scaling, tighter line-height (1.1) for large text
- Body text at 18px minimum

### Color — No Purple Gradients
- Kill the achromatic palette. Add a single confident brand accent
- Accent color: warm gold/amber (#C5A253 or similar) — distinctive, not the AI teal/purple
- Background: warm off-white (not pure white), deep warm charcoal (not pure black) for dark sections
- Keep the design mostly neutral with the accent used sparingly for CTAs and highlights

### Layout — Break the Grid
- Hero: asymmetric layout, NOT centered text + input below
- How-it-works: NOT a three-column icon grid — use a vertical timeline or editorial layout
- Result page: more breathing room, visual hierarchy through scale contrast
- Vary section heights — not every section gets the same padding

### Backgrounds — Premium Not Generic
- Replace Spotlight with something more distinctive from @components/ library
- Options: animated-grid-pattern, background-paths, flickering-grid, or shape-landing-hero
- Keep it subtle — the background should add depth, not compete with content

### Animation — Purposeful
- Entrance: fade-up 8-16px with 200-400ms, staggered children by 50-100ms
- Hover: scale(1.02) + shadow elevation, not dramatic transforms
- One focal animation moment, not effects on everything

### Components to Use from @components/
- Hero section: Codehagen/hero with HeroBadge for announcement pill
- Background: animated-grid-pattern or flickering-grid (subtle, technical feel)
- CTA: magnetic-button for premium hover interaction
- Text effects: text-reveal or typing-effect for headline
- How-it-works: replace with editorial vertical layout, not three-column grid

### What NOT To Do
- No purple gradients anywhere
- No three equal columns with icons
- No Inter/Roboto/system fonts
- No generic stock imagery
- No blur/glass effects for "premium" feel
- No animation on every element
- No "Learn More" CTAs

</decisions>

<code_context>
## Existing Code Insights

### Files to Modify
- web/src/app/globals.css — color palette overhaul
- web/src/app/layout.tsx — font imports
- web/src/components/landing/hero-section.tsx — complete rewrite
- web/src/components/landing/url-input-form.tsx — styling updates
- web/src/components/landing/how-it-works.tsx — complete rewrite (break three-column pattern)
- web/src/components/backgrounds/spotlight.tsx — replace with premium background
- web/src/components/result/result-view.tsx — spacing and typography
- web/src/components/result/contact-form.tsx — styling consistency
- web/src/components/progress/progress-view.tsx — typography updates

### Component Library Available
- /components/marketing-blocks/ — heroes, backgrounds, CTAs, testimonials, features
- /components/ui-components/ — buttons, inputs, cards, etc.
- Components are JSON files with full source code in `files[].content`

### Established Patterns
- Next.js App Router with "use client" components
- Motion (framer-motion) for animations
- shadcn/ui base components
- oklch color space for CSS variables

</code_context>

<specifics>
## Specific Ideas

- The site IS the portfolio piece — it must look like a $5,000 custom build
- User explicitly said "no slop" — every detail must feel intentional
- Reference: Linear.app, Stripe.com, Vercel.com aesthetic quality level
- Use Instrument Serif for that editorial headline feel (like Stripe's marketing pages)

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
