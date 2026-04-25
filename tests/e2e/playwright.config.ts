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
  ],

  // Shared timeouts. Keep generous for the moderator pipeline (~3s poll +
  // ~1.5s classify) so comment tests don't flake.
  timeout: 60_000,
  expect: { timeout: 10_000 },
});
