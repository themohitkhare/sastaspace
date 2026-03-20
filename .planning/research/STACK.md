# Stack Research

**Domain:** Public-facing SaaS frontend (Next.js) + Python FastAPI backend
**Researched:** 2026-03-21
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Next.js | 16.x (latest stable) | Frontend framework | Current stable release (Oct 2025). App Router is mature, Turbopack is default bundler (2-5x faster builds), React Compiler stable. SSR for SEO on a public landing page. Next.js 15 is also acceptable but 16 is the active release line. |
| React | 19.x | UI library | Ships with Next.js 16. Server Components, Actions, and the React Compiler are all stable. |
| TypeScript | 5.x | Type safety | Non-negotiable for any Next.js project. Next.js scaffolds it by default. |
| Tailwind CSS | 4.x | Styling | Ships with Next.js 16 scaffolding. No config file needed (uses `@theme inline` directive). The standard for utility-first CSS in 2025+. |
| Python | 3.14 | Backend runtime | Already in use. No change needed. |
| FastAPI | 0.135+ | Backend API framework | Already in use. Excellent SSE support via `sse-starlette`. Extend with `/redesign` endpoint. |
| Uvicorn | 0.42+ | ASGI server | Already in use. No change needed. |

### Frontend Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui | latest | UI component primitives | Every interactive element: buttons, inputs, dialogs, cards, toasts. Not an npm dependency -- copies component source into your project. Built on Radix UI primitives. Tailwind v4 compatible. |
| Motion (formerly Framer Motion) | 12.x | Animation | Landing page scroll reveals, page transitions, progress indicator animations. The standard React animation library. |
| Lucide React | latest | Icons | Icon set used by shadcn/ui. Consistent with the component library. |
| Zod | 3.x | Schema validation | Contact form validation (client + server). Works natively with React 19 form actions. |
| Resend | 4.x (SDK) | Email delivery | Contact form submissions. Free tier: 3,000 emails/month, 1 domain. More than sufficient for lead gen. |
| React Email | latest | Email templates | Build the contact notification email as a React component. Pairs with Resend. |

### Backend Libraries (additions to existing stack)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sse-starlette | 3.3+ | Server-Sent Events | The `/redesign` streaming endpoint. Production-ready SSE for FastAPI with auto-disconnect detection and graceful shutdown. FastAPI's official SSE docs reference this library. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Turbopack | Bundler (dev + build) | Default in Next.js 16. No configuration needed. |
| ESLint + `eslint-config-next` | Linting | Ships with `create-next-app`. |
| Prettier | Formatting | Standard for JS/TS projects. Use `prettier-plugin-tailwindcss` for class sorting. |
| concurrently | Process management | Run Next.js dev server + FastAPI dev server in one terminal during development. |

## Long-Running API Calls: SSE Architecture

This is the critical architectural decision. The redesign pipeline takes 30-60 seconds. Here is the recommended approach:

**Use Server-Sent Events (SSE) from FastAPI directly to the browser.**

### Why SSE (not WebSockets, not polling)

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **SSE** | **USE THIS** | Unidirectional (server-to-client) is exactly what we need. Works over standard HTTP. Auto-reconnect built into `EventSource` API. FastAPI has excellent support via `sse-starlette`. No proxy/firewall issues. |
| WebSockets | Overkill | Bidirectional communication not needed. More complex server and client code. Harder to debug. No advantage for a one-way progress stream. |
| Polling | Worse UX | Requires job queue + storage for job state. Adds infrastructure complexity (Redis/DB for job tracking). Delayed feedback. Only use this if deploying behind a proxy that kills long connections. |

### SSE Data Flow

```
Browser (EventSource) ---> FastAPI /api/redesign?url=example.com
                     <--- SSE: {event: "status", data: "Crawling website..."}
                     <--- SSE: {event: "status", data: "Extracting content..."}
                     <--- SSE: {event: "status", data: "Generating redesign..."}
                     <--- SSE: {event: "complete", data: {html_url: "/sites/example/index.html"}}
```

### Why NOT proxy SSE through Next.js API routes

Next.js Route Handlers buffer the response until the handler function completes. This means SSE streams get held up unless you use specific workarounds. Since we're self-hosting (not Vercel), the simplest and most reliable approach is:

- **Browser connects directly to FastAPI** for SSE streams
- **Next.js handles** page rendering, static content, and the contact form server action
- Both services run on different ports behind the Cloudflare tunnel

This avoids the Next.js SSE buffering problem entirely.

## Contact Form: Resend via Next.js Server Action

**Use a Next.js Server Action (not an API route) that calls Resend.**

```
User fills form --> Server Action (server-side) --> Resend API --> Email to owner
```

- Server Actions are the idiomatic Next.js 16 way to handle form submissions
- Zod validates on both client and server
- Resend free tier (3,000 emails/month) is more than enough for a lead gen site
- No need for SendGrid, Nodemailer, or SMTP configuration
- React Email lets you build the notification email as a React component

## Project Structure

**Colocate the Next.js frontend alongside the existing Python project.** Do NOT use a monorepo tool (Turborepo, Nx) -- the two projects have completely different package managers (uv vs npm) and build systems.

```
sastaspace/
  sastaspace/          # Existing Python package
  tests/               # Existing Python tests
  sites/               # Existing generated HTML output
  web/                 # NEW: Next.js frontend
    src/
      app/             # App Router pages
        page.tsx       # Landing page
        result/[id]/
          page.tsx     # Redesign result page
      components/      # React components
        ui/            # shadcn/ui components
      lib/             # Utilities, API client
      styles/          # Global CSS
    public/            # Static assets
    package.json
    tsconfig.json
    next.config.ts
  pyproject.toml       # Existing Python config
  Makefile             # Extend with frontend commands
  .env                 # Shared env vars
```

### Why this structure

- `web/` is a self-contained Next.js app with its own `package.json`
- No monorepo tooling overhead for two projects with different ecosystems
- Makefile already exists -- extend it with `make dev-web`, `make build-web`
- `.env` at the root can be shared (Next.js supports `NEXT_PUBLIC_` prefix for client vars)

## App Router vs Pages Router

**Use App Router. Not debatable in 2025+.**

The Pages Router is legacy. Next.js 16 has made App Router the only actively developed routing system. Server Components, Server Actions, streaming, and the React Compiler all require App Router. Every new feature targets App Router exclusively.

## Installation

```bash
# Create Next.js app in web/ directory
cd /path/to/sastaspace
npx create-next-app@latest web --ts --tailwind --eslint --app --src-dir

# Frontend dependencies
cd web
npx shadcn@latest init
npm install motion lucide-react zod resend @react-email/components

# Dev dependencies
npm install -D prettier prettier-plugin-tailwindcss concurrently

# Backend addition (from project root)
uv add sse-starlette
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| shadcn/ui | Mantine | If you want an opinionated, batteries-included component library with built-in hooks. Heavier, less customizable. |
| shadcn/ui | Hero UI (NextUI) | If you want zero-config pretty components. Less design control, more opinionated aesthetic. |
| Resend | SendGrid | If you need >3,000 emails/month or advanced analytics. More complex setup. |
| Resend | Web3Forms | If you want zero backend -- client-side form submission to a third-party endpoint. Less control over email content. |
| SSE | Polling + Redis | If deploying behind a load balancer that kills long HTTP connections. Not needed for Cloudflare tunnel. |
| Motion (Framer Motion) | GSAP | If you need timeline-based, frame-perfect animation sequences. Heavier, commercial license for some features. Motion is simpler and sufficient for landing page animations. |
| Colocated `web/` dir | Turborepo monorepo | If you had 3+ packages sharing code. Overkill for one Python backend + one Next.js frontend with no shared code. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Pages Router | Legacy, no new features, missing Server Components/Actions | App Router |
| `getServerSideProps` / `getStaticProps` | Pages Router patterns, deprecated in App Router | Server Components + `fetch` / Server Actions |
| Next.js API Routes for SSE proxy | Buffering issues, adds unnecessary middleware layer | Direct browser-to-FastAPI SSE connection |
| Chakra UI | v3 migration was painful, smaller ecosystem than shadcn/ui in 2025, runtime CSS-in-JS | shadcn/ui + Tailwind |
| Material UI (MUI) | Heavy bundle, opinionated Material Design aesthetic doesn't suit a "high-design portfolio" site | shadcn/ui + Tailwind |
| Nodemailer / raw SMTP | Complex setup, requires SMTP server configuration, error-prone deliverability | Resend (managed email API) |
| Socket.IO / WebSockets | Bidirectional overkill for server-to-client progress updates | SSE via `sse-starlette` |
| `tailwind.config.js` | Tailwind v4 uses CSS-based configuration (`@theme inline`), config file is legacy | `@theme inline` in `globals.css` |
| Redux / Zustand | No complex client state to manage. Form state is local, SSE state is ephemeral. | React 19 `useState` + `useActionState` |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Next.js 16.x | React 19.x | Bundled together. Do not install React separately. |
| Next.js 16.x | Tailwind CSS 4.x | Scaffolded by `create-next-app`. No manual config needed. |
| shadcn/ui (latest) | Tailwind CSS 4.x | Explicitly supports v4 as of early 2025. Uses `@theme inline`. |
| shadcn/ui (latest) | React 19.x | All components updated for React 19. |
| Motion 12.x | React 19.x | Compatible. Renamed from `framer-motion` to `motion`. |
| sse-starlette 3.3+ | FastAPI 0.135+ | Built for Starlette/FastAPI. No compatibility issues. |
| Resend SDK 4.x | Next.js 16.x | Works with Server Actions and API routes. |

## Sources

- [Next.js 16 release blog](https://nextjs.org/blog/next-16) -- Turbopack default, React Compiler stable, cache components
- [Next.js 16 upgrade guide](https://nextjs.org/docs/app/guides/upgrading/version-16) -- migration path from 15
- [FastAPI SSE tutorial](https://fastapi.tiangolo.com/tutorial/server-sent-events/) -- official SSE documentation
- [sse-starlette on PyPI](https://pypi.org/project/sse-starlette/) -- version 3.3.3, production-ready SSE for FastAPI
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) -- v4 setup instructions
- [shadcn/ui Next.js installation](https://ui.shadcn.com/docs/installation/next) -- official Next.js setup
- [Resend pricing](https://resend.com/pricing) -- free tier: 3,000 emails/month
- [Resend Next.js integration](https://resend.com/docs/send-with-nextjs) -- Server Actions support
- [Motion (Framer Motion) homepage](https://motion.dev/) -- renamed library, React animation standard
- [Next.js SSE discussion](https://github.com/vercel/next.js/discussions/48427) -- known buffering issues with Route Handlers
- [Vinta Software: FastAPI + Next.js monorepo](https://www.vintasoftware.com/blog/nextjs-fastapi-monorepo) -- project structure patterns

---
*Stack research for: SastaSpace web frontend*
*Researched: 2026-03-21*
