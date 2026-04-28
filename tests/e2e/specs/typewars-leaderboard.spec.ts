import { expect, test } from "@playwright/test";
import {
  freshContext,
  gotoTypewars,
  randomCallsign,
  registerPlayer,
} from "../helpers/typewars.js";

test.describe("typewars · Leaderboard", () => {
  test.beforeEach(async ({ page }) => {
    await freshContext(page);
    await gotoTypewars(page);
    await registerPlayer(page, "Surge", randomCallsign());
    await page.getByRole("button", { name: /^leaderboard$/i }).click();
    await expect(page.getByRole("heading", { name: /^Leaderboard$/ })).toBeVisible();
  });

  test("Legion Standings shows all 5 legions ranked by total damage", async ({ page }) => {
    const section = page.locator(".lb-section").filter({ hasText: "Legion Standings" });
    await expect(section).toBeVisible();
    for (const name of ["Ashborn", "The Codex", "Wardens", "Surge", "Solari"]) {
      await expect(section).toContainText(name);
    }
    await expect(section.locator(".lb-legion-row")).toHaveCount(5);
  });

  test("Player Roster renders rows with callsign + legion + WPM + season dmg", async ({
    page,
  }) => {
    const section = page.locator(".lb-section").filter({ hasText: "Player Roster" });
    await expect(section).toBeVisible();
    // At least one row (the player we just registered).
    await expect(section.locator(".lb-trow").first()).toBeVisible();
    await expect(section.locator(".lb-thead")).toContainText(/best wpm/i);
    await expect(section.locator(".lb-thead")).toContainText(/season dmg/i);
  });

  test("Your Records shows 6 personal stat tiles for the current player", async ({
    page,
  }) => {
    const section = page.locator(".lb-section").filter({ hasText: "Your Records" });
    await expect(section).toBeVisible();
    for (const label of [
      "season rank",
      "total dmg",
      "season dmg",
      "best wpm",
      "legion",
      "mechanic",
    ]) {
      await expect(section.locator(".hud-stat", { hasText: label })).toBeVisible();
    }
    // Surge mechanic = Overdrive — confirms personal grid is reading real player.
    await expect(section.locator(".hud-stat", { hasText: "mechanic" })).toContainText(
      /Overdrive/,
    );
  });
});
