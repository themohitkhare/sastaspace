---
phase: 09-premium-ui-redesign
plan: 01
subsystem: ui
tags: [typography, color-palette, oklch, google-fonts, instrument-serif, space-grotesk, canvas, flickering-grid]

requires:
  - phase: 03-core-ui-landing-progress-result
    provides: "Base layout.tsx and globals.css with Inter font and achromatic palette"
provides:
  - "Instrument Serif + Space Grotesk font loading via next/font/google"
  - "Warm oklch color palette with gold accent oklch(0.72 0.12 75)"
  - "FlickeringGrid canvas-based background component"
  - "font-heading Tailwind utility for serif headlines"
affects: [09-premium-ui-redesign plan 02, all components using color variables]

tech-stack:
  added: [Instrument Serif (Google Font), Space Grotesk (Google Font)]
  patterns: [warm oklch colors with nonzero chroma, font-heading for editorial headlines, font-sans for body]

key-files:
  created:
    - web/src/components/backgrounds/flickering-grid.tsx
  modified:
    - web/src/app/layout.tsx
    - web/src/app/globals.css

key-decisions:
  - "Instrument Serif weight 400 with normal+italic styles (not variable font)"
  - "Space Grotesk as variable font for flexible body text weights"
  - "Gold accent oklch(0.72 0.12 75) used for accent, ring, chart-1, and sidebar highlights"
  - "Warm hue angles 50-80 range throughout palette for cohesive warmth"

patterns-established:
  - "font-heading: CSS variable --font-heading maps to Instrument Serif for editorial headlines"
  - "font-sans: CSS variable --font-sans maps to Space Grotesk for body text"
  - "All oklch values use nonzero chroma with warm hue angles (50-80)"
  - "FlickeringGrid: canvas-based background with IntersectionObserver for perf"

requirements-completed: []

duration: 3min
completed: 2026-03-21
---

# Phase 09 Plan 01: Design Foundation Summary

**Instrument Serif + Space Grotesk fonts, warm gold/amber oklch palette, and FlickeringGrid canvas background replacing generic Inter + achromatic design**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-21T12:18:13Z
- **Completed:** 2026-03-21T12:21:22Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Replaced Inter with Instrument Serif (headlines) + Space Grotesk (body) via next/font/google CSS variables
- Overhauled entire oklch color palette from achromatic (zero chroma) to warm values with gold accent at oklch(0.72 0.12 75)
- Created FlickeringGrid canvas background component with warm default color and IntersectionObserver performance optimization

## Task Commits

Each task was committed atomically:

1. **Task 1: Install fonts and update layout.tsx** - `9a50dfb` (feat)
2. **Task 2: Overhaul globals.css with warm color palette** - `fa19458` (feat)
3. **Task 3: Add FlickeringGrid background component** - `ce367ea` (feat)

## Files Created/Modified
- `web/src/app/layout.tsx` - Font imports for Instrument Serif and Space Grotesk with CSS variables
- `web/src/app/globals.css` - Complete warm oklch palette with gold accent, dark mode with warm charcoal
- `web/src/components/backgrounds/flickering-grid.tsx` - Canvas-based flickering grid with warm defaults

## Decisions Made
- Used Instrument Serif weight 400 with both normal and italic styles (it's not a variable font, requires explicit weight)
- Space Grotesk loaded as variable font for flexible weight range
- Gold accent color applied consistently to accent, ring, chart-1, and sidebar-ring/sidebar-primary variables
- Removed purple hue (264.376) from dark mode sidebar-primary, replaced with gold
- Chart colors updated to warm amber/brown gradient instead of achromatic grays

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all components are fully functional.

## Next Phase Readiness
- Font variables (--font-heading, --font-sans) ready for component styling in Plan 02
- FlickeringGrid component ready to replace Spotlight in hero section
- Color palette active site-wide via CSS custom properties
- All builds pass cleanly with zero type errors

## Self-Check: PASSED

All 3 files verified present. All 3 commit hashes verified in git log.

---
*Phase: 09-premium-ui-redesign*
*Completed: 2026-03-21*
