import { expect, test } from "@playwright/test";
import {
  freshContext,
  gotoTypewars,
  randomCallsign,
  registerPlayer,
} from "../helpers/typewars.js";

test.describe("typewars · ProfileModal + Avatar", () => {
  test("clicking my own roster row opens ProfileModal with my stats", async ({ page }) => {
    await freshContext(page);
    await gotoTypewars(page);
    const callsign = randomCallsign();
    await registerPlayer(page, "Solari", callsign);
    await page.getByRole("button", { name: /^leaderboard$/i }).click();

    // Find my row (marked with YOU tag) and click.
    const myRow = page.locator(".lb-trow.you").first();
    await expect(myRow).toBeVisible();
    await expect(myRow).toContainText(callsign);
    await myRow.click();

    const modal = page.locator(".modal");
    await expect(modal).toBeVisible();
    await expect(modal.getByRole("heading", { name: callsign })).toBeVisible();
    // Solari mechanic = Clarity — proves the modal is wired to the player row.
    await expect(modal).toContainText(/Solari · Clarity/);

    // Four stat tiles per audit: total dmg, season dmg, best wpm, regions held.
    for (const label of ["total dmg", "season dmg", "best wpm", "regions held"]) {
      await expect(modal.locator(".hud-stat", { hasText: label })).toBeVisible();
    }
    await modal.getByRole("button", { name: /close/i }).click();
    await expect(modal).not.toBeVisible();
  });

  test("anon player avatar shows no verified badge in MapWarMap pill", async ({ page }) => {
    await freshContext(page);
    await gotoTypewars(page);
    await registerPlayer(page, "Ashborn", randomCallsign());
    // Verified badge is .avatar-verified — should NOT exist for an anon player.
    await expect(page.locator(".swap-pill .avatar-verified")).toHaveCount(0);
  });
});
