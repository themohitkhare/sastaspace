import { defineConfig } from "vitest/config";

// Workers are mostly glue code wrapping the SpacetimeDB client SDK against
// the moderator/auth-mailer/admin-collector/deck-agent loops. The existing
// tests cover the testable seams (env validation, message handling, retry
// branches) — the rest is SDK plumbing best exercised by the smoke tests
// and live worker boot. Thresholds are deliberately modest to start so
// they act as a regression floor rather than blocking honest refactors.
export default defineConfig({
  test: {
    include: ["src/**/*.{test,spec}.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "json-summary"],
      include: ["src/**/*.ts"],
      exclude: [
        "src/**/*.test.ts",
        "src/**/*.spec.ts",
        // Boot/index file — pure orchestration; tested via live worker boot.
        "src/index.ts",
        // Shared SDK glue: stdb client wrapper, mastra+ollama provider
        // factory, env validator. Each is exercised indirectly by every
        // agent test through dependency injection but contains little
        // standalone logic worth gating per-line.
        "src/shared/stdb.ts",
        "src/shared/mastra.ts",
        "src/shared/env.ts",
      ],
      thresholds: {
        lines: 50,
        functions: 55,
        statements: 50,
        branches: 45,
      },
    },
  },
});
