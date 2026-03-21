---
phase: 06-seo-feature-flags
plan: 01
subsystem: ui
tags: [seo, opengraph, twitter-cards, robots, sitemap, feature-flags, turnstile]

requires:
  - phase: 03-core-ui-landing-progress-result
    provides: "Layout and result page structure"
  - phase: 04-contact-form-polish
    provides: "Contact form with Turnstile integration"
provides:
  - "OG meta tags for social sharing on landing and result pages"
  - "robots.txt and sitemap.xml for search engine crawling"
  - "NEXT_PUBLIC_ENABLE_TURNSTILE feature flag for toggling spam protection"
affects: [07-design-assets, 08-e2e-tests]

tech-stack:
  added: []
  patterns: ["Next.js MetadataRoute for robots/sitemap", "NEXT_PUBLIC_ env var feature flags"]

key-files:
  created:
    - web/src/app/robots.ts
    - web/src/app/sitemap.ts
  modified:
    - web/src/app/layout.tsx
    - web/src/app/[subdomain]/page.tsx
    - web/src/components/result/contact-form.tsx
    - web/src/app/api/contact/route.ts

key-decisions:
  - "Used MetadataRoute types for robots.ts and sitemap.ts per Next.js conventions"
  - "OG image points to /og-image.png placeholder path (Phase 7 creates the asset)"
  - "Feature flag uses !== 'false' check so default (unset) keeps Turnstile enabled"

patterns-established:
  - "Feature flags: use NEXT_PUBLIC_ env vars with !== 'false' pattern for opt-out defaults"
  - "SEO metadata: use static metadata export for layout, generateMetadata for dynamic pages"

requirements-completed: [SEO-01, SEO-02, SEO-04, FLAG-01, FLAG-02]

duration: 2min
completed: 2026-03-21
---

# Phase 6 Plan 01: SEO + Feature Flags Summary

**OG meta tags for social sharing, robots/sitemap for crawlers, and NEXT_PUBLIC_ENABLE_TURNSTILE feature flag for toggling Turnstile spam protection**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-21T10:40:04Z
- **Completed:** 2026-03-21T10:42:05Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Landing page exports rich OG/Twitter metadata for social media sharing previews
- Result pages generate dynamic OG tags with the subdomain domain name
- robots.ts and sitemap.ts created using Next.js MetadataRoute conventions
- Turnstile widget conditionally rendered and verified based on NEXT_PUBLIC_ENABLE_TURNSTILE env var

## Task Commits

Each task was committed atomically:

1. **Task 1: SEO metadata, robots.txt, and sitemap.xml** - `49f2c2f` (feat)
2. **Task 2: Turnstile feature flag** - `a6b57a0` (feat)

## Files Created/Modified
- `web/src/app/layout.tsx` - Root metadata with metadataBase, openGraph, and twitter fields
- `web/src/app/[subdomain]/page.tsx` - Dynamic OG metadata with domain name in title/description
- `web/src/app/robots.ts` - robots.txt route handler allowing all crawlers
- `web/src/app/sitemap.ts` - sitemap.xml route handler with landing page entry
- `web/src/components/result/contact-form.tsx` - Conditional Turnstile rendering via feature flag
- `web/src/app/api/contact/route.ts` - Conditional Turnstile verification via feature flag

## Decisions Made
- Used MetadataRoute types for robots.ts and sitemap.ts per Next.js file convention docs
- OG image points to /og-image.png placeholder path (Phase 7 will create the actual asset)
- Feature flag uses `!== "false"` check so default (unset) keeps Turnstile enabled

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- OG image placeholder path (/og-image.png) ready for Phase 7 to create actual asset
- Feature flag pattern established for any future toggleable features
- SEO foundation complete for E2E testing in Phase 8

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 06-seo-feature-flags*
*Completed: 2026-03-21*
