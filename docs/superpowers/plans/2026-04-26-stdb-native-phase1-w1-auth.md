# Phase 1 W1 — Auth Mailer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (run as one of 4 parallel workstream subagents). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move email send logic out of `services/auth/` into a `pending_email` STDB table + a tiny `auth-mailer.ts` Mastra-free worker. Add a `verify_token` reducer that atomically consumes a token + registers a user (replacing the multi-step Python flow).

**Architecture:** New `pending_email` table holds outbound email rows. `request_magic_link` reducer (existing wrapper for `issue_auth_token`) inserts both an `auth_token` row AND a `pending_email` row in one transaction. `auth-mailer.ts` subscribes to `pending_email WHERE status='queued'`, calls Resend, then calls `mark_email_sent` or `mark_email_failed`. Frontend's `/auth/verify` page calls a single `verify_token` reducer that does consume + lookup-email + register-user atomically.

**Tech Stack:** Rust (STDB module, table+reducer+test), TypeScript (worker agent + Vitest), `resend` npm SDK.

**Spec:** `docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md` § "What gets added to the SpacetimeDB module / Email/auth"

**Master plan:** `docs/superpowers/plans/2026-04-26-stdb-native-master.md`

**Coordination:** Modifies `modules/sastaspace/src/lib.rs` — must use append-only fenced section `// === auth-mailer (Phase 1 W1) ===`. Other workstreams append after their own fences.

---

## Task 1: Add `pending_email` table + auth reducers (Rust)

**Files:**
- Modify: `modules/sastaspace/src/lib.rs` — append fenced section
- Modify: `modules/sastaspace/src/lib.rs` tests block (add tests at file end)

- [ ] **Step 1: Append the table and reducers**

At end of `modules/sastaspace/src/lib.rs`, before the final closing brace if any (or at file end if it's flat), append:

```rust
// === auth-mailer (Phase 1 W1) ===

/// Outbound emails the auth-mailer worker drains.
/// status: "queued" | "sent" | "failed"
#[table(accessor = pending_email)]
pub struct PendingEmail {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    pub to_email: String,
    pub subject: String,
    pub body_html: String,
    pub body_text: String,
    pub created_at: Timestamp,
    pub status: String,
    pub provider_msg_id: Option<String>,
    pub error: Option<String>,
}

/// Frontend-callable reducer. Validates email, mints a token, queues the email.
/// callback_url is the app's /auth/callback URL (notes/typewars/admin) — the
/// worker stitches it into the magic-link.
#[reducer]
pub fn request_magic_link(
    ctx: &ReducerContext,
    email: String,
    app: String,
    prev_identity_hex: Option<String>,
    callback_url: String,
) -> Result<(), String> {
    let email = email.trim().to_lowercase();
    if !email.contains('@') || email.len() > 200 {
        return Err("invalid email".into());
    }
    if !matches!(app.as_str(), "notes" | "typewars" | "admin") {
        return Err("unknown app".into());
    }
    if !callback_url.starts_with("https://") || callback_url.len() > 400 {
        return Err("invalid callback_url".into());
    }
    let token: String = (0..32)
        .map(|_| {
            let n = ctx.rng().u32(..62);
            let c = if n < 26 { b'a' + n as u8 }
                    else if n < 52 { b'A' + (n - 26) as u8 }
                    else { b'0' + (n - 52) as u8 };
            c as char
        })
        .collect();
    let now = ctx.timestamp;
    let expires = Timestamp::from_micros_since_unix_epoch(
        now.to_micros_since_unix_epoch() + AUTH_TOKEN_TTL_MICROS,
    );
    ctx.db.auth_token().insert(AuthToken {
        token: token.clone(),
        email: email.clone(),
        created_at: now,
        expires_at: expires,
        used_at: None,
    });
    let prev_qs = prev_identity_hex
        .as_deref()
        .map(|p| format!("&prev={}", p.trim_start_matches("0x")))
        .unwrap_or_default();
    let magic_link = format!(
        "{}?t={}&app={}{}",
        callback_url.trim_end_matches('/'),
        token,
        app,
        prev_qs,
    );
    ctx.db.pending_email().insert(PendingEmail {
        id: 0,
        to_email: email.clone(),
        subject: "Your sign-in link to sastaspace".into(),
        body_html: render_magic_link_html(&magic_link),
        body_text: render_magic_link_text(&magic_link),
        created_at: now,
        status: "queued".into(),
        provider_msg_id: None,
        error: None,
    });
    Ok(())
}

/// Worker-only: marks an email as sent. assert_owner enforces.
#[reducer]
pub fn mark_email_sent(ctx: &ReducerContext, id: u64, provider_msg_id: String) -> Result<(), String> {
    assert_owner(ctx)?;
    let mut row = ctx.db.pending_email().id().find(id).ok_or("unknown email id")?;
    row.status = "sent".into();
    row.provider_msg_id = Some(provider_msg_id);
    ctx.db.pending_email().id().update(row);
    Ok(())
}

/// Worker-only: records a send failure for retry/observability.
#[reducer]
pub fn mark_email_failed(ctx: &ReducerContext, id: u64, error: String) -> Result<(), String> {
    assert_owner(ctx)?;
    let mut row = ctx.db.pending_email().id().find(id).ok_or("unknown email id")?;
    row.status = "failed".into();
    row.error = Some(error);
    ctx.db.pending_email().id().update(row);
    Ok(())
}

/// Atomic verify: consume token + register user under ctx.sender() identity.
/// The frontend mints a fresh identity via POST /v1/identity, reconnects with
/// that JWT, then calls this reducer. ctx.sender() is therefore the new identity.
#[reducer]
pub fn verify_token(ctx: &ReducerContext, token: String, display_name: String) -> Result<(), String> {
    let now = ctx.timestamp;
    let mut tok = ctx.db.auth_token().token().find(token.clone())
        .ok_or("unknown token")?;
    if tok.used_at.is_some() {
        return Err("token already used".into());
    }
    if tok.expires_at.to_micros_since_unix_epoch() < now.to_micros_since_unix_epoch() {
        return Err("token expired".into());
    }
    tok.used_at = Some(now);
    ctx.db.auth_token().token().update(tok.clone());

    let display_name = if display_name.trim().is_empty() {
        tok.email.split('@').next().unwrap_or("user").to_string()
    } else {
        display_name.trim().chars().take(60).collect()
    };

    if let Some(mut existing) = ctx.db.user().email().find(tok.email.clone()) {
        existing.identity = ctx.sender();
        existing.display_name = display_name;
        ctx.db.user().email().update(existing);
    } else {
        ctx.db.user().insert(User {
            identity: ctx.sender(),
            email: tok.email.clone(),
            display_name,
            created_at: now,
        });
    }
    Ok(())
}

fn render_magic_link_html(link: &str) -> String {
    format!(
        r#"<!doctype html><html><body style="margin:0;padding:32px;background:#f5f1e8;color:#1a1917;font-family:-apple-system,system-ui,sans-serif"><div style="max-width:520px;margin:0 auto;background:#fbf8f0;border:1px solid rgba(168,161,150,0.4);border-radius:16px;padding:28px 32px"><h1 style="font-size:24px;font-weight:500;margin:0 0 14px">Sign in to sastaspace.</h1><p style="font-size:15px;line-height:1.55;margin:0 0 20px">Click below to sign in. Good for 15 minutes, works once.</p><p style="margin:0 0 24px"><a href="{link}" style="display:inline-block;background:#1a1917;color:#f5f1e8;padding:12px 22px;border-radius:10px;text-decoration:none;font-size:15px;font-weight:500">sign in &rarr;</a></p><p style="font-size:13px;color:#6b6458;margin:0 0 8px">If the button doesn't work, paste this URL:</p><p style="font-family:ui-monospace,Menlo,monospace;font-size:12px;color:#6b6458;word-break:break-all;margin:0 0 24px">{link}</p><p style="font-size:12px;color:#a8a196;margin:0">If you didn't ask for this, ignore.</p></div></body></html>"#
    )
}

fn render_magic_link_text(link: &str) -> String {
    format!("Sign in to sastaspace.\n\nClick this link (good for 15 minutes, works once):\n\n  {link}\n\nIf you didn't ask for this, ignore.\n\n—\nsastaspace.com\n")
}

// === end auth-mailer (Phase 1 W1) ===
```

- [ ] **Step 2: Add Rust tests for the new reducers**

In the `#[cfg(test)] mod tests {…}` block at the file's end (create one if absent), add:

```rust
#[cfg(test)]
mod auth_mailer_tests {
    use super::*;
    use spacetimedb::test::{TestContext, TestDb};

    #[test]
    fn request_magic_link_queues_email_and_token() {
        let db = TestDb::new();
        let ctx = TestContext::owner();
        request_magic_link(
            &ctx,
            "Foo@Example.com".into(),
            "notes".into(),
            None,
            "https://notes.sastaspace.com/auth/callback".into(),
        ).unwrap();
        assert_eq!(db.pending_email().iter().count(), 1);
        assert_eq!(db.auth_token().iter().count(), 1);
        let row = db.pending_email().iter().next().unwrap();
        assert_eq!(row.to_email, "foo@example.com");
        assert_eq!(row.status, "queued");
    }

    #[test]
    fn request_magic_link_rejects_bad_email() {
        let ctx = TestContext::owner();
        let r = request_magic_link(&ctx, "notanemail".into(), "notes".into(), None,
            "https://notes.sastaspace.com/auth/callback".into());
        assert!(r.is_err());
    }

    #[test]
    fn verify_token_happy_path_creates_user() {
        let db = TestDb::new();
        let ctx = TestContext::owner();
        request_magic_link(&ctx, "alice@example.com".into(), "notes".into(), None,
            "https://notes.sastaspace.com/auth/callback".into()).unwrap();
        let token = db.auth_token().iter().next().unwrap().token;
        let alice_ctx = TestContext::with_sender(Identity::from_hex(
            "1111111111111111111111111111111111111111111111111111111111111111").unwrap());
        verify_token(&alice_ctx, token, "Alice".into()).unwrap();
        let user = db.user().email().find("alice@example.com".to_string()).unwrap();
        assert_eq!(user.display_name, "Alice");
    }

    #[test]
    fn verify_token_rejects_used() {
        let db = TestDb::new();
        let ctx = TestContext::owner();
        request_magic_link(&ctx, "bob@example.com".into(), "notes".into(), None,
            "https://notes.sastaspace.com/auth/callback".into()).unwrap();
        let token = db.auth_token().iter().next().unwrap().token;
        let bob_ctx = TestContext::with_sender(Identity::from_hex(
            "2222222222222222222222222222222222222222222222222222222222222222").unwrap());
        verify_token(&bob_ctx, token.clone(), "Bob".into()).unwrap();
        let r = verify_token(&bob_ctx, token, "Bob".into());
        assert!(r.is_err());
    }

    #[test]
    fn mark_email_sent_requires_owner() {
        let db = TestDb::new();
        let owner = TestContext::owner();
        request_magic_link(&owner, "x@y.com".into(), "notes".into(), None,
            "https://notes.sastaspace.com/auth/callback".into()).unwrap();
        let id = db.pending_email().iter().next().unwrap().id;
        let stranger = TestContext::with_sender(Identity::from_hex(
            "3333333333333333333333333333333333333333333333333333333333333333").unwrap());
        assert!(mark_email_sent(&stranger, id, "msg-1".into()).is_err());
        assert!(mark_email_sent(&owner, id, "msg-1".into()).is_ok());
    }
}
```

(Note: the exact `TestContext`/`TestDb` API depends on the SpacetimeDB version. If these helpers don't exist verbatim, port the assertions to `spacetimedb::test_harness::*` or whatever the installed crate exposes — same intent. Discover the right import via `cargo doc --open --package spacetimedb`.)

- [ ] **Step 3: Build + run tests**

```bash
cd modules/sastaspace
cargo build --target wasm32-unknown-unknown --release
cargo test --target x86_64-unknown-linux-gnu  # tests run on host, not WASM
```

Expected: build succeeds, all 5 new tests pass.

- [ ] **Step 4: Regenerate TS bindings**

```bash
cd modules/sastaspace
spacetime publish --project-path . --server local sastaspace
spacetime generate --lang typescript --out-dir ../../packages/stdb-bindings/src --project-path .
```

Expected: `packages/stdb-bindings/src/` shows new exports `request_magic_link`, `verify_token`, `mark_email_sent`, `mark_email_failed`, `pending_email_table`. Diff with `git diff packages/stdb-bindings/`.

- [ ] **Step 5: Commit**

```bash
git add modules/sastaspace/src/lib.rs packages/stdb-bindings/
git commit -m "$(cat <<'EOF'
feat(stdb): pending_email table + verify_token + mailer reducers

Phase 1 W1. Adds the table and 4 reducers the auth-mailer worker needs.
Includes Rust tests for happy path + token re-use + owner-only enforcement.
TS bindings regenerated.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Implement `auth-mailer.ts` worker agent

**Files:**
- Modify: `workers/src/agents/auth-mailer.ts` (replace stub with real impl)
- Create: `workers/src/agents/auth-mailer.test.ts`
- Modify: `workers/src/shared/stdb.ts` (flesh out the connection — first agent to need it)

- [ ] **Step 1: Implement `workers/src/shared/stdb.ts`**

Replace the stub written in Phase 0 Task 5 Step 6 with the real connection wiring:

```typescript
import { DbConnection, type DbConnectionImpl } from "../../node_modules/@sastaspace/stdb-bindings/dist/index.js";
// ↑ Path depends on how stdb-bindings is exposed; if it's a workspace alias,
// `import { DbConnection } from "@sastaspace/stdb-bindings"` works.

export interface StdbConn {
  connection: DbConnectionImpl;
  callReducer(name: string, ...args: unknown[]): Promise<void>;
  subscribe(query: string, onRow: (row: unknown, op: "insert" | "update" | "delete") => void): Promise<void>;
  close(): Promise<void>;
}

export async function connect(url: string, module: string, token: string): Promise<StdbConn> {
  const conn = await new Promise<DbConnectionImpl>((resolve, reject) => {
    const c = DbConnection.builder()
      .withUri(url.replace(/^http/, "ws"))
      .withModuleName(module)
      .withToken(token)
      .onConnect(() => resolve(c.connection))
      .onConnectError((_ctx, err) => reject(err))
      .build();
  });
  return {
    connection: conn,
    async callReducer(name, ...args) {
      // The generated bindings expose typed reducer wrappers; this raw path
      // is a fallback for ad-hoc calls in tests.
      const r = (conn.reducers as Record<string, (...a: unknown[]) => void>)[name];
      if (!r) throw new Error(`unknown reducer ${name}`);
      r(...args);
    },
    async subscribe(query, onRow) {
      conn.subscriptionBuilder().subscribe([query]);
      // Wire row events from the typed table accessors. Each agent does this
      // through the typed bindings rather than this raw subscribe; this string
      // overload is here for completeness.
      void onRow;
    },
    async close() {
      conn.disconnect();
    },
  };
}
```

(The exact API surface of `@clockworklabs/spacetimedb-sdk` evolves; check `packages/stdb-bindings/src/index.ts` after Task 1 Step 4 regenerated it to see the actual exported types and adapt this wrapper. The shape above is correct as of the spec date.)

- [ ] **Step 2: Implement `workers/src/agents/auth-mailer.ts`**

```typescript
import { Resend } from "resend";
import { env } from "../shared/env.js";
import type { StdbConn } from "../shared/stdb.js";

const log = (level: string, msg: string, extra?: unknown) =>
  console.log(JSON.stringify({ ts: new Date().toISOString(), agent: "auth-mailer", level, msg, extra }));

export async function start(db: StdbConn): Promise<() => Promise<void>> {
  if (!env.RESEND_API_KEY) {
    throw new Error("auth-mailer enabled but RESEND_API_KEY missing");
  }
  const resend = new Resend(env.RESEND_API_KEY);

  const conn = db.connection;
  conn.subscriptionBuilder().subscribe(["SELECT * FROM pending_email WHERE status = 'queued'"]);

  const inFlight = new Set<bigint>();

  const handleRow = async (row: { id: bigint; to_email: string; subject: string; body_html: string; body_text: string }) => {
    if (inFlight.has(row.id)) return;
    inFlight.add(row.id);
    try {
      const sendResult = await resend.emails.send({
        from: env.RESEND_FROM,
        to: [row.to_email],
        subject: row.subject,
        html: row.body_html,
        text: row.body_text,
      });
      if (sendResult.error) {
        log("warn", "resend rejected", { id: row.id.toString(), error: sendResult.error });
        conn.reducers.markEmailFailed(row.id, JSON.stringify(sendResult.error).slice(0, 400));
      } else {
        log("info", "email sent", { id: row.id.toString(), msg_id: sendResult.data?.id });
        conn.reducers.markEmailSent(row.id, sendResult.data?.id ?? "unknown");
      }
    } catch (e) {
      log("error", "resend threw", { id: row.id.toString(), error: String(e) });
      conn.reducers.markEmailFailed(row.id, String(e).slice(0, 400));
    } finally {
      inFlight.delete(row.id);
    }
  };

  conn.db.pendingEmail.onInsert((_ctx, row) => {
    if (row.status === "queued") void handleRow(row);
  });

  // Drain anything that was queued before subscription wiring.
  for (const row of conn.db.pendingEmail.iter()) {
    if (row.status === "queued") void handleRow(row);
  }

  log("info", "auth-mailer started");
  return async () => {
    log("info", "auth-mailer stopping");
  };
}
```

(`conn.reducers.markEmailSent` / `markEmailFailed` and `conn.db.pendingEmail` are camelCased generated accessors per `spacetime generate --lang typescript`. If the casing differs, follow what the regenerated bindings expose.)

- [ ] **Step 3: Write Vitest spec `workers/src/agents/auth-mailer.test.ts`**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("resend", () => ({
  Resend: vi.fn().mockImplementation(() => ({
    emails: { send: vi.fn().mockResolvedValue({ data: { id: "msg-fake" }, error: null }) },
  })),
}));

vi.mock("../shared/env.js", () => ({
  env: {
    RESEND_API_KEY: "re_fake",
    RESEND_FROM: "test@sastaspace.com",
  },
}));

const fakeRow = {
  id: 1n,
  to_email: "x@y.com",
  subject: "s",
  body_html: "<p>h</p>",
  body_text: "h",
  status: "queued",
};

describe("auth-mailer", () => {
  let markEmailSent: ReturnType<typeof vi.fn>;
  let markEmailFailed: ReturnType<typeof vi.fn>;
  let onInsert: (ctx: unknown, row: typeof fakeRow) => void;

  beforeEach(() => {
    vi.clearAllMocks();
    markEmailSent = vi.fn();
    markEmailFailed = vi.fn();
  });

  const fakeDb = () => ({
    connection: {
      subscriptionBuilder: () => ({ subscribe: vi.fn() }),
      reducers: { markEmailSent, markEmailFailed },
      db: {
        pendingEmail: {
          onInsert: (cb: typeof onInsert) => { onInsert = cb; },
          iter: () => [fakeRow],
        },
      },
    },
    callReducer: vi.fn(),
    subscribe: vi.fn(),
    close: vi.fn(),
  } as unknown as Parameters<typeof import("./auth-mailer.js").start>[0]);

  it("happy path: drain queued + mark sent", async () => {
    const { start } = await import("./auth-mailer.js");
    const stop = await start(fakeDb());
    await new Promise((r) => setTimeout(r, 20));  // let async send settle
    expect(markEmailSent).toHaveBeenCalledWith(1n, "msg-fake");
    await stop();
  });

  it("failure: marks failed when resend errors", async () => {
    const { Resend } = await import("resend");
    (Resend as unknown as ReturnType<typeof vi.fn>).mockImplementationOnce(() => ({
      emails: { send: vi.fn().mockRejectedValue(new Error("boom")) },
    }));
    const { start } = await import("./auth-mailer.js");
    const stop = await start(fakeDb());
    await new Promise((r) => setTimeout(r, 20));
    expect(markEmailFailed).toHaveBeenCalled();
    expect(markEmailFailed.mock.calls[0][1]).toContain("boom");
    await stop();
  });
});
```

- [ ] **Step 4: Run tests**

```bash
cd workers && pnpm test
```

Expected: both auth-mailer tests pass.

- [ ] **Step 5: Lint**

```bash
cd workers && pnpm lint
```

Expected: clean.

- [ ] **Step 6: Smoke test against local STDB**

```bash
# In one terminal:
cd workers && WORKER_AUTH_MAILER_ENABLED=true STDB_TOKEN=$(spacetime login show --token) RESEND_API_KEY=test_dummy pnpm dev
# In another:
spacetime call --server local sastaspace request_magic_link \
  '["smoketest@example.com", "notes", null, "https://notes.sastaspace.com/auth/callback"]'
```

Expected: worker logs show `pending_email` row arrived and Resend was called (will fail with `test_dummy` key — that's fine, it proves the path). Worker should call `mark_email_failed` and the row's `status` flips to `failed`. Verify:
```bash
spacetime sql sastaspace "SELECT id, to_email, status, error FROM pending_email"
```

- [ ] **Step 7: Commit**

```bash
git add workers/src/
git commit -m "$(cat <<'EOF'
feat(workers): auth-mailer agent + STDB connection wiring

Phase 1 W1 worker. Subscribes pending_email queued rows, calls Resend,
marks sent/failed. Vitest covers happy + failure path. Smoke-tested
against local stdb.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## W1 acceptance checklist

- [ ] `cargo test` in `modules/sastaspace/` passes all 5 new auth_mailer_tests
- [ ] `pnpm test` in `workers/` passes both auth-mailer specs
- [ ] `spacetime publish` succeeds; bindings regenerated and committed
- [ ] Local smoke test: `request_magic_link` reducer call results in a `pending_email` row that the worker drains within 5 seconds
- [ ] `WORKER_AUTH_MAILER_ENABLED=false` (default in compose) — worker idles, Python `services/auth/` keeps handling auth flows on prod

When all checked: W1 is done. Frontend rewire to use these reducers happens in Phase 2 F1 (notes) and F2 (typewars).

---

## Self-review

**Spec coverage:** spec calls for `pending_email` table ✅, `request_magic_link` reducer ✅, `verify_token` (atomic) reducer ✅, `mark_email_sent`/`mark_email_failed` ✅, auth-mailer worker ✅. All covered. ✅

**Placeholder scan:** Test harness API note in Task 1 Step 2 acknowledges version drift — engineer can adapt. STDB SDK shape note in Task 2 Step 1 same. No "TBD" survives. ✅

**Type consistency:** Reducer args in Rust signatures match JS calls in worker (id: u64 ↔ id: bigint, status strings match). Generated bindings will enforce this — if drift, the binding regen step in Task 1 Step 4 catches it before the worker compiles. ✅
