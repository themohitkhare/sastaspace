# Phase 6: SEO + Feature Flags - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Add SEO meta tags (title, description, OG tags) to landing and result pages, generate robots.txt and sitemap.xml, and implement a Turnstile feature flag (`NEXT_PUBLIC_ENABLE_TURNSTILE`) that controls whether the Turnstile widget renders on the contact form.

</domain>

<decisions>
## Implementation Decisions

### SEO Strategy
- Landing page: static OG meta tags with SastaSpace branding
- Result pages `/[subdomain]/`: dynamic OG tags with subdomain name in title/description
- robots.txt: allow all crawlers, link to sitemap
- sitemap.xml: static sitemap with landing page (result pages are dynamic, not in sitemap)

### Feature Flags
- `NEXT_PUBLIC_ENABLE_TURNSTILE` env var (string "true"/"false", default "true")
- When disabled: Turnstile component does not render, form submits without token
- API route `/api/contact` skips Turnstile verification when no token provided and flag is off
- Feature flag check is client-side (NEXT_PUBLIC_ prefix makes it available in browser)

### Claude's Discretion
- OG image placeholder path (can use a static image or generate dynamically)
- Sitemap format (static XML file vs generated route)
- Meta tag content wording

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `web/src/app/[subdomain]/page.tsx` — already has `generateMetadata` function
- `web/src/app/layout.tsx` — root layout with existing metadata
- `web/src/components/result/contact-form.tsx` — Turnstile integration to modify
- `web/src/app/api/contact/route.ts` — Turnstile verification to conditionally skip

### Established Patterns
- Next.js App Router metadata via `export const metadata` or `generateMetadata`
- Turnstile imported from `@marsidev/react-turnstile`
- Environment variables: `NEXT_PUBLIC_*` for client-side, plain for server-side

### Integration Points
- `layout.tsx` — add default metadata
- `[subdomain]/page.tsx` — enhance `generateMetadata` with OG tags
- `contact-form.tsx` — conditionally render Turnstile based on env var
- `api/contact/route.ts` — conditionally verify Turnstile token

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard SEO and feature flag implementation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
