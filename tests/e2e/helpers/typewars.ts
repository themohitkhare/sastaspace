import { expect, type Page } from "@playwright/test";
import { TYPEWARS } from "./urls.js";

export const LEGION_NAMES = ["Ashborn", "The Codex", "Wardens", "Surge", "Solari"] as const;
export type LegionName = (typeof LEGION_NAMES)[number];

export function randomCallsign(prefix = "tw"): string {
  // 24-char limit on the input; base36 timestamp + random suffix stays well under.
  return `${prefix}-${Date.now().toString(36)}${Math.floor(Math.random() * 1000)}`;
}

export async function freshContext(page: Page): Promise<void> {
  // Spacetime's connection token AND the callback page's JWT both live under
  // typewars:auth_token. Clearing it before each test guarantees a fresh anon
  // identity → fresh player row.
  await page.goto(TYPEWARS);
  await page.evaluate(() => window.localStorage.clear());
}

export async function gotoTypewars(page: Page): Promise<void> {
  await page.goto(TYPEWARS, { waitUntil: "domcontentloaded" });
  // App.tsx shows "connecting to typewars…" until the spacetime ws is active.
  // Once active it shows either LegionSelect or MapWarMap depending on whether
  // the player row exists.
  await page.waitForFunction(
    () => !document.body.textContent?.includes("connecting to typewars"),
    null,
    { timeout: 20_000 },
  );
}

export async function registerPlayer(
  page: Page,
  legion: LegionName,
  callsign: string,
): Promise<void> {
  await expect(page.getByRole("heading", { name: /choose your legion/i })).toBeVisible();
  await page.getByRole("button", { name: new RegExp(legion, "i") }).first().click();
  await page.getByPlaceholder(/enter your callsign/i).fill(callsign);
  await page.getByRole("button", { name: /enlist/i }).click();
  // Warmap heading appears once the player row lands and screen flips.
  await expect(page.getByRole("heading", { name: /the contested worlds/i })).toBeVisible({
    timeout: 15_000,
  });
}

export async function enterFirstRegion(page: Page): Promise<string> {
  // Quick region list lives in the right sidebar. Click the first row, then the
  // detail panel "ENTER BATTLE" CTA.
  const firstRow = page.locator(".rql-row").first();
  await expect(firstRow).toBeVisible();
  const name = (await firstRow.locator(".rql-name").textContent())?.trim() ?? "";
  await firstRow.click();
  await page.getByRole("button", { name: /enter battle/i }).click();
  return name;
}

export async function exitBattle(page: Page): Promise<void> {
  await page.getByRole("button", { name: /^← exit$/i }).click();
  await expect(page.getByRole("heading", { name: /the contested worlds/i })).toBeVisible();
}

/** Wait for at least one server-spawned word card to appear in Battle. */
export async function waitForFirstWord(page: Page): Promise<string> {
  const firstCard = page.locator(".word-card").first();
  await expect(firstCard).toBeVisible({ timeout: 10_000 });
  const text = (await firstCard.locator(".word-rest").textContent())?.trim() ?? "";
  return text;
}
