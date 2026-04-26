import { defineConfig, devices } from "@playwright/test";

/**
 * E2E config — tests run against live prod by default.
 * Override via env vars when running locally against a dev stack.
 *
 * Required env (CI provides):
 *   E2E_TEST_SECRET — matches the auth service's E2E_TEST_SECRET so the
 *                     /auth/request side door returns the issued token
 *                     directly instead of sending an email.
 */

export default defineConfig({
  testDir: "./specs",
  fullyParallel: false, // serialise to keep stdb state predictable
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [["github"], ["html", { open: "never" }], ["list"]]
    : [["list"], ["html", { open: "never" }]],

  use: {
    baseURL: process.env.E2E_BASE_LANDING ?? "https://sastaspace.com",
    trace: "on-first-retry",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
  },

  projects: [
    {
      name: "desktop-chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    // Phase 2 F1: matrix for the notes auth rewire. Both legs run the full
    // suite. The legacy spec at specs/auth.spec.ts is unchanged and runs in
    // both legs (FastAPI service stays up through Phase 3); the new spec at
    // specs/notes-auth-stdb.spec.ts test.skip()s itself unless
    // E2E_STDB_AUTH=true.
    //
    // Local invocation:
    //   pnpm exec playwright test --project=notes-legacy
    //   E2E_STDB_AUTH=true pnpm exec playwright test --project=notes-stdb
    //
    // CI: drive via a `matrix.auth-path` axis that sets E2E_STDB_AUTH and
    // NEXT_PUBLIC_USE_STDB_AUTH together. See tests/e2e/README.md for the
    // GH Actions snippet (Phase 3 wires this fully).
    {
      name: "notes-legacy",
      use: { ...devices["Desktop Chrome"] },
      // E2E_STDB_AUTH unset; NEXT_PUBLIC_USE_STDB_AUTH unset in deploy.
    },
    {
      name: "notes-stdb",
      use: { ...devices["Desktop Chrome"] },
      // CI sets E2E_STDB_AUTH=true and deploys notes with
      // NEXT_PUBLIC_USE_STDB_AUTH=true for this project.
    },
  ],

  // Shared timeouts. Keep generous for the moderator pipeline (~3s poll +
  // ~1.5s classify) so comment tests don't flake.
  timeout: 60_000,
  expect: { timeout: 10_000 },
});
