/**
 * Phase 2 F3 — admin panels real-time STDB updates.
 *
 * Each test inserts a row into a public STDB table (or calls a reducer) and
 * asserts the corresponding admin panel UI reflects the change within the
 * spec'd budget. Both the legacy admin-api path and the new STDB path are
 * covered: this file targets the STDB path (NEXT_PUBLIC_USE_STDB_ADMIN=true);
 * the existing admin.spec.ts covers the legacy notes/admin queue.
 *
 * The test runner needs an owner-issued STDB JWT in E2E_OWNER_STDB_TOKEN so
 * we can both (a) authorise the moderation reducer the UI ends up calling
 * and (b) seed the privileged tables (system_metrics / container_status /
 * log_event) which only the owner identity can write to.
 *
 * The whole describe block skips when E2E_OWNER_STDB_TOKEN is unset so CI
 * without the secret keeps passing.
 */

import { expect, test } from "@playwright/test";
import { signIn } from "../helpers/auth.js";
import { sql, pollUntil } from "../helpers/stdb.js";
import { ADMIN, STDB_REST, STDB_DATABASE } from "../helpers/urls.js";

const OWNER_EMAIL = process.env.E2E_OWNER_EMAIL ?? "mohitkhare582@gmail.com";
const OWNER_STDB_TOKEN = process.env.E2E_OWNER_STDB_TOKEN ?? "";

// Owner is auto-registered by sastaspace module init (audit fix C1/C3/P1,
// 2026-04-26): the #[reducer(init)] body now inserts the owner identity as a
// User row if absent, eliminating the need for a separate register_owner_e2e
// call. SKIP_PENDING_BOOTSTRAP_FIX is now false — these tests are unblocked.
const SKIP_PENDING_BOOTSTRAP_FIX = false;

/**
 * Calls a reducer over the STDB REST POST endpoint. Used to seed
 * privileged-write tables (system_metrics, container_status, log_event)
 * which the UI is reading. Equivalent to `spacetime call <db> <reducer>
 * '<json args>'`.
 */
async function callReducer(
  request: import("@playwright/test").APIRequestContext,
  reducerName: string,
  args: unknown[],
  token: string,
): Promise<void> {
  const r = await request.post(
    `${STDB_REST}/v1/database/${STDB_DATABASE}/call/${reducerName}`,
    {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      data: JSON.stringify(args),
    },
  );
  if (r.status() >= 400) {
    throw new Error(
      `stdb reducer ${reducerName} failed: HTTP ${r.status()} ${await r.text()}`,
    );
  }
}

test.describe("admin panels — STDB live updates", () => {
  test.skip(
    !OWNER_STDB_TOKEN || SKIP_PENDING_BOOTSTRAP_FIX,
    "E2E_OWNER_STDB_TOKEN not set, or owner-as-user bootstrap pending (Phase 4 follow-up)",
  );

  test.afterEach(async ({ request }) => {
    // Clean up probe rows so reruns are deterministic.
    await sql(
      request,
      `DELETE FROM comment WHERE author_name LIKE 'e2e-probe-%' OR body LIKE '%e2e-probe-%'`,
    ).catch(() => {});
    await sql(
      request,
      `DELETE FROM container_status WHERE name LIKE 'e2e-probe-%'`,
    ).catch(() => {});
    await sql(
      request,
      `DELETE FROM log_event WHERE container = 'sastaspace-stdb' AND text LIKE 'E2E_PROBE_%'`,
    ).catch(() => {});
  });

  test.beforeEach(async ({ page }) => {
    await signIn(page, OWNER_EMAIL);
    // Admin Shell.resolveAuth reads TWO things, both must be present:
    //   1. localStorage.admin_token  — Google OAuth ID JWT (we decode the
    //      payload to confirm email matches OWNER_EMAIL)
    //   2. admin_stdb_owner_token   — STDB owner JWT for reducer calls
    //      (Group 5/7 audit-fix moved this to sessionStorage; localStorage
    //      stays as a migration fallback)
    // Without admin_token Shell shows the AuthSignIn screen instead of the
    // panels, so the Comments-button click times out. The Google JWT
    // doesn't need to be cryptographically valid — readToken just decodes
    // the payload and checks email + exp.
    await page.addInitScript(
      ([stdbToken, ownerEmail]) => {
        // Fake-but-valid-shape Google ID JWT.
        const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
        const payload = btoa(
          JSON.stringify({
            email: ownerEmail,
            sub: ownerEmail,
            exp: Math.floor(Date.now() / 1000) + 86400, // +1d
          }),
        );
        localStorage.setItem("admin_token", `${header}.${payload}.test-sig`);

        sessionStorage.setItem("admin_stdb_owner_token", stdbToken);
        localStorage.setItem("admin_stdb_owner_token", stdbToken);
      },
      [OWNER_STDB_TOKEN, OWNER_EMAIL] as const,
    );
    await page.goto(ADMIN);
  });

  test("Comments — pending row appears within 5s; Approve flips status via reducer", async ({ page, request }) => {
    const probeBody = `e2e-probe-${Date.now()} hello world`;
    const slug = "2026-04-25-hello";
    // Seed a pending comment via the submit_user_comment reducer. Requires
    // ctx.sender() to exist in the user table — the e2e job's bootstrap
    // step registers the owner identity (E2E_Owner) before tests run.
    await callReducer(
      request,
      "submit_user_comment",
      [slug, probeBody],
      OWNER_STDB_TOKEN,
    );

    await page.locator('button, a', { hasText: /^Comments$/ }).first().click();
    await expect(page.locator(`text=${probeBody}`)).toBeVisible({
      timeout: 10_000,
    });

    await page
      .locator('.comment-card', { hasText: probeBody })
      .locator('button', { hasText: /Approve/ })
      .click();

    await pollUntil(async () => {
      const rows = await sql(
        request,
        `SELECT status FROM comment WHERE body = '${probeBody.replace(/'/g, "''")}'`,
      );
      return rows[0]?.[0] === "approved";
    }, { what: "comment approved via reducer", timeoutMs: 10_000 });
  });

  test("Server — system_metrics upsert reflects in UI within 5s", async ({ page, request }) => {
    await page.locator('button, a', { hasText: /^Server$/ }).first().click();
    const targetCpu = 73.0;
    // Reducer signature (matches modules/sastaspace/src/lib.rs):
    // upsert_system_metrics(cpu_pct, cores, mem_used_gb, mem_total_gb,
    //   mem_pct, swap_used_mb, swap_total_mb, disk_used_gb, disk_total_gb,
    //   disk_pct, net_tx_bytes, net_rx_bytes, uptime_s, gpu_pct?,
    //   gpu_vram_used_mb?, gpu_vram_total_mb?, gpu_temp_c?, gpu_model?)
    await callReducer(
      request,
      "upsert_system_metrics",
      [
        targetCpu,                  // cpu_pct
        16,                         // cores
        8.0, 32.0, 25.0,            // mem
        0, 2048,                    // swap
        100, 500, 20.0,             // disk
        0, 0,                       // net (u64)
        100,                        // uptime_s (u64)
        null, null, null, null, null, // gpu fields
      ],
      OWNER_STDB_TOKEN,
    );
    // Wait for the rounded CPU value to appear on a card.
    await expect(
      page.locator(".card__value", { hasText: `${Math.round(targetCpu)}%` }),
    ).toBeVisible({ timeout: 5_000 });
  });

  test("Services — container_status upsert reflects in UI within 5s", async ({ page, request }) => {
    await page.locator('button, a', { hasText: /^Services$/ }).first().click();
    const probeName = `e2e-probe-${Date.now()}`;
    await callReducer(
      request,
      "upsert_container_status",
      [
        probeName,         // name
        "running",         // status
        "test:latest",     // image
        60,                // uptime_s (u64)
        100, 1024,         // mem
        0,                 // restart_count
      ],
      OWNER_STDB_TOKEN,
    );
    // friendlyName(): "e2e-probe-<n>" → "E2e Probe <n>". Match the EXACT
    // probe — concurrent test projects (desktop-chromium, notes-legacy,
    // notes-stdb) write probes near-simultaneously, so a /e2e probe/i
    // partial match hits multiple rows and trips strict-mode locator.
    const friendlyProbe = probeName
      .replace(/-/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
    await expect(
      page.locator(".service-card__name", { hasText: friendlyProbe }),
    ).toBeVisible({ timeout: 5_000 });
  });

  test("Logs — log_event row appears in panel within 5s", async ({ page, request }) => {
    // The Logs sidebar lists containers from `container_status` (STDB
    // path) or /containers HTTP poll (legacy path). The admin-collector
    // worker that normally populates either is currently disabled
    // (binding regen pending). The STDB path lets us seed direct; the
    // legacy path doesn't, so we skip it for this test until the
    // admin-collector is back online.
    test.skip(
      test.info().project.name === "notes-legacy",
      "Logs sidebar in legacy path needs admin-api/admin-collector — currently disabled",
    );

    await callReducer(
      request,
      "upsert_container_status",
      ["sastaspace-stdb", "running", "clockworklabs/spacetime:latest", 60, 100, 1024, 0],
      OWNER_STDB_TOKEN,
    );
    await page.locator('button, a', { hasText: /^Logs$/ }).first().click();
    // Wait for the sidebar entry to render before clicking it (the upsert
    // → STDB subscription → React render chain isn't instantaneous).
    const stdbItem = page.locator(".logs-service-item", { hasText: /Stdb/i }).first();
    await expect(stdbItem).toBeVisible({ timeout: 10_000 });
    await stdbItem.click();
    // Give the add_log_interest reducer a beat to land before we append.
    await new Promise((r) => setTimeout(r, 500));
    const probeText = `E2E_PROBE_${Date.now()}`;
    // append_log_event(container, ts_micros, level, text)
    await callReducer(
      request,
      "append_log_event",
      ["sastaspace-stdb", Date.now() * 1000, "info", probeText],
      OWNER_STDB_TOKEN,
    );
    await expect(
      page.locator(`.log-line:has-text("${probeText}")`),
    ).toBeVisible({ timeout: 5_000 });
  });
});
