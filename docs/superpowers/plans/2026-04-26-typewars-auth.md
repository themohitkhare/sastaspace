# TypeWars Auth (Guest → Verified) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional sign-in tier on top of the live TypeWars game so anyone can play as a "faceless" guest, then optionally claim their progress with an email-based magic link to gain a persistent identity, an initials-disc avatar with a verified pip, and a profile.

**Architecture:** A single `Player` row gains a new `email: Option<String>` field. A new `claim_progress` reducer rekeys / merges the row when a guest signs in. The frontend reuses the existing `services/auth/` magic-link service via a new `/auth/callback` route on `typewars.sastaspace.com`. A new shared package `@sastaspace/auth-ui` lifts the existing notes sign-in modal so both apps share it.

**Tech Stack:** Rust 2021 (`game/`), SpacetimeDB 2.1 (existing module on `stdb.sastaspace.com`), Next.js 16 / React 19 / TypeScript (`apps/typewars`, `apps/notes`), the existing FastAPI auth service at `services/auth/`, pnpm workspaces.

**Spec:** `docs/superpowers/specs/2026-04-26-typewars-auth-design.md`

---

## File map

| File | Change | Responsibility |
|------|--------|----------------|
| `game/src/player.rs` | Modify | Add `email: Option<String>` field; add username-uniqueness check; add pure `plan_claim` helper; add `claim_progress` reducer. |
| `infra/docker-compose.yml` | Modify | Add `TYPEWARS_CALLBACK` env var to the `auth` service; add `https://typewars.sastaspace.com` to `ALLOWED_ORIGINS`. |
| `packages/auth-ui/package.json` | Create | New shared package wrapping the magic-link sign-in UI. |
| `packages/auth-ui/src/index.ts` | Create | Re-export `SignInModal`. |
| `packages/auth-ui/src/SignInModal.tsx` | Create | Lifted from `apps/notes/src/components/AuthMenu.tsx`. |
| `apps/notes/src/components/AuthMenu.tsx` | Modify | Use `<SignInModal>` from `@sastaspace/auth-ui`. |
| `apps/typewars/src/components/Avatar.tsx` | Create | Initials disc, legion color background, optional verified pip. |
| `apps/typewars/src/components/ProfileModal.tsx` | Create | Stat card opened from any callsign click. |
| `apps/typewars/src/components/SignInTrigger.tsx` | Create | Topbar button that opens `<SignInModal>`. |
| `apps/typewars/src/app/auth/callback/page.tsx` | Create | Magic-link callback handler: stores JWT, calls `claim_progress`, navigates home. |
| `apps/typewars/src/components/MapWarMap.tsx` | Modify | Render `SignInTrigger` for guests, `Avatar` pill for verified players. |
| `apps/typewars/src/components/Battle.tsx` | Modify | Render `Avatar` next to back button. |
| `apps/typewars/src/components/LiberatedSplash.tsx` | Modify | (No avatars in MVP — splash uses legion damage breakdown, not contributors.) |
| `apps/typewars/src/components/Leaderboard.tsx` | Modify | Render `Avatar` per row; clicking a row opens `ProfileModal`. |
| `apps/typewars/src/components/App.tsx` | Modify | Wire `ProfileModal` open/close state. |
| `apps/typewars/package.json` | Modify | Depend on `@sastaspace/auth-ui`. |
| `apps/notes/package.json` | Modify | Depend on `@sastaspace/auth-ui`. |
| `apps/typewars/src/styles/typewars.css` | Modify | Add `.avatar` and `.avatar-pip` classes. |

---

## Task 1: Player schema — add email field + username uniqueness

**Files:**
- Modify: `game/src/player.rs`

- [ ] **Step 1: Read the current Player struct + register_player to know exact lines**

Run: `grep -n "pub struct Player\|pub fn register_player\|pub fn validate_registration" /Users/mkhare/Development/sastaspace/game/src/player.rs`

- [ ] **Step 2: Write a failing unit test for username uniqueness**

Append to the `#[cfg(test)] mod tests` block in `game/src/player.rs`:

```rust
#[test]
fn validate_registration_rejects_duplicate_username_case_insensitive() {
    // existing usernames are passed in lowercased form
    let existing = vec!["ash_q".to_string(), "smoketest".to_string()];
    assert!(validate_registration("ASH_Q", 0, &existing).is_err());
    assert!(validate_registration("Smoketest", 1, &existing).is_err());
    assert!(validate_registration("new_recruit", 2, &existing).is_ok());
}
```

- [ ] **Step 3: Run the test — should fail because validate_registration takes 2 args today**

Run: `cd /Users/mkhare/Development/sastaspace/game && cargo test player::tests::validate_registration_rejects_duplicate 2>&1 | tail -10`

Expected: compile error (signature mismatch).

- [ ] **Step 4: Update validate_registration to take an existing-usernames slice**

Modify the `validate_registration` function in `game/src/player.rs`. Change its signature and add the uniqueness check at the bottom:

```rust
pub fn validate_registration(
    username: &str,
    legion: u8,
    existing_usernames_lower: &[String],
) -> Result<(), String> {
    if username.is_empty() || username.len() > 32 {
        return Err("username must be 1-32 chars".into());
    }
    if legion > 4 {
        return Err("invalid legion".into());
    }
    let lower = username.to_lowercase();
    if existing_usernames_lower.iter().any(|u| u == &lower) {
        return Err("username taken".into());
    }
    Ok(())
}
```

- [ ] **Step 5: Update the existing tests to pass `&[]`**

For every existing call to `validate_registration(...)` in the same `mod tests` block, add a third argument `&[]`. Run `grep -n "validate_registration(" game/src/player.rs` to find them.

- [ ] **Step 6: Add the email field to the Player struct**

```rust
#[table(accessor = player, public)]
pub struct Player {
    #[primary_key]
    pub identity: Identity,
    pub username: String,
    pub legion: u8,
    pub total_damage: u64,
    pub season_damage: u64,
    pub best_wpm: u32,
    pub joined_at: Timestamp,
    pub email: Option<String>,
}
```

- [ ] **Step 7: Update `register_player` to compute existing-usernames and set email=None**

Inside `register_player`, before validating, gather usernames:

```rust
let existing: Vec<String> = ctx.db.player()
    .iter()
    .map(|p| p.username.to_lowercase())
    .collect();
validate_registration(&username, legion, &existing)?;
```

When constructing the new `Player` row, add `email: None,`.

- [ ] **Step 8: Run all tests — should pass**

Run: `cargo test 2>&1 | tail -10`

Expected: all tests pass (the existing `validate_registration_*` tests now pass `&[]`; the new uniqueness test passes).

- [ ] **Step 9: Commit**

```bash
git add game/src/player.rs
git commit -m "feat(typewars): add Player.email field and case-insensitive username uniqueness"
```

---

## Task 2: Pure `plan_claim` helper for the four claim cases

**Files:**
- Modify: `game/src/player.rs`

- [ ] **Step 1: Append the pure helper at the bottom of player.rs (above the test mod)**

```rust
/// Result of planning a claim_progress reducer call. Pure: no DB access.
#[derive(Debug, PartialEq)]
pub enum ClaimAction {
    /// Caller has a guest row and no email row yet — rekey the guest row.
    Rekey { delete_id: Identity, insert: Player },
    /// Caller already has a verified row and brought guest stats — merge.
    Merge { delete_id: Identity, update: Player },
    /// Caller has a verified row and no prior guest play — just stamp email.
    StampEmail { update: Player },
    /// Caller has nothing on either side — nothing to do.
    Noop,
}

pub fn plan_claim(
    guest: Option<Player>,
    existing: Option<Player>,
    new_id: Identity,
    email: String,
) -> ClaimAction {
    match (guest, existing) {
        (Some(g), None) => {
            let mut row = g.clone();
            row.identity = new_id;
            row.email = Some(email);
            ClaimAction::Rekey { delete_id: g.identity, insert: row }
        }
        (Some(g), Some(mut e)) => {
            e.total_damage = e.total_damage.saturating_add(g.total_damage);
            e.season_damage = e.season_damage.saturating_add(g.season_damage);
            e.best_wpm = e.best_wpm.max(g.best_wpm);
            e.email = Some(email);
            ClaimAction::Merge { delete_id: g.identity, update: e }
        }
        (None, Some(mut e)) => {
            e.email = Some(email);
            ClaimAction::StampEmail { update: e }
        }
        (None, None) => ClaimAction::Noop,
    }
}
```

`Player` needs `Clone` for the rekey arm. Add `#[derive(Clone)]` to the struct (above `#[table(...)]`).

- [ ] **Step 2: Add 4 unit tests, one per arm**

Append to the `#[cfg(test)] mod tests` block:

```rust
fn mk_player(id_byte: u8, username: &str, legion: u8, total: u64, season: u64, wpm: u32, email: Option<&str>) -> Player {
    let mut bytes = [0u8; 32];
    bytes[0] = id_byte;
    Player {
        identity: Identity::from_byte_array(bytes),
        username: username.into(),
        legion,
        total_damage: total,
        season_damage: season,
        best_wpm: wpm,
        joined_at: Timestamp::from_micros_since_unix_epoch(0),
        email: email.map(Into::into),
    }
}

#[test]
fn plan_claim_rekey_when_guest_has_row_and_email_does_not() {
    let guest = mk_player(0x01, "ash_q", 0, 1000, 500, 80, None);
    let new_id = Identity::from_byte_array([0x02; 32]);
    let action = plan_claim(Some(guest.clone()), None, new_id, "a@b.com".into());
    match action {
        ClaimAction::Rekey { delete_id, insert } => {
            assert_eq!(delete_id, guest.identity);
            assert_eq!(insert.identity, new_id);
            assert_eq!(insert.email, Some("a@b.com".into()));
            assert_eq!(insert.total_damage, 1000);
            assert_eq!(insert.username, "ash_q");
        }
        other => panic!("expected Rekey, got {:?}", other),
    }
}

#[test]
fn plan_claim_merge_sums_damages_takes_max_wpm_keeps_email_row_legion() {
    let guest = mk_player(0x01, "guest_one", 3 /* surge */, 1000, 500, 80, None);
    let existing = mk_player(0x02, "real_name", 0 /* ashborn */, 5000, 2000, 100, Some("a@b.com"));
    let action = plan_claim(Some(guest.clone()), Some(existing.clone()), existing.identity, "a@b.com".into());
    match action {
        ClaimAction::Merge { delete_id, update } => {
            assert_eq!(delete_id, guest.identity);
            assert_eq!(update.identity, existing.identity);
            assert_eq!(update.username, "real_name", "email row's username should win");
            assert_eq!(update.legion, 0, "email row's legion should win");
            assert_eq!(update.total_damage, 6000);
            assert_eq!(update.season_damage, 2500);
            assert_eq!(update.best_wpm, 100);
            assert_eq!(update.email, Some("a@b.com".into()));
        }
        other => panic!("expected Merge, got {:?}", other),
    }
}

#[test]
fn plan_claim_stamp_email_when_only_existing() {
    let existing = mk_player(0x02, "real_name", 0, 5000, 2000, 100, None);
    let action = plan_claim(None, Some(existing.clone()), existing.identity, "a@b.com".into());
    match action {
        ClaimAction::StampEmail { update } => {
            assert_eq!(update.email, Some("a@b.com".into()));
            assert_eq!(update.total_damage, 5000); // unchanged
        }
        other => panic!("expected StampEmail, got {:?}", other),
    }
}

#[test]
fn plan_claim_noop_when_neither_exists() {
    let new_id = Identity::from_byte_array([0x09; 32]);
    let action = plan_claim(None, None, new_id, "a@b.com".into());
    assert_eq!(action, ClaimAction::Noop);
}
```

- [ ] **Step 3: Run the tests — all 4 should pass**

Run: `cargo test plan_claim 2>&1 | tail -10`

Expected: 4 passed.

- [ ] **Step 4: Run full test suite — nothing else broken**

Run: `cargo test 2>&1 | tail -10`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add game/src/player.rs
git commit -m "feat(typewars): plan_claim pure helper covering all four guest/email arms"
```

---

## Task 3: `claim_progress` reducer (thin wrapper around plan_claim)

**Files:**
- Modify: `game/src/player.rs`

- [ ] **Step 1: Append the reducer near the bottom of player.rs (before the test mod)**

```rust
#[reducer]
pub fn claim_progress(
    ctx: &ReducerContext,
    prev_identity: Identity,
    email: String,
) -> Result<(), String> {
    if email.is_empty() || email.len() > 254 {
        return Err("invalid email".into());
    }
    let me = ctx.sender;
    let guest = ctx.db.player().identity().find(&prev_identity);
    let existing = ctx.db.player().identity().find(&me);
    match plan_claim(guest, existing, me, email) {
        ClaimAction::Rekey { delete_id, insert } => {
            ctx.db.player().identity().delete(&delete_id);
            ctx.db.player().insert(insert);
        }
        ClaimAction::Merge { delete_id, update } => {
            ctx.db.player().identity().delete(&delete_id);
            ctx.db.player().identity().update(update);
        }
        ClaimAction::StampEmail { update } => {
            ctx.db.player().identity().update(update);
        }
        ClaimAction::Noop => {}
    }
    Ok(())
}
```

Make sure `reducer` and `ReducerContext` are already imported at the top of player.rs (they are — `register_player` uses them). Add `Identity` to the imports if it isn't there.

- [ ] **Step 2: Verify it compiles**

Run: `cargo check 2>&1 | tail -10`

Expected: clean (no errors). Pre-existing dead-code warning on `LEGION_NAMES` is OK.

- [ ] **Step 3: Run all tests**

Run: `cargo test 2>&1 | tail -10`

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add game/src/player.rs
git commit -m "feat(typewars): claim_progress reducer wrapping plan_claim"
```

---

## Task 4: Backend deploy + bindings regen + smoke

**Files:** none (CLI only)

- [ ] **Step 1: Republish typewars module**

```bash
cd /Users/mkhare/Development/sastaspace
PATH=$HOME/.cargo/bin:$PATH spacetime publish --server prod -p game typewars -y 2>&1 | tail -10
```

Expected: `Updated database`. If publish complains about a breaking change ("incompatible schema"), retry with `--break-clients` (the existing two prod rows will gain `email = None` automatically since `Option<String>` defaults to `None`):

```bash
PATH=$HOME/.cargo/bin:$PATH spacetime publish --server prod -p game typewars -y --break-clients
```

- [ ] **Step 2: Verify schema migration happened**

```bash
spacetime sql --server prod typewars "SELECT identity, username, legion, email FROM player" 2>&1 | tail -10
```

Expected: 2 rows (`smoketest`, `e2e_recruit`), both with `email` shown as `null`/empty.

- [ ] **Step 3: Regenerate TypeScript bindings**

```bash
PATH=$HOME/.cargo/bin:$PATH pnpm typewars:bindings 2>&1 | tail -10
```

Expected: files regenerated under `packages/typewars-bindings/src/generated/`. Check that `player_table.ts` now has `email: __t.option(__t.string())` (or similar nullable form) and that a new `claim_progress_reducer.ts` exists.

- [ ] **Step 4: Smoke-test the reducer over the wire**

Use a fake "guest" identity (the `e2e_recruit` row from earlier E2E):

```bash
# Look at the existing identity strings
spacetime sql --server prod typewars "SELECT identity FROM player" 2>&1 | tail -10
# Observe the typewars module accepts the new reducer
spacetime call --server prod typewars claim_progress 0x0000000000000000000000000000000000000000000000000000000000000000 'manual@test' 2>&1 | tail -5
```

Expected: no error. `claim_progress` with an unknown `prev_identity` and the caller (CLI identity) having no Player row falls into the `Noop` arm. (Don't claim a real player's row in the smoke test.)

- [ ] **Step 5: Commit the regenerated bindings**

```bash
git add packages/typewars-bindings/src/generated
git commit -m "chore(typewars): regenerate bindings for email field + claim_progress reducer"
```

---

## Task 5: Auth service config — add typewars callback + origin

**Files:**
- Modify: `infra/docker-compose.yml`

- [ ] **Step 1: Find the existing auth service block**

Run: `grep -n "ALLOWED_ORIGINS\|NOTES_CALLBACK\|ADMIN_CALLBACK" /Users/mkhare/Development/sastaspace/infra/docker-compose.yml`

- [ ] **Step 2: Add TYPEWARS_CALLBACK and extend ALLOWED_ORIGINS**

Inside the `auth:` service's `environment:` list, after `ADMIN_CALLBACK=...`, append:

```yaml
      - TYPEWARS_CALLBACK=https://typewars.sastaspace.com/auth/callback
```

And in the `ALLOWED_ORIGINS` line, append `,https://typewars.sastaspace.com`:

```yaml
      - ALLOWED_ORIGINS=https://sastaspace.com,https://www.sastaspace.com,https://notes.sastaspace.com,https://admin.sastaspace.com,https://typewars.sastaspace.com
```

- [ ] **Step 3: Read services/auth/src/sastaspace_auth/main.py to confirm how the callback is selected**

Run: `grep -n "callback\|TYPEWARS\|app =\|app:" /Users/mkhare/Development/sastaspace/services/auth/src/sastaspace_auth/main.py | head -30`

If the `request_magic_link` endpoint already accepts an arbitrary `callback` URL from the request body (whitelist-checked against the env), no service code change is needed. **If the endpoint maps `app=notes` / `app=admin` to env vars**, add:

```python
TYPEWARS_CALLBACK = env("TYPEWARS_CALLBACK", "https://typewars.sastaspace.com/auth/callback", required=False)
# ...
APP_CALLBACKS = {
    "notes": NOTES_CALLBACK,
    "admin": ADMIN_CALLBACK,
    "typewars": TYPEWARS_CALLBACK,
}
```

(Adapt to the existing dispatch shape — don't blindly paste.)

- [ ] **Step 4: Commit infra change**

```bash
git add infra/docker-compose.yml services/auth
git commit -m "feat(auth): add typewars.sastaspace.com callback + origin"
```

The CI's `agents` job will redeploy the auth container on push (its diff detector watches `infra/docker-compose`).

- [ ] **Step 5: Verify CORS preflight works after CI redeploys**

After CI completes:

```bash
curl -sI -X OPTIONS \
  -H 'Origin: https://typewars.sastaspace.com' \
  -H 'Access-Control-Request-Method: POST' \
  https://auth.sastaspace.com/auth/request 2>&1 | grep -i 'access-control'
```

Expected: `access-control-allow-origin: https://typewars.sastaspace.com`.

---

## Task 6: Shared `@sastaspace/auth-ui` package

**Files:**
- Create: `packages/auth-ui/package.json`
- Create: `packages/auth-ui/src/index.ts`
- Create: `packages/auth-ui/src/SignInModal.tsx`
- Create: `packages/auth-ui/src/SignInModal.module.css`

- [ ] **Step 1: Read the existing notes AuthMenu modal to know what to lift**

Run: `cat /Users/mkhare/Development/sastaspace/apps/notes/src/components/AuthMenu.tsx`

Identify: (a) the email input + submit button rendering, (b) the POST to `https://auth.sastaspace.com/auth/request`, (c) the success / error state handling. The lifted `SignInModal` should match the same UX.

- [ ] **Step 2: Create the package manifest**

Write `packages/auth-ui/package.json`:

```json
{
  "name": "@sastaspace/auth-ui",
  "version": "0.1.0",
  "private": true,
  "description": "Shared sign-in modal that drives the magic-link flow on services/auth.",
  "type": "module",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  },
  "files": [
    "src"
  ],
  "peerDependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  }
}
```

- [ ] **Step 3: Create the index re-export**

Write `packages/auth-ui/src/index.ts`:

```ts
export { SignInModal } from "./SignInModal";
export type { SignInModalProps } from "./SignInModal";
```

- [ ] **Step 4: Create the modal component**

Write `packages/auth-ui/src/SignInModal.tsx`. Use the AuthMenu modal logic verbatim — same fetch URL, same body shape — adjusted to take `app: 'notes' | 'typewars'` and `callback: string` as props so each consumer can target itself:

```tsx
"use client";
import { useState, type FormEvent } from "react";

export interface SignInModalProps {
  /** App identifier sent to the auth service so the right callback is used. */
  app: string;
  /** Public URL the auth service should redirect to after verification. */
  callback: string;
  /** Auth service base URL. Defaults to env or production. */
  authBase?: string;
  open: boolean;
  onClose: () => void;
}

export function SignInModal({ app, callback, authBase, open, onClose }: SignInModalProps) {
  const base = authBase ?? "https://auth.sastaspace.com";
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setStatus("sending");
    setError(null);
    try {
      const r = await fetch(`${base}/auth/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, app, callback }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setStatus("sent");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "request failed");
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2 className="ss-h3">Sign in</h2>
          <button className="link-btn" onClick={onClose}>close</button>
        </div>
        {status === "sent" ? (
          <p className="ss-body">Check your inbox — magic link sent to <strong>{email}</strong>. Open the link in this same browser to keep your guest progress.</p>
        ) : (
          <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p className="ss-small" style={{ color: "var(--brand-muted)" }}>
              We&apos;ll email you a one-time link. No password.
            </p>
            <input
              className="callsign-input"
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
            />
            <button className="enlist-btn" type="submit" disabled={status === "sending"}>
              {status === "sending" ? "sending…" : "send magic link →"}
            </button>
            {error && <p className="ss-small" style={{ color: "var(--brand-sasta-text)" }}>{error}</p>}
          </form>
        )}
      </div>
    </div>
  );
}
```

(Reuse existing CSS classes `.modal`, `.modal-backdrop`, `.modal-head`, `.callsign-input`, `.enlist-btn`, `.link-btn`, `.ss-body`, `.ss-small`, `.ss-h3` — these exist in both notes and typewars.)

- [ ] **Step 5: Install workspace dep + verify build**

```bash
cd /Users/mkhare/Development/sastaspace
pnpm install 2>&1 | tail -5
```

Expected: workspace recognises new `@sastaspace/auth-ui` package.

- [ ] **Step 6: Commit**

```bash
git add packages/auth-ui pnpm-lock.yaml
git commit -m "feat(auth-ui): shared SignInModal package"
```

---

## Task 7: Migrate `apps/notes` to use the shared SignInModal

**Files:**
- Modify: `apps/notes/package.json`
- Modify: `apps/notes/src/components/AuthMenu.tsx`

- [ ] **Step 1: Add the workspace dependency**

In `apps/notes/package.json`, under `dependencies`, add `"@sastaspace/auth-ui": "workspace:*",` next to the existing design-tokens entry.

- [ ] **Step 2: Replace the inline modal markup with the shared component**

Edit `apps/notes/src/components/AuthMenu.tsx`. Identify the part of `AuthMenu` that renders the sign-in modal (the email input + submit + sent confirmation). Replace it with:

```tsx
import { SignInModal } from "@sastaspace/auth-ui";
// inside the AuthMenu component:
<SignInModal
  app="notes"
  callback="https://notes.sastaspace.com/auth/callback"
  open={signInOpen}
  onClose={() => setSignInOpen(false)}
/>
```

Keep all *other* AuthMenu logic (session detection, sign-out, user pill) untouched — only the modal sub-tree moves into the shared package.

- [ ] **Step 3: Install + typecheck + build**

```bash
cd /Users/mkhare/Development/sastaspace
pnpm install 2>&1 | tail -3
pnpm --filter @sastaspace/notes typecheck 2>&1 | tail -5
pnpm --filter @sastaspace/notes build 2>&1 | tail -5
```

Expected: all clean.

- [ ] **Step 4: Spot-check by running notes dev**

```bash
pnpm --filter @sastaspace/notes dev &
sleep 5
curl -sI http://127.0.0.1:3001/ 2>&1 | head -3
pkill -f 'notes.*next dev' 2>/dev/null
```

Expected: HTTP 200 on the dev server.

- [ ] **Step 5: Commit**

```bash
git add apps/notes pnpm-lock.yaml
git commit -m "refactor(notes): migrate AuthMenu modal to shared @sastaspace/auth-ui"
```

---

## Task 8: `<Avatar />` component

**Files:**
- Create: `apps/typewars/src/components/Avatar.tsx`
- Modify: `apps/typewars/src/styles/typewars.css`

- [ ] **Step 1: Create the Avatar component**

Write `apps/typewars/src/components/Avatar.tsx`:

```tsx
"use client";
import type { LegionId } from "@/types";
import { LEGION_INFO } from "@/lib/legions";

export interface AvatarProps {
  callsign: string;
  legion: LegionId;
  verified: boolean;
  size?: number;
}

export function Avatar({ callsign, legion, verified, size = 24 }: AvatarProps) {
  const letters = (callsign.match(/[A-Za-z]/g)?.join("") ?? callsign)
    .slice(0, 2)
    .toUpperCase();
  const color = LEGION_INFO[legion].color;
  const fontSize = Math.max(10, Math.round(size * 0.42));
  return (
    <span
      className="avatar"
      style={{
        width: size,
        height: size,
        background: color,
        fontSize,
        // wrapper pip uses absolute pos
        position: "relative",
      }}
      aria-label={callsign}
    >
      {letters || "?"}
      {verified && <span className="avatar-pip" />}
    </span>
  );
}
```

- [ ] **Step 2: Add the avatar CSS classes**

Append to `apps/typewars/src/styles/typewars.css`:

```css
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  border: 1px solid var(--brand-dust-40);
  color: #fff;
  font-family: var(--font-mono);
  font-weight: 500;
  letter-spacing: 0.04em;
  flex-shrink: 0;
  user-select: none;
}
.avatar-pip {
  position: absolute;
  bottom: -1px;
  right: -1px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand-sasta);
  border: 1px solid var(--brand-paper);
}
```

- [ ] **Step 3: Verify it builds**

```bash
cd /Users/mkhare/Development/sastaspace/apps/typewars
pnpm typecheck 2>&1 | tail -3
pnpm build 2>&1 | tail -3
```

Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add apps/typewars/src/components/Avatar.tsx apps/typewars/src/styles/typewars.css
git commit -m "feat(typewars-fe): Avatar component (initials + verified pip)"
```

---

## Task 9: `<ProfileModal />` component

**Files:**
- Create: `apps/typewars/src/components/ProfileModal.tsx`

- [ ] **Step 1: Create the modal**

Write `apps/typewars/src/components/ProfileModal.tsx`:

```tsx
"use client";
import { useMemo } from "react";
import { useTable } from "spacetimedb/react";
import { tables } from "@sastaspace/typewars-bindings";
import type { LegionId } from "@/types";
import { LEGION_INFO } from "@/lib/legions";
import { Avatar } from "./Avatar";

export interface ProfileModalProps {
  /** Callsign of the player whose profile to display. */
  username: string;
  onClose: () => void;
}

function timeAgo(joinedMs: number): string {
  const sec = Math.max(1, Math.floor((Date.now() - joinedMs) / 1000));
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}

export function ProfileModal({ username, onClose }: ProfileModalProps) {
  const [allPlayers] = useTable(tables.player);
  const [allRegions] = useTable(tables.region);

  const player = useMemo(
    () => allPlayers.find((p) => p.username === username),
    [allPlayers, username],
  );

  if (!player) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <p className="ss-body">Player not found.</p>
          <button className="link-btn" onClick={onClose}>close</button>
        </div>
      </div>
    );
  }

  const legion = player.legion as LegionId;
  const info = LEGION_INFO[legion];
  const verified = player.email != null;
  const joinedMs = Number(player.joinedAt.toMillis());
  const regionsHeld = allRegions.filter((r) => r.controllingLegion === legion).length;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head" style={{ alignItems: "center", gap: 16 }}>
          <Avatar callsign={player.username} legion={legion} verified={verified} size={48} />
          <div style={{ flex: 1 }}>
            <h2 className="ss-h2" style={{ margin: 0 }}>{player.username}</h2>
            <p className="ss-small" style={{ color: "var(--brand-muted)", margin: 0 }}>
              {info.name} · {info.mechanic} · joined {timeAgo(joinedMs)}
              {verified && <span style={{ color: "var(--brand-sasta-text)", marginLeft: 8 }}>✓ verified</span>}
            </p>
          </div>
          <button className="link-btn" onClick={onClose}>close</button>
        </div>
        <div className="personal-grid" style={{ marginTop: 24 }}>
          <div className="hud-stat">
            <span className="hud-label">total dmg</span>
            <span className="hud-val">{Number(player.totalDamage).toLocaleString()}</span>
          </div>
          <div className="hud-stat">
            <span className="hud-label">season dmg</span>
            <span className="hud-val">{Number(player.seasonDamage).toLocaleString()}</span>
          </div>
          <div className="hud-stat">
            <span className="hud-label">best wpm</span>
            <span className="hud-val">{player.bestWpm}</span>
          </div>
          <div className="hud-stat">
            <span className="hud-label">regions held</span>
            <span className="hud-val">{regionsHeld}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build + typecheck**

```bash
cd /Users/mkhare/Development/sastaspace/apps/typewars
pnpm typecheck 2>&1 | tail -3
pnpm build 2>&1 | tail -3
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add apps/typewars/src/components/ProfileModal.tsx
git commit -m "feat(typewars-fe): ProfileModal stat card from player + region subscriptions"
```

---

## Task 10: Magic-link callback page

**Files:**
- Create: `apps/typewars/src/app/auth/callback/page.tsx`

- [ ] **Step 1: Create the route**

Write `apps/typewars/src/app/auth/callback/page.tsx`:

```tsx
"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { DbConnection, reducers } from "@sastaspace/typewars-bindings";
import { STDB_URI, STDB_MODULE } from "@/lib/spacetime";

const TOKEN_KEY = "typewars:auth_token";

export default function AuthCallbackPage() {
  const router = useRouter();
  const params = useSearchParams();
  const [status, setStatus] = useState<"working" | "done" | "error">("working");
  const [message, setMessage] = useState("Completing sign-in…");

  useEffect(() => {
    const jwt = params.get("jwt") ?? params.get("token");
    const email = params.get("email");
    if (!jwt || !email) {
      setStatus("error");
      setMessage("Missing token in callback URL — please request a new magic link.");
      return;
    }

    // Capture the *current* (guest) auth token, if any. The SDK builds an
    // Identity from this when reconnecting; if absent, the guest never had a
    // session on this browser and there's nothing to claim.
    const prevJwt = window.localStorage.getItem(TOKEN_KEY);

    // Build a one-shot connection with the new email-derived JWT.
    const builder = DbConnection.builder()
      .withUri(STDB_URI)
      .withDatabaseName(STDB_MODULE)
      .withToken(jwt)
      .onConnect(async (ctx, identity) => {
        try {
          const meHex = identity.toHexString();
          // Determine prevIdentity by *temporarily* connecting with the guest token
          // and reading its identity. If no prevJwt, there's nothing to claim.
          let prevIdHex = meHex; // fall back to "same identity" → reducer Noop
          if (prevJwt) {
            const probe = await new Promise<string>((resolve, reject) => {
              const p = DbConnection.builder()
                .withUri(STDB_URI)
                .withDatabaseName(STDB_MODULE)
                .withToken(prevJwt)
                .onConnect((_pctx, prevIdentity) => {
                  resolve(prevIdentity.toHexString());
                  p.disconnect();
                })
                .onConnectError((_pctx, err) => reject(err))
                .build();
            }).catch(() => meHex);
            prevIdHex = probe;
          }

          await reducers.claim_progress({
            prev_identity: prevIdHex as unknown as never,
            email,
          });
          window.localStorage.setItem(TOKEN_KEY, jwt);
          setStatus("done");
          setMessage("Signed in. Redirecting…");
          router.replace("/");
        } catch (err) {
          setStatus("error");
          setMessage(err instanceof Error ? err.message : "claim failed");
        }
      })
      .onConnectError((_ctx, err) => {
        setStatus("error");
        setMessage(`Could not connect: ${err.message}`);
      })
      .build();

    return () => {
      try { builder.disconnect(); } catch { /* idempotent */ }
    };
  }, [params, router]);

  return (
    <div className="page" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
      <div style={{ textAlign: "center" }}>
        <p className="ss-eyebrow">~/typewars/auth/callback —</p>
        <p className="ss-body" style={{ marginTop: 8 }}>{message}</p>
        {status === "error" && (
          <button className="enlist-btn" onClick={() => router.replace("/")} style={{ marginTop: 16 }}>
            back to map →
          </button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Confirm reducer accessor name**

Run: `grep -n "export const reducers\|claim_progress\|claimProgress" /Users/mkhare/Development/sastaspace/packages/typewars-bindings/src/generated/index.ts`

The accessor will likely be `reducers.claimProgress` (camelCase, mirroring `registerPlayer`). Adjust the call site in step 1 to use the actual generated name. Likewise, the param shape will be `{ prevIdentity: Identity; email: string }` — pass an `Identity` (use `Identity.fromHexString(...)` from `spacetimedb` if needed), not a raw hex string.

- [ ] **Step 3: Build**

```bash
cd /Users/mkhare/Development/sastaspace/apps/typewars
pnpm typecheck 2>&1 | tail -5
pnpm build 2>&1 | tail -5
```

Expected: clean. The `/auth/callback` route should appear in the build output.

- [ ] **Step 4: Commit**

```bash
git add apps/typewars/src/app/auth/callback
git commit -m "feat(typewars-fe): /auth/callback route — claim_progress on magic-link return"
```

---

## Task 11: Wire SignInTrigger + Avatar into MapWarMap topbar

**Files:**
- Create: `apps/typewars/src/components/SignInTrigger.tsx`
- Modify: `apps/typewars/package.json`
- Modify: `apps/typewars/src/components/MapWarMap.tsx`

- [ ] **Step 1: Add the workspace dependency on @sastaspace/auth-ui**

In `apps/typewars/package.json`, under `dependencies`, add `"@sastaspace/auth-ui": "workspace:*",` next to the existing entries.

Run `pnpm install` from the repo root.

- [ ] **Step 2: Create the trigger component**

Write `apps/typewars/src/components/SignInTrigger.tsx`:

```tsx
"use client";
import { useState } from "react";
import { SignInModal } from "@sastaspace/auth-ui";

export function SignInTrigger() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="link-btn" onClick={() => setOpen(true)}>sign in →</button>
      <SignInModal
        app="typewars"
        callback="https://typewars.sastaspace.com/auth/callback"
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
```

- [ ] **Step 3: Update MapWarMap topbar**

In `apps/typewars/src/components/MapWarMap.tsx`, modify the topbar to:
1. Import `Avatar` and `SignInTrigger`
2. Replace the existing player pill render with: an `<Avatar callsign={player.username} legion={player.legion} verified={!!player.email} size={28} />` followed by a `<span>{player.username} · {LEGION_INFO[player.legion].short}</span>` inside the same pill button, then either `<SignInTrigger />` (if `!player.email`) or nothing (verified players use the avatar disc itself as their visual).

Concrete patch (find the block that renders `.player-pill swap-pill` and adapt):

```tsx
import { Avatar } from "./Avatar";
import { SignInTrigger } from "./SignInTrigger";
// ... inside the topbar render:
<button className="player-pill swap-pill" onClick={onSwapLegion} style={{ borderColor: LEGION_INFO[player.legion].color }}>
  <Avatar callsign={player.username} legion={player.legion} verified={!!player.email} size={20} />
  <span className="ss-mono" style={{ fontSize: 12 }}>{player.username}</span>
  <span className="ss-mono" style={{ fontSize: 11, color: "var(--brand-muted)" }}>· {LEGION_INFO[player.legion].name}</span>
  <span className="ss-mono" style={{ fontSize: 10, color: "var(--brand-muted)", marginLeft: 6 }}>swap ↺</span>
</button>
{!player.email && <SignInTrigger />}
```

- [ ] **Step 4: Update Player type in adapters.ts to expose email**

Open `apps/typewars/src/lib/adapters.ts`. The `toPlayer` adapter needs to surface `email`. Add:

```ts
type PlayerRow = {
  // ...existing fields
  email: string | null;
};

export function toPlayer(row: PlayerRow): Player {
  return {
    // ...existing fields
    email: row.email ?? undefined,
  };
}
```

And in `apps/typewars/src/types/index.ts` add `email?: string;` to the `Player` interface.

- [ ] **Step 5: Build**

```bash
cd /Users/mkhare/Development/sastaspace/apps/typewars
pnpm typecheck 2>&1 | tail -5
pnpm build 2>&1 | tail -5
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add apps/typewars/src/components/SignInTrigger.tsx apps/typewars/src/components/MapWarMap.tsx apps/typewars/src/lib/adapters.ts apps/typewars/src/types/index.ts apps/typewars/package.json pnpm-lock.yaml
git commit -m "feat(typewars-fe): topbar sign-in button + verified avatar in MapWarMap"
```

---

## Task 12: Avatars + ProfileModal in Battle and Leaderboard

**Files:**
- Modify: `apps/typewars/src/components/Battle.tsx`
- Modify: `apps/typewars/src/components/Leaderboard.tsx`
- Modify: `apps/typewars/src/components/App.tsx`

- [ ] **Step 1: Battle header avatar**

In `apps/typewars/src/components/Battle.tsx`, in the `.battle-header-left` div (next to the back button), insert:

```tsx
import { Avatar } from "./Avatar";
// ...
<Avatar callsign={player.username} legion={player.legion} verified={!!player.email} size={20} />
```

- [ ] **Step 2: Leaderboard row avatars + click → ProfileModal**

In `apps/typewars/src/components/Leaderboard.tsx`:

1. Import `Avatar` and accept a new prop `onOpenProfile: (username: string) => void`.
2. In the `.lb-trow` mapping (in the player roster table), prepend an `<Avatar callsign={p.username} legion={p.legion} verified={!!p.email} size={20} />` and wrap the row's clickable area with `onClick={() => onOpenProfile(p.username)}`.
3. Update the `PlayerEntry` type and the rows-mapping `useMemo` to include `email: string | null` (sourced from `p.email`).

```tsx
interface PlayerEntry {
  username: string;
  legion: LegionId;
  seasonDamage: number;
  totalDamage: number;
  bestWpm: number;
  email: string | null;
}
// in useMemo:
.map(p => ({
  username: p.username,
  legion: p.legion as LegionId,
  seasonDamage: Number(p.seasonDamage),
  totalDamage: Number(p.totalDamage),
  bestWpm: p.bestWpm,
  email: p.email ?? null,
}))
```

- [ ] **Step 3: App.tsx wires ProfileModal state**

In `apps/typewars/src/components/App.tsx`:

```tsx
import { ProfileModal } from "./ProfileModal";
// inside App():
const [profileUser, setProfileUser] = useState<string | null>(null);
// pass handler to Leaderboard:
<Leaderboard regions={regions} player={player} onBack={() => setScreen('warmap')} onOpenProfile={setProfileUser} />
// and at the bottom of the JSX (sibling to the screen switch):
{profileUser && <ProfileModal username={profileUser} onClose={() => setProfileUser(null)} />}
```

- [ ] **Step 4: Build**

```bash
cd /Users/mkhare/Development/sastaspace/apps/typewars
pnpm typecheck 2>&1 | tail -5
pnpm build 2>&1 | tail -5
```

Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add apps/typewars/src/components
git commit -m "feat(typewars-fe): avatars in Battle + Leaderboard rows; ProfileModal trigger"
```

---

## Task 13: Push, deploy, Playwright E2E end-to-end verification

**Files:** none (CLI + browser)

- [ ] **Step 1: Push branch to origin/main**

```bash
git push origin main 2>&1 | tail -3
```

- [ ] **Step 2: Wait for CI to deploy typewars**

```bash
sleep 8
RID=$(gh run list --branch main --limit 1 --json databaseId -q '.[0].databaseId')
until [ "$(gh run view $RID --json status -q .status)" = "completed" ]; do
  state=$(gh run view $RID --json jobs --jq '.jobs[] | select(.name=="typewars" or .name=="auth") | "\(.name): \(.status)/\(.conclusion)"' 2>/dev/null)
  echo "[$(date +%H:%M:%S)]"; echo "$state"
  sleep 30
done
gh run view $RID --json conclusion,jobs --jq '{conclusion, typewars: (.jobs[] | select(.name=="typewars") | .conclusion), auth: (.jobs[] | select(.name=="auth") | .conclusion)}'
```

Expected: `typewars: success`, `auth: success`.

- [ ] **Step 3: Verify HTTP**

```bash
curl -sI -L "https://typewars.sastaspace.com/?bust=$(date +%s)" 2>&1 | head -3
```

Expected: HTTP 200.

- [ ] **Step 4: Playwright E2E — guest flow + sign-in flow + claim**

Use the Playwright MCP browser to:

1. Navigate to `https://typewars.sastaspace.com/?bust=auth1`.
2. Snapshot. Confirm console has zero errors.
3. Click on a legion card (e.g. Surge), enter callsign `claim_test_<unix>`, click ENLIST.
4. Wait for warmap.
5. Click on a tier-1 region, click ENTER BATTLE.
6. Type one visible word + Enter inside an `evaluate(...)` block to ensure it lands as a hit (per the timing trick used in the prior E2E).
7. Click `← exit` to return to warmap.
8. Click `sign in →` in the topbar.
9. Type a real test email (e.g. an `+typewars-e2e@gmail.com` alias). Click "send magic link".
10. Confirm "check your inbox" message renders.
11. *(Manual)* In a real follow-up, the operator opens the email and clicks the link in the same browser; after redirect, confirm:
    - `https://typewars.sastaspace.com/auth/callback?jwt=...&email=...` shows "Signed in. Redirecting…"
    - Returns to `/`, the topbar shows the avatar with the orange verified pip overlay
    - `spacetime sql --server prod typewars "SELECT username, email FROM player WHERE username = 'claim_test_<...>'"` returns the row with the email populated
    - Stats from the brief battle (≥10 damage) are present on the row

If the manual email step is impractical in the autonomous run, simulate the second half by:
- Capturing the prevIdentity via `localStorage.getItem('typewars:auth_token')` in the page console.
- Calling the auth service's verify endpoint with a CLI-issued token (requires the SPACETIME_TOKEN secret), or by visiting `https://auth.sastaspace.com/auth/verify?t=<token>` after generating one out-of-band.
- Confirm the post-callback state as above.

- [ ] **Step 5: Final smoke**

```bash
spacetime sql --server prod typewars "SELECT COUNT(*) AS players, SUM(CASE WHEN email IS NOT NULL THEN 1 ELSE 0 END) AS verified FROM player" 2>&1 | tail -5
```

Expected: at least 1 verified player after the E2E run.

- [ ] **Step 6: Final commit (if any unstaged debug changes)**

```bash
git status -s
# if clean, skip; otherwise:
git add -p
git commit -m "chore(typewars): post-deploy cleanups"
git push origin main
```

---

## Self-review notes (left in for plan readers)

Spec coverage checked: Player.email field (Task 1), username uniqueness (Task 1), `claim_progress` reducer (Task 3), backend deploy + bindings (Task 4), auth service config (Task 5), shared SignInModal package (Task 6), notes migration (Task 7), Avatar component (Task 8), ProfileModal (Task 9), `/auth/callback` route (Task 10), MapWarMap topbar (Task 11), Battle + Leaderboard avatars + ProfileModal trigger (Task 12), CSP unchanged (no task — verified during E2E in Task 13).

Type consistency: `Player.email: Option<String>` (Rust) → camelCase `email: string | null` (bindings) → optional `email?: string` in local `Player` type (adapters). `claim_progress(prev_identity: Identity, email: String)` — frontend passes `prev_identity` as `Identity` (camelCase `prevIdentity` in the generated reducer call). Adjust at call sites if generated names differ.
