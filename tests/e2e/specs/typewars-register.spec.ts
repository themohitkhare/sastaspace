import { expect, test } from "@playwright/test";
import {
  freshContext,
  gotoTypewars,
  randomCallsign,
  registerPlayer,
} from "../helpers/typewars.js";

test.describe("typewars · LegionSelect + App routing", () => {
  test("anon visit lands on LegionSelect with all 5 legions + season placeholder", async ({
    page,
  }) => {
    await freshContext(page);
    await gotoTypewars(page);

    await expect(page.getByRole("heading", { name: /choose your legion/i })).toBeVisible();
    for (const name of ["Ashborn", "The Codex", "Wardens", "Surge", "Solari"]) {
      await expect(page.getByRole("button", { name: new RegExp(name) })).toBeVisible();
    }
    // Hardcoded placeholder from LegionSelect:23 — flagged in audit.
    await expect(page.locator(".topbar")).toContainText(/season 1.*day 12.*30/);
  });

  test("ENLIST button stays disabled until both legion + callsign are set", async ({
    page,
  }) => {
    await freshContext(page);
    await gotoTypewars(page);

    const enlist = page.getByRole("button", { name: /enlist/i });
    await expect(enlist).toBeDisabled();
    await page.getByRole("button", { name: /Wardens/ }).click();
    await expect(enlist).toBeDisabled();
    await page.getByPlaceholder(/enter your callsign/i).fill(randomCallsign());
    await expect(enlist).toBeEnabled();
  });

  test("registerPlayer reducer round trip → warmap renders", async ({ page }) => {
    await freshContext(page);
    await gotoTypewars(page);

    const callsign = randomCallsign();
    await registerPlayer(page, "Wardens", callsign);

    // The header pill shows the callsign + legion name.
    await expect(page.locator(".swap-pill")).toContainText(callsign);
    await expect(page.locator(".swap-pill")).toContainText(/Wardens/);
  });
});
