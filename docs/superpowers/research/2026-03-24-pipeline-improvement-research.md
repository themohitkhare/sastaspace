# Pipeline & Design Quality Research — March 2026

## Top 10 Actionable Improvements (Priority Order)

### 1. Embed Design System in Builder Prompt
Define CSS variables (OKLCH colors, 8px spacing grid, fluid clamp() typography, border-radius tokens) upfront in every Builder call. Every generated site uses these tokens for internal consistency.

### 2. Per-Step Model Routing
- Gemini Flash for Planner (fast, cheap JSON output)
- Claude for Builder/Composer (highest quality HTML/React)
- Already supported by `_create_model` — just needs step-level routing

### 3. No Blue/Indigo Rule (from v0 leaked prompt)
v0 explicitly avoids default blue/indigo because they scream "AI-generated." Select palette based on crawled site's brand colors or industry.

### 4. Magic UI Integration (MIT, AI-safe)
150+ animated components. Best fit for our pipeline. Other premium libraries (Shadcnblocks, Shadcn Studio) explicitly BAN AI site builders.

### 5. Post-Generation Quality Gate
axe-core accessibility check + multi-viewport screenshot (375/768/1440px) + 8-point Premium Test checklist. Auto-fix critical violations via LLM feedback loop.

### 6. Template Caching by site_type
Cache Planner outputs for common types (restaurant, portfolio, SaaS). Skip Planner for cache hits — saves 30-50% pipeline time.

### 7. Parallel Section Generation
Split Builder into concurrent section-level LLM calls (above-fold, content, footer). ~35% speedup via asyncio.gather.

### 8. Premium Font Pairings
Encode 4-5 Google Fonts pairings in prompts:
- Inter + Instrument Serif (SaaS)
- Geist Sans + Geist Mono (developer)
- Plus Jakarta Sans + Source Serif 4 (professional)
- DM Sans + DM Serif Display (elegant)

### 9. Unsplash Image Integration
Use direct URLs: `https://images.unsplash.com/photo-{id}?w=800&auto=format` selected by industry/content type.

### 10. Require Micro-Interactions
Mandate: CSS hover transitions, scroll-reveal (IntersectionObserver), gradient text on hero, bento grid layouts for features.

## Component Library Licensing

### SAFE (MIT/open-source):
- shadcn/ui core, Magic UI, Animata, Cult UI, Launch UI, Tailark Blocks

### BANNED for AI site builders:
- Shadcnblocks ($8K penalty), Shadcn Studio (explicit ban), Aceternity Pro (resale ban)

## Competitor Architecture

### v0.dev
Multi-model routing (Claude 26%, Grok 16%, Gemini 11%), shadcn/ui trained, sandbox-based

### Lovable
Opinionated React+shadcn+Supabase, three modes (Agent/Chat/Visual Edit)

### Bolt.new
WebContainers (in-browser Node.js), diff-based updates, multi-framework

### Common Pattern: All use shadcn/ui + multi-model backends + real-time preview
