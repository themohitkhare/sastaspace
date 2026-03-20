# Phase 2: Next.js Scaffold + Wiring - Research

**Researched:** 2026-03-21
**Domain:** Next.js 16 App Router scaffolding, UI toolchain, dev workflow, tunnel routing
**Confidence:** HIGH

## Summary

Phase 2 scaffolds a Next.js 16 App Router project inside `web/` of the existing Python/FastAPI monorepo, installs the UI toolchain (shadcn/ui + Tailwind CSS v4 + Motion), wires up a concurrent dev server via Makefile, and configures Cloudflare tunnel ingress rules for path-based routing.

The project already has a working FastAPI server on port 8080 with CORS configured for `http://localhost:3000`. Node.js v24.13.0 and npm 11.6.2 are available. Next.js 16.2.0 is the current stable release (shipped March 18, 2026), using Turbopack by default and requiring Node.js 20.9+. The `create-next-app` CLI scaffolds a project with App Router, TypeScript, Tailwind CSS, and ESLint out of the box.

**Primary recommendation:** Use `npx create-next-app@latest` inside `web/`, run `npx shadcn@latest init` to add shadcn/ui (which auto-configures for Tailwind v4), install `motion` and `tw-animate-css`, then add Makefile targets for concurrent dev startup and a `cloudflared` config for path-based ingress routing.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FRONT-01 | Next.js 16 App Router project scaffolded in `web/` directory | `create-next-app@latest` creates App Router project with TypeScript + Tailwind v4 by default. Place in `web/` subdirectory of repo root. |
| FRONT-02 | shadcn/ui + Tailwind v4 + Motion installed and configured | `npx shadcn@latest init` auto-detects Tailwind v4 and configures CSS-first theming with `@theme inline`. Motion installed as `motion` package. `tw-animate-css` replaces deprecated `tailwindcss-animate`. |
| FRONT-03 | Makefile `dev` target starts both FastAPI and Next.js dev servers together | Bash trap pattern: `(trap 'kill 0' SIGINT; cmd1 & cmd2 & wait)` runs both servers and kills both on Ctrl+C. |
| FRONT-04 | Cloudflare tunnel ingress rules configured: `/api/*` -> FastAPI (8080), `/` -> Next.js (3000) | `config.yml` with path-based ingress rules using regex `^/api/.*` routing to `http://localhost:8080`, catch-all to `http://localhost:3000`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 16.2.0 | React framework with App Router, SSR, Turbopack | Current stable, Turbopack default, Node 20.9+ required |
| react | 19.2.4 | UI library | Required by Next.js 16, includes View Transitions, Activity |
| react-dom | 19.2.4 | React DOM renderer | Required peer of react |
| tailwindcss | 4.2.2 | Utility-first CSS framework | CSS-first config (no tailwind.config.js), `@theme inline` directive |
| typescript | 5.x | Type safety | Required minimum 5.1.0 by Next.js 16 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui | latest (CLI) | Component library (copies components into project) | All UI components -- button, input, card, etc. |
| motion | 12.38.0 | Animation library (formerly framer-motion) | Page transitions, progress animations, micro-interactions |
| tw-animate-css | 1.4.0 | CSS animations for Tailwind | Replaces deprecated `tailwindcss-animate`, used by shadcn/ui |
| cloudflared | latest (brew) | Cloudflare Zero Trust tunnel daemon | Exposes local dev/prod to internet via tunnel |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| motion | CSS animations only | Motion provides declarative React API; CSS is lighter but less capable for orchestrated animations |
| shadcn/ui | Radix UI directly | shadcn/ui wraps Radix with Tailwind styling and copies code into project -- more convenient |
| Makefile concurrency | npm-run-all / concurrently | Extra dependency; Makefile with bash trap is zero-dependency and already in use |

**Installation:**
```bash
# Scaffold Next.js 16 project
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

# Initialize shadcn/ui (auto-detects Tailwind v4)
cd web && npx shadcn@latest init -d

# Install Motion and animation CSS
npm install motion
npm install -D tw-animate-css

# Add a starter shadcn component to verify setup
npx shadcn@latest add button
```

## Architecture Patterns

### Recommended Project Structure
```
sastaspace/                  # Repo root (Python monorepo)
├── sastaspace/              # Python backend package
│   ├── server.py            # FastAPI app (port 8080)
│   ├── config.py            # Settings (pydantic-settings)
│   └── ...
├── web/                     # Next.js 16 frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx   # Root layout
│   │   │   ├── page.tsx     # Landing page (placeholder for Phase 2)
│   │   │   └── globals.css  # Tailwind v4 + shadcn theme vars
│   │   ├── components/
│   │   │   └── ui/          # shadcn/ui components (auto-generated)
│   │   └── lib/
│   │       └── utils.ts     # shadcn cn() utility
│   ├── public/              # Static assets
│   ├── next.config.ts       # Next.js config
│   ├── package.json
│   ├── tsconfig.json
│   └── components.json      # shadcn/ui config
├── cloudflared/
│   └── config.yml           # Tunnel ingress rules
├── Makefile                 # Dev targets (existing + new)
├── pyproject.toml           # Python project config
└── .gitignore               # Updated for web/node_modules, .next
```

### Pattern 1: Tailwind v4 CSS-First Configuration
**What:** Tailwind v4 uses CSS files for all configuration instead of `tailwind.config.js`. Theme values defined with `@theme inline` directive.
**When to use:** Always -- this is the only config approach in Tailwind v4.
**Example:**
```css
/* web/src/app/globals.css */
@import "tailwindcss";
@import "tw-animate-css";

/* shadcn/ui theme variables */
:root {
  --background: hsl(0 0% 100%);
  --foreground: hsl(0 0% 3.9%);
  --primary: hsl(0 0% 9%);
  --primary-foreground: hsl(0 0% 98%);
  /* ... more theme vars */
}

.dark {
  --background: hsl(0 0% 3.9%);
  --foreground: hsl(0 0% 98%);
  /* ... dark mode vars */
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  /* ... map all theme vars */
}
```

### Pattern 2: Concurrent Dev Server Makefile Target
**What:** Single `make dev` command starts both FastAPI (uvicorn) and Next.js dev servers, killing both on Ctrl+C.
**When to use:** Local development workflow.
**Example:**
```makefile
.PHONY: dev dev-api dev-web

dev:
	@echo "Starting FastAPI (8080) and Next.js (3000)..."
	$(MAKE) dev-api & $(MAKE) dev-web & wait

dev-api:
	uv run uvicorn sastaspace.server:app --host 127.0.0.1 --port 8080 --reload

dev-web:
	cd web && npm run dev
```

**Note:** The simpler `make -j 2 dev-api dev-web` approach also works but output interleaving can be messy. The `&` approach with `wait` is cleaner and the trap for SIGINT is handled by make's default behavior of killing child processes.

### Pattern 3: Cloudflare Tunnel Path-Based Ingress
**What:** Single tunnel routes `/api/*` to FastAPI and everything else to Next.js based on path regex.
**When to use:** Production and development tunnel exposure.
**Example:**
```yaml
# cloudflared/config.yml
tunnel: <TUNNEL_UUID>
credentials-file: <HOME>/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: sastaspace.example.com
    path: ^/api/.*
    service: http://localhost:8080
  - hostname: sastaspace.example.com
    service: http://localhost:3000
  - service: http_status:404
```

### Pattern 4: Placeholder Page with shadcn/ui
**What:** Minimal page using shadcn/ui components to verify the UI toolchain works end-to-end.
**When to use:** Phase 2 success criterion -- proves shadcn + Tailwind v4 + Motion are wired correctly.
**Example:**
```tsx
// web/src/app/page.tsx
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-background text-foreground">
      <h1 className="text-4xl font-bold mb-4">SastaSpace</h1>
      <p className="text-muted-foreground mb-8">AI Website Redesigner</p>
      <Button size="lg">Coming Soon</Button>
    </main>
  );
}
```

### Anti-Patterns to Avoid
- **Proxying API through Next.js:** The browser should talk directly to FastAPI at `:8080` (via tunnel `/api/*` routing), NOT through Next.js rewrites. This avoids double-hop latency and SSE buffering issues.
- **Using `tailwind.config.js` with Tailwind v4:** Tailwind v4 is CSS-first. There is no JS config file. All theme configuration goes in `globals.css` via `@theme inline`.
- **Using `EventSource` for SSE:** Cloudflare buffers GET-based SSE. The project uses POST + `fetch()` + `ReadableStream` (requirement PROG-02 in Phase 3). This is a Phase 3 concern but the architecture must support it.
- **Installing `framer-motion`:** The package was renamed to `motion`. Import from `motion/react` not `framer-motion`.
- **Installing `tailwindcss-animate`:** Deprecated in favor of `tw-animate-css` since March 2025.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Component library | Custom React components from scratch | shadcn/ui + Radix UI primitives | Accessibility, keyboard navigation, ARIA attributes all handled |
| Animation system | Custom CSS keyframes + JS orchestration | motion (framer-motion) | Declarative API, layout animations, gesture support, SSR-compatible |
| CSS utility framework | Custom utility classes | Tailwind CSS v4 | Industry standard, tree-shaking, design system via `@theme` |
| Dev server concurrency | Custom shell script | Makefile `&` + `wait` | Already have Makefile; keep tooling minimal |
| Tunnel routing | nginx/caddy reverse proxy | cloudflared ingress rules | Zero config, auto-TLS, integrated with Cloudflare Zero Trust |

**Key insight:** This phase is pure wiring -- no custom business logic. Every piece is a standard tool configured correctly. The risk is misconfiguration, not missing functionality.

## Common Pitfalls

### Pitfall 1: Tailwind v4 Config Confusion
**What goes wrong:** Developer creates `tailwind.config.js` or `tailwind.config.ts` expecting Tailwind v4 to use it. Components don't pick up theme values.
**Why it happens:** Most tutorials and training data reference Tailwind v3 JS-based config.
**How to avoid:** All theme configuration goes in `globals.css` using `@theme inline {}`. No JS config file exists in Tailwind v4.
**Warning signs:** Tailwind classes not applying, theme colors not matching design.

### Pitfall 2: shadcn/ui Animation Import
**What goes wrong:** `tailwindcss-animate` is installed instead of `tw-animate-css`. Animation classes like `animate-in`, `animate-out` don't work.
**Why it happens:** Deprecated package still appears in older docs and tutorials.
**How to avoid:** Use `tw-animate-css` and import it in globals.css as `@import "tw-animate-css";`.
**Warning signs:** Missing animation classes, console warnings about missing CSS.

### Pitfall 3: Port Mismatch Between FastAPI and Tunnel Config
**What goes wrong:** Tunnel config points to port 8000 but FastAPI runs on 8080 (the project default). API requests fail silently.
**Why it happens:** FastAPI tutorials commonly use port 8000; this project's `config.py` defaults to `server_port=8080`.
**How to avoid:** Always reference `config.py` -- the FastAPI server runs on port 8080 by default. Tunnel ingress for `/api/*` must point to `http://localhost:8080`.
**Warning signs:** 502 errors from tunnel, API calls timing out.

### Pitfall 4: Next.js 16 Async APIs
**What goes wrong:** Accessing `params`, `searchParams`, `cookies()`, or `headers()` synchronously causes runtime errors.
**Why it happens:** Next.js 16 removed sync compatibility that existed in 15.
**How to avoid:** Always `await` these APIs: `const { slug } = await params`.
**Warning signs:** TypeScript errors about Promise types, runtime errors about synchronous access.

### Pitfall 5: Motion Import Path
**What goes wrong:** `import { motion } from "framer-motion"` fails because the package is now `motion`.
**Why it happens:** Package was renamed in late 2024.
**How to avoid:** Import from `motion/react`: `import { motion } from "motion/react"`.
**Warning signs:** Module not found errors.

### Pitfall 6: .gitignore Missing Node.js Entries
**What goes wrong:** `node_modules/`, `.next/`, `.next/dev/` committed to git. Massive repo bloat.
**Why it happens:** Existing `.gitignore` only covers Python artifacts.
**How to avoid:** Add `web/node_modules/`, `web/.next/`, and `web/.next/dev/` to root `.gitignore`.
**Warning signs:** Git status showing thousands of new files after `npm install`.

### Pitfall 7: CORS Origin for Production Tunnel
**What goes wrong:** CORS rejects requests from the tunnel hostname because only `http://localhost:3000` is in `cors_origins`.
**Why it happens:** The config.py default only includes localhost.
**How to avoid:** Add the production tunnel hostname to `CORS_ORIGINS` env var (comma-separated). The existing `parse_cors_origins` validator handles this.
**Warning signs:** CORS preflight failures in browser console from production URL.

## Code Examples

### Next.js 16 `next.config.ts` (minimal for this project)
```typescript
// web/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Turbopack is default in Next.js 16 -- no flag needed
  // No custom webpack config needed
};

export default nextConfig;
```

### shadcn/ui `components.json` (auto-generated, expected shape)
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/app/globals.css",
    "baseColor": "zinc",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

### Root Layout with Font and Theme
```tsx
// web/src/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SastaSpace - AI Website Redesigner",
  description: "See your website redesigned by AI in 60 seconds",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

### Cloudflare Tunnel Installation (macOS)
```bash
# Install cloudflared
brew install cloudflared

# Login and create tunnel (one-time setup)
cloudflared tunnel login
cloudflared tunnel create sastaspace

# The tunnel UUID and credentials are created automatically
# Copy the UUID into cloudflared/config.yml
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `tailwind.config.js` | CSS-first `@theme inline` in globals.css | Tailwind v4 (Jan 2025) | No JS config file; all theming in CSS |
| `tailwindcss-animate` | `tw-animate-css` | March 2025 | New import syntax: `@import "tw-animate-css"` |
| `framer-motion` package | `motion` package | Late 2024 | Import from `motion/react` not `framer-motion` |
| `middleware.ts` | `proxy.ts` | Next.js 16 (Oct 2025) | Renamed; edge runtime deprecated for proxy |
| Webpack default bundler | Turbopack default | Next.js 16 (Oct 2025) | No `--turbopack` flag needed; opt-out with `--webpack` |
| `next lint` command | ESLint/Biome directly | Next.js 16 (Oct 2025) | `next lint` removed; run eslint CLI directly |
| Sync `params`/`cookies`/`headers` | Async-only (`await params`) | Next.js 16 (Oct 2025) | Breaking change from Next.js 15 compatibility shim |

**Deprecated/outdated:**
- `tailwindcss-animate`: Use `tw-animate-css` instead
- `framer-motion`: Use `motion` instead (import from `motion/react`)
- `middleware.ts`: Renamed to `proxy.ts` in Next.js 16
- `next lint`: Removed in Next.js 16; use ESLint CLI directly
- `experimental.turbopack`: Now top-level `turbopack` config key

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Manual validation + shell commands (no Jest/Vitest needed for scaffold phase) |
| Config file | N/A -- scaffold verification is process-based, not unit-test-based |
| Quick run command | `cd web && npm run build` |
| Full suite command | `make dev` (verify both servers start) + `curl` checks |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FRONT-01 | Next.js 16 project exists in `web/` with App Router | smoke | `cd web && npx next --version && test -f src/app/page.tsx` | N/A (scaffold) |
| FRONT-02 | shadcn/ui + Tailwind v4 + Motion installed | smoke | `cd web && node -e "require('motion'); require('tw-animate-css')" && test -f components.json && test -f src/components/ui/button.tsx` | N/A (scaffold) |
| FRONT-03 | `make dev` starts both servers | smoke | `make dev & sleep 5 && curl -s http://localhost:3000 > /dev/null && curl -s http://localhost:8080 > /dev/null; kill %1` | N/A (Makefile) |
| FRONT-04 | Cloudflare tunnel config exists with correct ingress | smoke | `test -f cloudflared/config.yml && grep -q "localhost:8080" cloudflared/config.yml && grep -q "localhost:3000" cloudflared/config.yml` | N/A (config) |

### Sampling Rate
- **Per task commit:** `cd web && npm run build` (verifies TypeScript + Tailwind compile)
- **Per wave merge:** `make dev` manual verification (both servers accessible)
- **Phase gate:** All 4 smoke tests pass before `/gsd:verify-work`

### Wave 0 Gaps
None -- this phase is scaffold/config work with no application logic requiring unit tests. Validation is structural (files exist, servers start, config correct).

## Open Questions

1. **Tunnel UUID and hostname**
   - What we know: Cloudflare tunnel requires a UUID and hostname. `cloudflared` is not currently installed.
   - What's unclear: The actual tunnel UUID, credentials path, and production hostname.
   - Recommendation: Create a `cloudflared/config.yml.example` template with placeholder values. Document the one-time setup steps. The actual tunnel creation is a manual step.

2. **CORS origins for production**
   - What we know: `config.py` defaults to `["http://localhost:3000"]`. Production needs the tunnel hostname.
   - What's unclear: The exact production domain.
   - Recommendation: Document that `CORS_ORIGINS` env var should include the production hostname (comma-separated). The existing `parse_cors_origins` validator handles this. No code change needed.

3. **Next.js 16 vs 15 in requirements doc**
   - What we know: REQUIREMENTS.md says "Next.js 16". The additional context says "Next.js 15 (App Router)". Next.js 16.2.0 is current stable.
   - What's unclear: Whether there's a deliberate preference for 15.
   - Recommendation: Use Next.js 16 (latest stable, 16.2.0). It is what `create-next-app@latest` installs. The requirements doc explicitly says "Next.js 16".

## Sources

### Primary (HIGH confidence)
- [Next.js 16 blog post](https://nextjs.org/blog/next-16) - Feature overview, breaking changes, version requirements
- [Next.js 16 upgrade guide](https://nextjs.org/docs/app/guides/upgrading/version-16) - Detailed migration/setup instructions
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) - CSS-first configuration, `@theme inline`, `tw-animate-css`
- [shadcn/ui Next.js installation](https://ui.shadcn.com/docs/installation/next) - `npx shadcn@latest init` steps
- [Cloudflare tunnel config docs](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/configuration-file/) - Ingress rules, path matching, YAML format
- npm registry: `next@16.2.0`, `react@19.2.4`, `tailwindcss@4.2.2`, `motion@12.38.0`, `tw-animate-css@1.4.0` (verified 2026-03-21)

### Secondary (MEDIUM confidence)
- [Motion docs](https://motion.dev/docs/react) - Import from `motion/react`, SSR support
- [Cloudflare blog: Many services, one cloudflared](https://blog.cloudflare.com/many-services-one-cloudflared/) - Path-based ingress pattern

### Tertiary (LOW confidence)
- None -- all critical claims verified against primary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All versions verified against npm registry; Next.js 16 docs read in full
- Architecture: HIGH - Project structure follows `create-next-app` defaults + existing repo layout
- Pitfalls: HIGH - Based on official breaking changes docs and verified package renames
- Tunnel config: MEDIUM - Config format verified against Cloudflare docs; actual tunnel UUID/hostname are placeholders

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable ecosystem, 30-day validity)
