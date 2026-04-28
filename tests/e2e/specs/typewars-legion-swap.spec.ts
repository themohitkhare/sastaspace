import { expect, test } from "@playwright/test";
import {
  freshContext,
  gotoTypewars,
  randomCallsign,
  registerPlayer,
} from "../helpers/typewars.js";

test.describe("typewars · LegionSwapModal (regression sentinel)", () => {
  test("swap modal opens, picks new legion, confirm closes modal — but legion does NOT change (known bug)", async ({
    page,
  }) => {
    await freshContext(page);
    await gotoTypewars(page);
    const callsign = randomCallsign();
    await registerPlayer(page, "Wardens", callsign);

    // Open the swap modal via the player pill (it doubles as a swap trigger).
    await page.locator(".swap-pill").click();
    const modal = page.locator(".modal");
    await expect(modal).toBeVisible();
    await expect(modal.getByRole("heading", { name: /switch legion/i })).toBeVisible();

    // Pick a different legion (Surge).
    await modal.getByRole("button", { name: /Surge/ }).click();
    const confirm = modal.getByRole("button", { name: /confirm switch/i });
    await expect(confirm).toBeEnabled();
    await confirm.click();

    // Modal closes.
    await expect(modal).not.toBeVisible();

    // BUG: App.tsx:68-70 swapLegion is a no-op — legion stays "Wardens".
    // Expected behaviour once fixed: pill should now read "Surge".
    // Until then, the assertion below DOCUMENTS the bug.
    await expect(page.locator(".swap-pill")).toContainText(/Wardens/);
    await expect(page.locator(".swap-pill")).not.toContainText(/Surge/);
  });
});
