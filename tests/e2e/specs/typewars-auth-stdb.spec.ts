/**
 * Phase 2 F2 — STDB-native /auth/verify page coverage.
 *
 * This spec is intentionally scoped to the new verify page only. The broader
 * legacy + matrix coverage lives in the user's untracked typewars-auth.spec.ts
 * which exercises NEXT_PUBLIC_USE_STDB_AUTH=false (legacy FastAPI path).
 *
 * These scenarios assume the typewars build has NEXT_PUBLIC_USE_STDB_AUTH=true
 * baked in (Next.js bakes NEXT_PUBLIC_* at build time). They `test.skip` if
 * the env var is not set so the suite stays green on the legacy build.
 */
import { expect, test } from "@playwright/test";
import { TYPEWARS } from "../helpers/urls.js";

const STDB_AUTH_ENABLED =
  process.env.E2E_TYPEWARS_USE_STDB_AUTH === "true" ||
  process.env.NEXT_PUBLIC_USE_STDB_AUTH === "true";

test.describe("typewars · STDB-native /auth/verify", () => {
  test("missing token shows friendly error and a back-to-map button", async ({
    page,
  }) => {
    await page.goto(`${TYPEWARS}/auth/verify?app=typewars`);
    await expect(page.getByText(/missing required fields/i)).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      page.getByRole("button", { name: /back to map/i }),
    ).toBeVisible();
  });

  test("missing app parameter shows friendly error", async ({ page }) => {
    await page.goto(`${TYPEWARS}/auth/verify?t=anything`);
    await expect(page.getByText(/missing required fields/i)).toBeVisible({
      timeout: 10_000,
    });
  });

  test("bad token: sign-in fails with surfaced error message", async ({
    page,
  }) => {
    test.skip(
      !STDB_AUTH_ENABLED,
      "Requires the typewars app built with NEXT_PUBLIC_USE_STDB_AUTH=true so the verify page actually contacts the sastaspace module.",
    );
    await page.goto(
      `${TYPEWARS}/auth/verify?t=${"x".repeat(48)}&app=typewars`,
    );
    await expect(page.getByText(/sign-in failed/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page.getByRole("button", { name: /back to map/i }),
    ).toBeVisible();
  });
});
