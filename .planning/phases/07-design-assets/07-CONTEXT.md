# Phase 7: Design Assets - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Create professional branding assets for SastaSpace: custom favicon, app icons for mobile home screen, and OG image template for social sharing. Use Google Stitch MCP to generate design assets.

</domain>

<decisions>
## Implementation Decisions

### Favicon
- Custom SastaSpace favicon replacing the default Next.js icon
- Include multiple sizes: favicon.ico (16x16, 32x32), apple-touch-icon (180x180), android icons (192x192, 512x512)
- Design should reflect the AI/redesign concept — modern, clean, tech-forward

### OG Image Template
- 1200x630px OG image for social sharing
- Include SastaSpace branding and tagline
- Used as default OG image for landing page and fallback for result pages

### App Icons
- Apple touch icon for iOS Safari home screen
- Android Chrome icons (192x192, 512x512) for PWA manifest
- Consistent design language with favicon

### Asset Generation
- Use Stitch MCP (`mcp__stitch__generate_screen_from_text`) to create design concepts
- Export and optimize assets for web (SVG for favicon where possible, PNG for raster)

### Claude's Discretion
- Exact visual design of favicon and icons
- Color palette (should align with existing shadcn theme)
- Typography choices for OG image

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `web/src/app/favicon.ico` — current default favicon to replace
- `web/src/app/layout.tsx` — root layout where icons are configured
- `web/src/app/globals.css` — existing color variables (oklch color space)

### Established Patterns
- Next.js App Router icon convention: place in `app/` directory
- shadcn v4 base-nova style with oklch colors
- Dark theme with accent colors

### Integration Points
- `web/src/app/` — favicon.ico, apple-icon.png, icon.png
- `web/src/app/layout.tsx` — metadata icons configuration
- `web/public/` — static assets (OG images, manifest icons)
- `web/src/app/manifest.ts` or `web/public/manifest.json` — PWA manifest

</code_context>

<specifics>
## Specific Ideas

- Use Stitch MCP to generate screen designs for the assets
- Design should be modern, tech-forward, reflecting AI-powered redesign
- Consistent with existing dark theme and shadcn styling

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
