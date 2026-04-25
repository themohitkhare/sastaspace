import { expect, test } from "@playwright/test";
import { LANDING, NOTES } from "../helpers/urls.js";

/**
 * Catches the bug class from earlier today: home page going stale and
 * still serving anchor links to in-page sections instead of routing
 * to /lab, /projects, /about. Also catches: pages disappearing,
 * security headers regressing, brand wordmark missing.
 */

test.describe("landing — multi-page nav", () => {
  test("home renders with brand + hero + nav links to /lab /projects /about", async ({ page }) => {
    await page.goto(LANDING);
    // Brand identity
    await expect(page.getByLabel(/sastaspace home/i)).toBeVisible();
    // Hero
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/sasta lab/i);
    // CTAs link to actual pages, not anchors
    await expect(page.getByRole("link", { name: /see the lab/i })).toHaveAttribute(
      "href",
      "/projects",
    );
    await expect(page.getByRole("link", { name: /about the idea/i })).toHaveAttribute(
      "href",
      "/about",
    );
  });

  test("nav links go to dedicated pages, NOT in-page anchors", async ({ page }) => {
    await page.goto(LANDING);
    const nav = page.locator("nav[aria-label='Primary']");
    await expect(nav.getByRole("link", { name: "the lab" })).toHaveAttribute("href", "/lab");
    await expect(nav.getByRole("link", { name: "projects" })).toHaveAttribute("href", "/projects");
    await expect(nav.getByRole("link", { name: "about" })).toHaveAttribute("href", "/about");
    // Notes navigates to the subdomain
    await expect(nav.getByRole("link", { name: "notes" })).toHaveAttribute(
      "href",
      "https://notes.sastaspace.com",
    );
  });

  test("clicking 'the lab' navigates to /lab and renders the principles", async ({ page }) => {
    await page.goto(LANDING);
    await page.getByRole("link", { name: "the lab", exact: true }).click();
    await page.waitForURL(/\/lab\/?$/);
    await expect(page.getByRole("heading", { name: /not a portfolio/i })).toBeVisible();
    await expect(page.getByText(/cheap to build/i)).toBeVisible();
    await expect(page.getByText(/one command to live/i)).toBeVisible();
    await expect(page.getByText(/open by default/i)).toBeVisible();
  });

  test("clicking 'projects' navigates to /projects", async ({ page }) => {
    await page.goto(LANDING);
    await page.getByRole("link", { name: "projects", exact: true }).click();
    await page.waitForURL(/\/projects\/?$/);
    await expect(page.getByRole("heading", { name: /what's on the bench/i })).toBeVisible();
  });

  test("clicking 'about' navigates to /about with the lab-card", async ({ page }) => {
    await page.goto(LANDING);
    await page.getByRole("link", { name: "about", exact: true }).click();
    await page.waitForURL(/\/about\/?$/);
    await expect(page.getByRole("heading", { name: /Hi.*Mohit/i })).toBeVisible();
    await expect(page.getByText(/the lab, in one line/i)).toBeVisible();
  });

  test("footer links to real GitHub + LinkedIn (themohitkhare), not placeholders", async ({ page }) => {
    await page.goto(LANDING);
    const footer = page.locator("footer");
    await expect(footer.getByRole("link", { name: "github" })).toHaveAttribute(
      "href",
      "https://github.com/themohitkhare",
    );
    await expect(footer.getByRole("link", { name: "linkedin" })).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/themohitkhare",
    );
    // No placeholder href="#" links survived
    const hrefs = await footer.locator("a").evaluateAll((els) =>
      (els as HTMLAnchorElement[]).map((a) => a.getAttribute("href")),
    );
    expect(hrefs.every((h) => h && h !== "#")).toBe(true);
  });
});

test.describe("landing — security baseline", () => {
  for (const path of ["/", "/lab", "/projects", "/about"]) {
    test(`${path} returns 200 with full security header set`, async ({ request }) => {
      const r = await request.get(`${LANDING}${path}`);
      expect(r.status()).toBe(200);
      const headers = r.headers();
      expect(headers["strict-transport-security"]).toContain("max-age=");
      expect(headers["x-frame-options"]).toBe("DENY");
      expect(headers["x-content-type-options"]).toBe("nosniff");
      expect(headers["content-security-policy"]).toContain("default-src 'self'");
      // CSP must include the auth service so the sign-in modal can POST to it
      const csp = headers["content-security-policy"] ?? "";
      // notes is the surface that needs auth; landing's CSP doesn't strictly
      // need it, but presence checks the header isn't truncated.
      expect(csp).toContain("frame-ancestors 'none'");
    });
  }
});
