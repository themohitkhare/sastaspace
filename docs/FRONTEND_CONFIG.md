# Frontend config and Bun

## Why we still have config files

Bun replaces the **runtime and package manager** (Node + npm). We use it for `bun install`, `bun run`, `bun dev`, `bun run build`. Bun does **not** replace Vite, Tailwind, or Playwright.

We still rely on:

- **Vite** – dev server + bundler (React, HMR, `@shared` alias, build)
- **Tailwind** – CSS (design tokens: fonts, colors, shadows)
- **PostCSS** – Tailwind + Autoprefixer pipeline
- **Vitest** (sastadice) – unit tests
- **Playwright** (sastadice) – E2E tests

Each of these tools expects its own config. So we keep:

| Config | Purpose | Bun equivalent? |
|--------|---------|------------------|
| `vite.config.js` | Vite dev/build, React plugin, aliases, **Vitest** (sastadice) | No – we use Vite, not Bun’s bundler |
| `tailwind.config.js` | Theme (fonts, colors, shadows) | No |
| `postcss.config.js` | Tailwind + Autoprefixer | No |
| `playwright.config.ts` (sastadice) | E2E dir, base URL, Chromium, webServer | No |

## What we could trim

1. **Use `bun test` instead of Vitest**  
   Bun has a built-in, Jest-compatible test runner. We could:
   - Drop the `test` block from `vite.config.js` (~25 lines)
   - Remove Vitest (and `@vitest/coverage-v8`) from `package.json`
   - Migrate tests from `vi.mock` / `vi.fn` / `vi.useFakeTimers` to Bun’s `mock` and `bun:test` APIs  
   That’s a non-trivial migration (many mocks, fake timers), but it would reduce config and deps.

2. **Use Bun’s bundler instead of Vite**  
   Bun can bundle. Switching would mean:
   - No `vite.config.js`
   - Replacing Vite’s React plugin, HMR, and alias setup with Bun’s build config  
   For a React + Tailwind + `@shared` monorepo, that’s a large change. Vite stays for now.

3. **Tailwind v4**  
   Newer Tailwind can reduce config (e.g. `@import "tailwindcss"`). We’re on v3; upgrading is a separate migration.

## Already removed

- **`.nvmrc`** – we use Bun, not Node version managers.
- **`package-lock.json`** – replaced by `bun.lock`.

## Summary

We have several config files because we use several tools (Vite, Tailwind, PostCSS, Vitest, Playwright). Bun replaces Node/npm only. The main way to cut config further is to adopt Bun’s test runner (and optionally its bundler) and migrate away from Vitest (and Vite) where it makes sense.
