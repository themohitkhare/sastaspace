import { expect, test } from "@playwright/test";
import { signInTypewars } from "../helpers/auth.js";
import {
  freshContext,
  gotoTypewars,
  randomCallsign,
  registerPlayer,
} from "../helpers/typewars.js";
import { TYPEWARS } from "../helpers/urls.js";

test.describe("typewars · SignInTrigger + auth callback", () => {
  test("anon player sees 'sign in →' button in MapWarMap header", async ({ page }) => {
    await freshContext(page);
    await gotoTypewars(page);
    await registerPlayer(page, "Wardens", randomCallsign());
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("magic-link round trip stores JWT under typewars:auth_token and lands on warmap", async ({
    page,
  }) => {
    await freshContext(page);
    await gotoTypewars(page);
    const callsign = randomCallsign();
    await registerPlayer(page, "The Codex", callsign);

    const email = `e2e-tw-${Date.now()}@sastaspace.com`;
    await signInTypewars(page, email);

    // Token landed in localStorage under the typewars-specific key
    // (typewars/src/lib/spacetime.ts:8).
    const token = await page.evaluate(() => window.localStorage.getItem("typewars:auth_token"));
    expect(token, "JWT should be stored in localStorage").toBeTruthy();
    expect(token!.length).toBeGreaterThan(20);

    // After router.replace("/"), we should be back on a typewars URL.
    expect(page.url().startsWith(TYPEWARS)).toBe(true);
  });

  test("/auth/callback with no fragment shows friendly error", async ({ page }) => {
    await page.goto(`${TYPEWARS}/auth/callback`);
    await expect(page.getByText(/missing sign-in details/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /back to map/i })).toBeVisible();
  });
});
