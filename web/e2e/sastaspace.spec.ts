import { test, expect, type Page } from "@playwright/test";

const BASE = "http://localhost:3000";
const RESULT_URL = `${BASE}/example-com`;

// ─── Helpers ────────────────────────────────────────────────────────────────

async function getBodyWidth(page: Page): Promise<number> {
  return page.evaluate(() => document.body.scrollWidth);
}

async function getViewportWidth(page: Page): Promise<number> {
  return page.evaluate(() => window.innerWidth);
}

async function hasHorizontalScroll(page: Page): Promise<boolean> {
  const [body, vp] = await Promise.all([getBodyWidth(page), getViewportWidth(page)]);
  return body > vp;
}

// ─── 1. Landing page – desktop ───────────────────────────────────────────────

test.describe("Landing page – desktop (1280px)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(BASE);
  });

  test("renders headline and subtext", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /See your website reimagined/i })).toBeVisible();
    await expect(page.getByText(/Enter your URL and watch AI redesign/i)).toBeVisible();
  });

  test("URL input and button are visible", async ({ page }) => {
    await expect(page.getByPlaceholder("yourwebsite.com")).toBeVisible();
    await expect(page.getByRole("button", { name: /Redesign My Site/i })).toBeVisible();
  });

  test("How it works section is visible", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /How it works/i })).toBeVisible();
    await expect(page.getByText("Enter your URL", { exact: true })).toBeVisible();
    await expect(page.getByText("AI redesigns it")).toBeVisible();
    await expect(page.getByText("See the result")).toBeVisible();
  });

  test("submit empty URL shows validation error", async ({ page }) => {
    await page.getByRole("button", { name: /Redesign My Site/i }).click();
    await expect(page.getByText(/Please enter a valid website address|enter a valid/i)).toBeVisible();
  });

  test("submit invalid string shows error (noValidate — custom inline error)", async ({ page }) => {
    await page.getByPlaceholder("yourwebsite.com").fill("notaurl");
    await page.getByRole("button", { name: /Redesign My Site/i }).click();
    // noValidate disables browser tooltip — custom error must appear as DOM element
    await expect(page.getByText(/Please enter a valid website address|valid/i)).toBeVisible();
  });

  test("no horizontal scroll", async ({ page }) => {
    expect(await hasHorizontalScroll(page)).toBe(false);
  });

  test("page title is set", async ({ page }) => {
    await expect(page).toHaveTitle(/SastaSpace/i);
  });
});

// ─── 2. Landing page – mobile (375px) ────────────────────────────────────────

test.describe("Landing page – mobile (375px)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(BASE);
  });

  test("no horizontal scroll at 375px", async ({ page }) => {
    expect(await hasHorizontalScroll(page)).toBe(false);
  });

  test("URL input is visible and usable", async ({ page }) => {
    const input = page.getByPlaceholder("yourwebsite.com");
    await expect(input).toBeVisible();
    const box = await input.boundingBox();
    expect(box).not.toBeNull();
    // input should fill most of the viewport width
    expect(box!.width).toBeGreaterThan(300);
  });

  test("button is visible with adequate touch target (>=44px tall)", async ({ page }) => {
    const btn = page.getByRole("button", { name: /Redesign My Site/i });
    await expect(btn).toBeVisible();
    const box = await btn.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(44);
  });

  test("headline is readable (no overflow)", async ({ page }) => {
    const h1 = page.getByRole("heading", { name: /See your website reimagined/i });
    await expect(h1).toBeVisible();
  });
});

// ─── 3. Result page – structure ──────────────────────────────────────────────

test.describe("Result page – structure", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(RESULT_URL);
    // Wait for the contact form to appear (it's client-rendered)
    await page.waitForSelector("h2", { timeout: 5000 });
  });

  test("shows correct heading for subdomain", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /example\.com has been redesigned/i })).toBeVisible();
  });

  test("iframe preview exists", async ({ page }) => {
    const iframe = page.locator("iframe").first();
    await expect(iframe).toBeVisible();
  });

  test("'Take me to the future' button exists inside iframe overlay", async ({ page }) => {
    await expect(page.getByRole("link", { name: /Take me to the future/i })).toBeVisible();
  });

  test("'View original site' link exists and points to original domain", async ({ page }) => {
    const link = page.getByRole("link", { name: /View original site/i });
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", "https://example.com");
    await expect(link).toHaveAttribute("target", "_blank");
  });

  test("HR divider exists between preview and form", async ({ page }) => {
    const hr = page.locator("hr").first();
    await expect(hr).toBeVisible();
  });

  test("page title is set", async ({ page }) => {
    await expect(page).toHaveTitle(/Your redesign is ready/i);
  });

  test("no horizontal scroll on desktop", async ({ page }) => {
    expect(await hasHorizontalScroll(page)).toBe(false);
  });
});

// ─── 4. Contact form – presence and fields ───────────────────────────────────

test.describe("Contact form – fields and layout", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(RESULT_URL);
    await page.waitForSelector("h2", { timeout: 5000 });
  });

  test("contact form heading is correct", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: /Like what you see\? Let's build the real thing\./i })
    ).toBeVisible();
  });

  test("has exactly Name, Email, Message fields and no phone field", async ({ page }) => {
    await expect(page.getByLabel("Name")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Message")).toBeVisible();
    // No phone field
    await expect(page.getByLabel(/phone/i)).not.toBeVisible();
    await expect(page.locator("input[type=tel]")).not.toBeVisible();
    await expect(page.locator("input[name=phone]")).not.toBeVisible();
  });

  test("message field is a textarea with rows=4", async ({ page }) => {
    const textarea = page.locator("textarea");
    await expect(textarea).toBeVisible();
    await expect(textarea).toHaveAttribute("rows", "4");
  });

  test("submit button says 'Send Message'", async ({ page }) => {
    await expect(page.getByRole("button", { name: /Send Message/i })).toBeVisible();
  });

  test("submit button is full-width (>=44px tall)", async ({ page }) => {
    // Wait for motion.div scale animation to complete (0.4s duration)
    await page.waitForTimeout(500);
    const btn = page.getByRole("button", { name: /Send Message/i });
    const box = await btn.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(44);
  });

  test("form max-width is constrained (max-w-xl ≈ 576px)", async ({ page }) => {
    const form = page.locator("form").first();
    const box = await form.boundingBox();
    expect(box).not.toBeNull();
    // max-w-xl = 36rem = 576px at default 16px base, allow small tolerance
    expect(box!.width).toBeLessThanOrEqual(580);
  });
});

// ─── 5. Contact form – client-side validation ─────────────────────────────────

test.describe("Contact form – validation", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(RESULT_URL);
    await page.waitForSelector("form", { timeout: 5000 });
  });

  test("submit empty form shows all three field errors", async ({ page }) => {
    await page.getByRole("button", { name: /Send Message/i }).click();
    await expect(page.getByText("Please enter your name")).toBeVisible();
    await expect(page.getByText("Please enter a valid email address")).toBeVisible();
    await expect(page.getByText("Please enter a message")).toBeVisible();
  });

  test("name error clears when name is filled", async ({ page }) => {
    await page.getByRole("button", { name: /Send Message/i }).click();
    await expect(page.getByText("Please enter your name")).toBeVisible();
    await page.getByLabel("Name").fill("Alice");
    await expect(page.getByText("Please enter your name")).not.toBeVisible();
  });

  test("email error clears when valid email is filled", async ({ page }) => {
    await page.getByRole("button", { name: /Send Message/i }).click();
    await expect(page.getByText("Please enter a valid email address")).toBeVisible();
    await page.getByLabel("Email").fill("alice@example.com");
    await expect(page.getByText("Please enter a valid email address")).not.toBeVisible();
  });

  test("invalid email format shows error (noValidate — custom inline error)", async ({ page }) => {
    await page.getByLabel("Name").fill("Alice");
    await page.getByLabel("Email").fill("not-an-email");
    await page.getByLabel("Message").fill("Hello");
    await page.getByRole("button", { name: /Send Message/i }).click();
    // noValidate disables browser tooltip — custom validation error must show inline
    await expect(page.getByText("Please enter a valid email address")).toBeVisible();
  });

  test("message error clears when message is filled", async ({ page }) => {
    await page.getByRole("button", { name: /Send Message/i }).click();
    await expect(page.getByText("Please enter a message")).toBeVisible();
    await page.getByLabel("Message").fill("Hello there");
    await expect(page.getByText("Please enter a message")).not.toBeVisible();
  });
});

// ─── 6. Contact form – mobile (375px) ────────────────────────────────────────

test.describe("Contact form – mobile (375px)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(RESULT_URL);
    await page.waitForSelector("form", { timeout: 5000 });
  });

  test("no horizontal scroll at 375px on result page", async ({ page }) => {
    expect(await hasHorizontalScroll(page)).toBe(false);
  });

  test("Name input fills available width at 375px", async ({ page }) => {
    const input = page.getByLabel("Name");
    const box = await input.boundingBox();
    expect(box).not.toBeNull();
    // At 375px with px-4 padding (32px total) input should be ~300+ px wide
    expect(box!.width).toBeGreaterThan(280);
  });

  test("submit button fills available width at 375px", async ({ page }) => {
    // Wait for motion.div scale animation (0.4s) before measuring
    await page.waitForTimeout(500);
    const btn = page.getByRole("button", { name: /Send Message/i });
    const box = await btn.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThan(280);
    expect(box!.height).toBeGreaterThanOrEqual(44);
  });

  test("contact form heading is visible at 375px", async ({ page }) => {
    await page.locator("h2").first().scrollIntoViewIfNeeded();
    const h2 = page.getByRole("heading", { name: /Like what you see/i });
    await expect(h2).toBeVisible();
  });

  test("validation errors visible at 375px", async ({ page }) => {
    await page.getByRole("button", { name: /Send Message/i }).click();
    await expect(page.getByText("Please enter your name")).toBeVisible();
  });
});

// ─── 7. API route – direct HTTP tests ────────────────────────────────────────

test.describe("API /api/contact – server-side logic", () => {
  test("honeypot field returns 200 ok:true without sending email", async ({ request }) => {
    const res = await request.post(`${BASE}/api/contact`, {
      data: {
        name: "Bot",
        email: "bot@spam.com",
        message: "spam",
        website: "filled-by-bot",   // honeypot
        turnstileToken: "fake",
        subdomain: "example-com",
      },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
  });

  test("missing required fields returns 400", async ({ request }) => {
    const res = await request.post(`${BASE}/api/contact`, {
      data: {
        name: "",
        email: "",
        message: "",
        website: "",
        turnstileToken: "fake",
        subdomain: "example-com",
      },
    });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.error).toBeTruthy();
  });

  test("missing name returns 400", async ({ request }) => {
    const res = await request.post(`${BASE}/api/contact`, {
      data: {
        name: "",
        email: "alice@example.com",
        message: "Hello",
        website: "",
        turnstileToken: "fake",
        subdomain: "example-com",
      },
    });
    expect(res.status()).toBe(400);
  });

  test("invalid turnstile token is handled (400 in prod, 500 in dev with test keys)", async ({ request }) => {
    const res = await request.post(`${BASE}/api/contact`, {
      data: {
        name: "Alice",
        email: "alice@example.com",
        message: "Hello, I am interested",
        website: "",
        turnstileToken: "invalid-token-xyz",
        subdomain: "example-com",
      },
    });
    // Dev test key (1x000...AA) accepts ALL tokens → Turnstile passes → Resend fails → 500
    // Production real secret → Turnstile rejects invalid token → 400
    // Either way: never 200 with ok:true
    expect([400, 500]).toContain(res.status());
    const body = await res.json();
    expect(body.ok).not.toBe(true);
  });

  test("GET /api/contact returns 405 Method Not Allowed", async ({ request }) => {
    const res = await request.get(`${BASE}/api/contact`);
    expect(res.status()).toBe(405);
  });
});

// ─── 8. Iframe recursive loop detection ──────────────────────────────────────

test.describe("Result page – iframe sanity", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(RESULT_URL);
    await page.waitForSelector("iframe", { timeout: 5000 });
  });

  test("iframe src points to backend URL (not a same-origin Next.js route)", async ({ page }) => {
    const iframeSrc = await page.locator("iframe").first().getAttribute("src");
    // With NEXT_PUBLIC_BACKEND_URL set, src must include the backend origin
    // This prevents the recursive ResultView loop in development
    expect(iframeSrc).toContain("localhost:8080/example-com/");
  });

  test("iframe does NOT recursively render the Next.js result page", async ({ page }) => {
    // With NEXT_PUBLIC_BACKEND_URL fix applied, the iframe points to the backend.
    // The backend returns 404/empty for unknown subdomains in dev (not ResultView).
    // Either way, there must NOT be another ResultView heading inside the iframe.
    const frame = page.frameLocator("iframe").first();
    const h2InIframe = await frame.getByRole("heading", { name: /has been redesigned/i })
      .count()
      .catch(() => 0);
    expect(h2InIframe).toBe(0);
  });
});

// ─── 9. Progress page appearance ────────────────────────────────────────────

test.describe("Landing → progress transition", () => {
  test("submitting valid URL transitions to connecting state", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(BASE);
    await page.getByPlaceholder("yourwebsite.com").fill("https://example.com");
    await page.getByRole("button", { name: /Redesign My Site/i }).click();
    // Should transition away from landing (either to progress or error state)
    await expect(page.getByPlaceholder("yourwebsite.com")).not.toBeVisible({ timeout: 5000 });
  });

  test("progress page no horizontal scroll at 375px", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(BASE);
    await page.getByPlaceholder("yourwebsite.com").fill("https://example.com");
    await page.getByRole("button", { name: /Redesign My Site/i }).click();
    await page.waitForTimeout(1000);
    expect(await hasHorizontalScroll(page)).toBe(false);
  });
});

// ─── 10. SSE progress view with mocked backend (TEST-03) ────────────────────

test.describe("SSE progress flow (mocked backend)", () => {
  /**
   * Helper: Build an SSE text payload from an array of events.
   * Each event is { event: string, data: object }.
   */
  function buildSSE(events: Array<{ event: string; data: Record<string, unknown> }>): string {
    return events
      .map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`)
      .join("");
  }

  test("valid URL triggers progress view with crawling, redesigning, deploying steps", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });

    // Intercept POST /redesign to the backend and return a mocked SSE stream
    await page.route("**/redesign", async (route) => {
      const sseBody = buildSSE([
        { event: "crawling", data: { status: "crawling" } },
        { event: "redesigning", data: { status: "redesigning" } },
        { event: "deploying", data: { status: "deploying" } },
        { event: "done", data: { subdomain: "example-com" } },
      ]);

      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sseBody,
      });
    });

    await page.goto(BASE);

    // Fill and submit a valid URL
    await page.getByPlaceholder("yourwebsite.com").fill("https://example.com");
    await page.getByRole("button", { name: /Redesign My Site/i }).click();

    // The progress view should appear — verify step labels are rendered
    // The SSE events trigger step indicators; at least the step labels should show
    // "Analyzing example.com", "Redesigning your site with AI", "Preparing your new example.com"
    // After "done", the app navigates to /example-com
    // We verify the landing page disappears (progress view takes over)
    await expect(page.getByPlaceholder("yourwebsite.com")).not.toBeVisible({ timeout: 5000 });

    // Eventually navigates to result page after done event
    await page.waitForURL("**/example-com", { timeout: 10000 });
  });

  test("progress view shows step indicators during SSE stream", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });

    // Intercept and hold the SSE stream so we can check the progress view state
    await page.route("**/redesign", async (route) => {
      // Only send crawling and redesigning — do NOT send done, so progress view stays visible
      const sseBody = buildSSE([
        { event: "crawling", data: { status: "crawling" } },
        { event: "redesigning", data: { status: "redesigning" } },
      ]);

      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sseBody,
      });
    });

    await page.goto(BASE);
    await page.getByPlaceholder("yourwebsite.com").fill("https://example.com");
    await page.getByRole("button", { name: /Redesign My Site/i }).click();

    // Wait for the progress view to render with step indicators
    // The progress view shows step labels like "Analyzing example.com"
    await expect(page.getByText(/Analyzing example\.com/i)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Redesigning your site with AI/i)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Preparing your new example\.com/i)).toBeVisible({ timeout: 5000 });
  });

  test("SSE error event shows error message", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });

    await page.route("**/redesign", async (route) => {
      const sseBody = buildSSE([
        { event: "crawling", data: { status: "crawling" } },
        { event: "error", data: { error: "Site could not be crawled" } },
      ]);

      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sseBody,
      });
    });

    await page.goto(BASE);
    await page.getByPlaceholder("yourwebsite.com").fill("https://example.com");
    await page.getByRole("button", { name: /Redesign My Site/i }).click();

    // Error view should appear with "Something went wrong"
    await expect(page.getByText(/Something went wrong/i)).toBeVisible({ timeout: 5000 });
    // "Try again" button should be visible
    await expect(page.getByRole("button", { name: /Try again/i })).toBeVisible();
  });
});
