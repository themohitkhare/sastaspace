# Phase 2 F3 — Admin Panels Rewire (STDB-Native)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (run as one of 4 parallel Phase 2 workstream subagents). Steps use checkbox (`- [ ]`) syntax for tracking. This is the LARGEST Phase 2 workstream — six panels + connection plumbing + tests + cleanup.

**Goal:** Replace the admin panel's `services/admin-api/` HTTP path AND its `apps/admin/src/lib/data.ts` mock data with direct SpacetimeDB subscriptions and reducer calls. After this lands, every admin panel reads live STDB rows; the only writes go through `set_comment_status_with_reason` / `delete_comment` reducers; no `https://api.sastaspace.com` traffic remains. The mock-data file is deleted.

**Architecture:**

```
admin.sastaspace.com  (static Next.js, nginx)
  │
  ├── Google ID-token gate (UNCHANGED — keep f52296c9 owner verification)
  │
  ├── Anonymous read STDB ──► wss://stdb.sastaspace.com/sastaspace
  │     comment, user, system_metrics, container_status,
  │     log_event, moderation_event
  │
  ├── Anonymous read STDB ──► wss://stdb.sastaspace.com/typewars
  │     player, region, global_war, battle_session
  │
  └── Owner-token write STDB (separate connection, JWT from localStorage)
        set_comment_status_with_reason, delete_comment,
        add_log_interest, remove_log_interest
```

The Google JWT identifies the human; the **owner-STDB-token** (separate, pasted-in from `spacetime login show --token`) identifies the writer to STDB. They are decoupled — both must be present for writes to succeed. The owner pastes the token once into a settings UI; it is stored in `localStorage` under `admin_stdb_owner_token` and reused.

**Tech Stack:** TypeScript, Next.js 16 (`output: "export"`), `spacetimedb` SDK ^2.1.0 (`spacetimedb/react`), `@sastaspace/stdb-bindings`, `@sastaspace/typewars-bindings`, Playwright (E2E).

**Spec:** `docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md` § "Per-app frontend changes / apps/admin/"

**Salvaged from:** `docs/superpowers/specs/2026-04-26-admin-realdata-design.md` (the SUPERSEDED FastAPI design — only the STDB *subscription* patterns survive; all FastAPI/EventSource/`usePoll` paths are discarded).

**Master plan:** `docs/superpowers/plans/2026-04-26-stdb-native-master.md`

**Coordination:**
- F1/F2/F4 do not touch `apps/admin/`. No conflict risk inside this workstream.
- Reducer signatures consumed (already landed in Phase 1 W2 + W4):
  - `set_comment_status(id: u64, status: string)` (existing)
  - `set_comment_status_with_reason(id: u64, status: string, reason: string)` (W4)
  - `delete_comment(id: u64)` (existing)
  - `add_log_interest(container: string)` (W2)
  - `remove_log_interest(container: string)` (W2)
- Tables consumed: `comment`, `user`, `system_metrics`, `container_status`, `log_event`, `moderation_event` (sastaspace) + `player`, `region`, `global_war`, `battle_session` (typewars).
- `apps/admin/package.json` already declares `@sastaspace/typewars-bindings` workspace dep — no package.json edit required.
- Existing hooks (`apps/admin/src/hooks/useStdb.ts`, `usePoll.ts`) already exist from the WIP commit; this plan EXTENDS `useStdb.ts` and DELETES `usePoll.ts` once unused.

**Coexistence flag:** `NEXT_PUBLIC_USE_STDB_ADMIN=true|false` (default `false` until cutover per master plan). When `false`, panels keep using `usePoll` against `api.sastaspace.com` and the `data.ts` mock; when `true`, the new STDB path is active. Each panel reads the flag once and branches at the top of its component.

---

## Task 1: Extend `useStdb` to provide owner-write connection + token UI

**Files:**
- Modify: `apps/admin/src/hooks/useStdb.ts`
- Create: `apps/admin/src/components/auth/OwnerTokenSettings.tsx`
- Modify: `apps/admin/src/components/Shell.tsx` (add settings button + flag check)
- Modify: `apps/admin/next.config.mjs` (add `NEXT_PUBLIC_USE_STDB_ADMIN`)

- [ ] **Step 1: Add the env flag**

In `apps/admin/next.config.mjs`, add the flag to the `env` block:

```js
env: {
  NEXT_PUBLIC_GOOGLE_CLIENT_ID: '867977197738-pdb93cs9rm2enujjfe13jsnd5jv67cqr.apps.googleusercontent.com',
  NEXT_PUBLIC_ADMIN_API_URL: process.env.NEXT_PUBLIC_ADMIN_API_URL ?? 'https://api.sastaspace.com',
  NEXT_PUBLIC_STDB_URI: process.env.NEXT_PUBLIC_STDB_URI ?? 'wss://stdb.sastaspace.com',
  NEXT_PUBLIC_USE_STDB_ADMIN: process.env.NEXT_PUBLIC_USE_STDB_ADMIN ?? 'false',
  NEXT_PUBLIC_OWNER_EMAIL: process.env.NEXT_PUBLIC_OWNER_EMAIL ?? 'mohitkhare582@gmail.com',
},
```

- [ ] **Step 2: Extend `apps/admin/src/hooks/useStdb.ts`**

Keep the existing `SastaspaceProvider` and `TypewarsProvider` (they wrap anonymous read connections — perfect for read subscriptions). ADD an authenticated wrapper used by panels that need write access:

```typescript
'use client';

import { useMemo, useEffect, useState, createContext, useContext } from 'react';
import { SpacetimeDBProvider, useSpacetimeDB } from 'spacetimedb/react';
import { DbConnection as SastaspaceConn, reducers as sastaReducers } from '@sastaspace/stdb-bindings';
import { DbConnection as TypewarsConn } from '@sastaspace/typewars-bindings';

const STDB_URI = process.env.NEXT_PUBLIC_STDB_URI ?? 'wss://stdb.sastaspace.com';
export const USE_STDB_ADMIN = process.env.NEXT_PUBLIC_USE_STDB_ADMIN === 'true';

const OWNER_TOKEN_KEY = 'admin_stdb_owner_token';

export function getOwnerToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(OWNER_TOKEN_KEY);
}
export function setOwnerToken(t: string): void { localStorage.setItem(OWNER_TOKEN_KEY, t); }
export function clearOwnerToken(): void { localStorage.removeItem(OWNER_TOKEN_KEY); }

/**
 * Anonymous read connection — already used by Comments/Dashboard/etc for table subscriptions.
 * No JWT; STDB serves all `public` rows without auth.
 */
export function SastaspaceProvider({ children }: { children: React.ReactNode }) {
  const builder = useMemo(
    () => SastaspaceConn.builder().withUri(STDB_URI).withDatabaseName('sastaspace'),
    [],
  );
  return SpacetimeDBProvider({ connectionBuilder: builder, children });
}

/**
 * Owner-write connection — used to call moderation reducers, add/remove log_interest.
 * Pulls JWT from localStorage; if absent, returns null and panels show the
 * "paste your owner STDB token" prompt instead of write buttons.
 */
export function SastaspaceOwnerProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getOwnerToken());
  // Re-read token on storage events (other tab pasted it, settings modal saved it)
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === OWNER_TOKEN_KEY) setToken(e.newValue);
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const builder = useMemo(() => {
    if (!token) return null;
    return SastaspaceConn.builder()
      .withUri(STDB_URI)
      .withDatabaseName('sastaspace')
      .withToken(token);
  }, [token]);

  if (!builder) {
    // No token yet — render children without the provider.
    // Components downstream see useSpacetimeDB().isActive === false and
    // gracefully degrade to read-only.
    return <>{children}</>;
  }
  return SpacetimeDBProvider({ connectionBuilder: builder, children });
}

export function TypewarsProvider({ children }: { children: React.ReactNode }) {
  const builder = useMemo(
    () => TypewarsConn.builder().withUri(STDB_URI).withDatabaseName('typewars'),
    [],
  );
  return SpacetimeDBProvider({ connectionBuilder: builder, children });
}

/** Re-export the SDK hook for convenience so panels import from one place. */
export { useSpacetimeDB } from 'spacetimedb/react';
```

(If the `withToken` builder method is named differently in `spacetimedb` ^2.1.0 — e.g. `withCredentials` — adapt to whatever the regenerated `index.ts` of `@sastaspace/stdb-bindings` exposes. The auth-mailer worker plan in W1 Task 2 Step 1 has the same caveat.)

- [ ] **Step 3: Create the owner-token settings UI**

`apps/admin/src/components/auth/OwnerTokenSettings.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { getOwnerToken, setOwnerToken, clearOwnerToken } from '@/hooks/useStdb';
import Icon from '@/components/Icon';

type Props = { open: boolean; onClose: () => void };

export default function OwnerTokenSettings({ open, onClose }: Props) {
  const [value, setValue] = useState(() => getOwnerToken() ?? '');
  const [saved, setSaved] = useState(false);

  if (!open) return null;

  const save = () => {
    if (!value.trim()) return;
    setOwnerToken(value.trim());
    setSaved(true);
    setTimeout(() => { setSaved(false); onClose(); window.location.reload(); }, 600);
  };

  const clear = () => { clearOwnerToken(); setValue(''); window.location.reload(); };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
        <div className="modal__title">SpacetimeDB owner token</div>
        <div className="modal__body">
          <p style={{ marginBottom: 12 }}>
            Paste the output of <code style={{ fontFamily: 'var(--font-mono)' }}>spacetime login show --token</code> below.
            Stored only in this browser. Required for moderation actions and live log streaming.
          </p>
          <textarea
            className="input"
            style={{ width: '100%', minHeight: 96, fontFamily: 'var(--font-mono)', fontSize: 11 }}
            placeholder="eyJ0eXAiOiJKV1QiLCJhbGc..."
            value={value}
            onChange={e => setValue(e.target.value)}
          />
          {saved && <div style={{ marginTop: 8, color: 'var(--brand-status-live)' }}>Saved — reloading…</div>}
        </div>
        <div className="modal__actions">
          <button className="btn btn--ghost" onClick={clear}><Icon name="trash" size={13}/> Clear</button>
          <button className="btn btn--ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn--approve" onClick={save} disabled={!value.trim()}>Save</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Wire settings button into Shell**

In `apps/admin/src/components/Shell.tsx`:
- Import `OwnerTokenSettings` and `SastaspaceOwnerProvider`, `USE_STDB_ADMIN` from `@/hooks/useStdb`
- Add a `useState` for `settingsOpen`
- Add a settings button in the sidebar footer next to "Sign out": `<button onClick={() => setSettingsOpen(true)} title="Owner STDB token"><Icon name="key" size={16}/></button>` (if `key` icon doesn't exist, reuse `shield` or add a one-line SVG to `Icon.tsx`)
- Wrap the entire authenticated `<main>` body in `<SastaspaceOwnerProvider>` so all child panels can use `useSpacetimeDB()` against the owner connection where present
- When `USE_STDB_ADMIN` is `false`, do not wrap in the owner provider (legacy path stays untouched)
- Render `<OwnerTokenSettings open={settingsOpen} onClose={() => setSettingsOpen(false)}/>` at the end of the auth-app return

- [ ] **Step 5: Typecheck**

```bash
cd apps/admin && pnpm typecheck
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add apps/admin/src/hooks/useStdb.ts \
        apps/admin/src/components/auth/OwnerTokenSettings.tsx \
        apps/admin/src/components/Shell.tsx \
        apps/admin/next.config.mjs
git commit -m "$(cat <<'EOF'
feat(admin): owner STDB token wiring + USE_STDB_ADMIN flag

Phase 2 F3 connection layer. SastaspaceOwnerProvider opens a JWT-authed
STDB connection for moderation writes; owner pastes the token once via
the settings modal (stored in localStorage). Read subscriptions stay on
the existing anonymous SastaspaceProvider. USE_STDB_ADMIN env flag gates
the new path so panels can flip per coexistence pattern.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Rewire Comments panel

**Files:**
- Modify: `apps/admin/src/components/panels/Comments.tsx`

The existing panel ALREADY uses `useTable(tables.comment)` + `useTable(tables.user)` for reads (the WIP commit landed that). The remaining work is replacing the FastAPI write `fetch(... /stdb/comments/{id}/status ...)` with a reducer call, AND subscribing to `moderation_event` to surface verdict reasons.

- [ ] **Step 1: Add moderation_event subscription + verdict join**

At the top of `CommentsInner`, alongside the existing `useTable(tables.comment)` and `useTable(tables.user)`, add:

```typescript
const [moderationRows] = useTable(tables.moderation_event);
const verdictMap = useMemo(() => {
  const m = new Map<bigint, string>();
  // Last verdict per comment wins
  const sorted = [...moderationRows].sort((a, b) => {
    const at = a.createdAt instanceof Date ? a.createdAt.getTime()
      : typeof a.createdAt === 'bigint' ? Number(a.createdAt / 1000n) : 0;
    const bt = b.createdAt instanceof Date ? b.createdAt.getTime()
      : typeof b.createdAt === 'bigint' ? Number(b.createdAt / 1000n) : 0;
    return at - bt;
  });
  for (const ev of sorted) m.set(ev.commentId, ev.reason);
  return m;
}, [moderationRows]);
```

In the `comments` `useMemo`, attach `reason: verdictMap.get(c.id) ?? null` to each row.

In each card's render, when `c.status === 'flagged'` show a one-line muted caption: `<div className="comment-card__reason">verdict: {c.reason ?? 'unknown'}</div>`.

- [ ] **Step 2: Replace FastAPI write fetches with reducer calls**

Import:
```typescript
import { reducers } from '@sastaspace/stdb-bindings';
import { USE_STDB_ADMIN } from '@/hooks/useStdb';
```

Replace `setStatus` with:
```typescript
const setStatus = async (id: bigint, status: CommentStatus, reason: string) => {
  setActioning(id);
  setOptimistic(prev => new Map(prev).set(id, status));
  try {
    if (USE_STDB_ADMIN) {
      // Owner connection (set up by SastaspaceOwnerProvider in Shell) sends this.
      // The hook lookup goes through the same useSpacetimeDB() — when the owner
      // connection is active, reducer calls flow over it; otherwise they fail fast.
      reducers.setCommentStatusWithReason(id, status, reason);
    } else {
      // Legacy FastAPI path
      const token = localStorage.getItem('admin_token') ?? '';
      const res = await fetch(`${ADMIN_API_URL}/stdb/comments/${id}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    }
  } catch {
    setOptimistic(prev => { const n = new Map(prev); n.delete(id); return n; });
  } finally {
    setActioning(null);
  }
};
```

Update the button handlers:
- Approve: `void setStatus(c.id, 'approved', 'approved')`
- Flag: `void setStatus(c.id, 'flagged', 'classifier-rejected')`
- Reject: `void setStatus(c.id, 'rejected', 'manual-reject')`

Replace `doDelete` similarly:
```typescript
const doDelete = async () => {
  if (confirmDelete == null) return;
  const id = confirmDelete;
  setConfirmDelete(null);
  if (USE_STDB_ADMIN) {
    try { reducers.deleteComment(id); } catch { /* row stays; subscription would have removed it */ }
  } else {
    const token = localStorage.getItem('admin_token') ?? '';
    await fetch(`${ADMIN_API_URL}/stdb/comments/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => {});
  }
};
```

(Reducer name `setCommentStatusWithReason` / `deleteComment` is the camel-cased binding generated by `spacetime generate --lang typescript`. Verify against `packages/stdb-bindings/src/generated/index.ts` exported `reducers` accessor map — adjust if the casing differs.)

- [ ] **Step 3: Show "no owner token" warning when in STDB mode without token**

Below the filter bar, when `USE_STDB_ADMIN && !getOwnerToken()`:
```tsx
<div className="banner banner--warn" style={{ marginBottom: 14 }}>
  <Icon name="shield-x" size={16}/>
  <span>Moderation actions disabled — paste your STDB owner token in Settings.</span>
</div>
```

Disable Approve/Flag/Reject/Delete buttons in that state.

- [ ] **Step 4: Typecheck**

```bash
cd apps/admin && pnpm typecheck
```

- [ ] **Step 5: Commit**

```bash
git add apps/admin/src/components/panels/Comments.tsx
git commit -m "$(cat <<'EOF'
feat(admin): Comments panel calls reducers + shows moderation reason

Phase 2 F3. Approve/Flag/Reject route through set_comment_status_with_reason
reducer; Delete routes through delete_comment. moderation_event subscription
surfaces verdict reason (e.g. classifier-rejected) inline on flagged rows.
USE_STDB_ADMIN flag preserves the legacy admin-api path.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Rewire Server panel (system_metrics subscription)

**Files:**
- Modify: `apps/admin/src/components/panels/Server.tsx`

- [ ] **Step 1: Branch on USE_STDB_ADMIN**

Replace the top of `Server()`:

```typescript
import { useSpacetimeDB, useTable } from 'spacetimedb/react';
import { tables } from '@sastaspace/stdb-bindings';
import { USE_STDB_ADMIN } from '@/hooks/useStdb';

export default function Server() {
  if (USE_STDB_ADMIN) return <ServerStdb/>;
  return <ServerLegacy/>;
}
```

Move the existing `usePoll` body into a `ServerLegacy` component (rename, no other change).

- [ ] **Step 2: Implement `ServerStdb`**

```typescript
function ServerStdb() {
  const { isActive } = useSpacetimeDB();
  const [metricsRows] = useTable(tables.system_metrics);
  // The table is single-row (id=0) but useTable returns an array
  const row = metricsRows[0];

  // Same history-buffer dance as legacy, fed by row updates
  const cpuHistory = useRef<number[]>([]);
  const memHistory = useRef<number[]>([]);
  const netTxHistory = useRef<number[]>([]);
  const netRxHistory = useRef<number[]>([]);
  const prevNet = useRef<{ tx: bigint; rx: bigint } | null>(null);
  const [, forceRender] = useState(0);

  useEffect(() => {
    if (!row) return;
    const push = (arr: number[], val: number) => {
      arr.push(val); if (arr.length > 60) arr.shift();
    };
    push(cpuHistory.current, row.cpuPct);
    push(memHistory.current, row.memUsedGb);
    const prev = prevNet.current;
    if (prev) {
      push(netTxHistory.current, Math.max(0, Number(row.netTxBytes - prev.tx) / 1e6));
      push(netRxHistory.current, Math.max(0, Number(row.netRxBytes - prev.rx) / 1e6));
    }
    prevNet.current = { tx: row.netTxBytes, rx: row.netRxBytes };
    forceRender(n => n + 1);
  }, [row]);

  if (!isActive) return <div style={{ padding: 40, color: 'var(--color-fg-muted)', textAlign: 'center' }}>Connecting to SpacetimeDB…</div>;
  if (!row) return <div style={{ padding: 40, color: 'var(--color-fg-muted)', textAlign: 'center' }}>No system metrics yet — waiting for admin-collector worker.</div>;

  // Adapt STDB row shape to the same `data` view the legacy renderer uses.
  const data: SystemMetrics = {
    cpu: { pct: row.cpuPct, cores: row.cores },
    mem: {
      used_gb: row.memUsedGb, total_gb: row.memTotalGb, pct: row.memPct,
      swap_used_mb: row.swapUsedMb, swap_total_mb: row.swapTotalMb,
    },
    disk: { used_gb: row.diskUsedGb, total_gb: row.diskTotalGb, pct: row.diskPct, mount: '/' },
    net: { tx_bytes: Number(row.netTxBytes), rx_bytes: Number(row.netRxBytes) },
    uptime_s: Number(row.uptimeS),
    gpu: row.gpuPct != null ? {
      pct: row.gpuPct,
      vram_used_mb: row.gpuVramUsedMb ?? 0,
      vram_total_mb: row.gpuVramTotalMb ?? 0,
      temp_c: row.gpuTempC ?? 0,
      model: row.gpuModel ?? 'unknown',
    } : undefined,
  };

  return /* ... reuse the existing JSX from legacy, parameterized on `data` ... */;
}
```

Extract the legacy panel's JSX (the `<div><div className="grid-4">…</div>…</div>` block) into a shared `renderServerView(data, cpuHistory, memHistory, netTxHistory, netRxHistory)` function used by both `ServerLegacy` and `ServerStdb` to avoid duplication. The mount field for `disk` is hardcoded `'/'` in STDB mode since the table doesn't carry it — that matches the spec; if needed later, add a column.

- [ ] **Step 3: Typecheck**

- [ ] **Step 4: Commit**

```bash
git add apps/admin/src/components/panels/Server.tsx
git commit -m "$(cat <<'EOF'
feat(admin): Server panel reads system_metrics table live

Phase 2 F3. ServerStdb subscribes to the single-row system_metrics table
and feeds the same chart-history buffers the legacy poller used. Behind
USE_STDB_ADMIN flag — legacy /system poll path preserved.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Rewire Services panel (container_status subscription)

**Files:**
- Modify: `apps/admin/src/components/panels/Services.tsx`

- [ ] **Step 1: Add `ServicesStdb` branch**

Same split-on-flag pattern as Server. `ServicesStdb`:

```typescript
function ServicesStdb({ navigate }: { navigate: (path: string) => void }) {
  const { isActive } = useSpacetimeDB();
  const [statusRows] = useTable(tables.container_status);
  if (!isActive) return <div style={{ padding: 40, color: 'var(--color-fg-muted)' }}>Connecting…</div>;
  if (statusRows.length === 0) return <div style={{ padding: 40, color: 'var(--color-fg-muted)' }}>No container data yet.</div>;

  // Adapt STDB row shape to ContainerRow shape used by friendlyName / Chip etc.
  const containers: ContainerRow[] = statusRows.map(r => ({
    name: r.name,
    status: r.status,
    image: r.image,
    started_at: '', // not carried in the table; uptime_s suffices
    uptime_s: Number(r.uptimeS),
    mem_usage_mb: r.memUsedMb,
    mem_limit_mb: r.memLimitMb,
    restart_count: r.restartCount,
  }));

  return /* same JSX as legacy, fed by `containers` */;
}
```

Extract shared `renderServicesView(containers, navigate)` so the legacy and STDB branches share rendering.

- [ ] **Step 2: Typecheck**

- [ ] **Step 3: Commit**

```bash
git add apps/admin/src/components/panels/Services.tsx
git commit -m "$(cat <<'EOF'
feat(admin): Services panel reads container_status table live

Phase 2 F3. ServicesStdb subscribes to container_status (collector
upserts every 15s). Same render path as legacy.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Rewire Logs panel (log_event subscription + interest tracking)

**Files:**
- Modify: `apps/admin/src/components/panels/Logs.tsx`

This is the most behaviour-heavy panel. Three things:
1. On mount (and on container switch): call `add_log_interest(currentContainer)` so the worker starts following that container's logs.
2. Subscribe to `log_event WHERE container = '<currentContainer>'`, render most-recent N.
3. On unmount (and before container switch): call `remove_log_interest(prev)`.

- [ ] **Step 1: Split on flag**

```typescript
export default function Logs({ initialService, theme = 'dark' }: LogsProps) {
  if (USE_STDB_ADMIN) return <LogsStdb initialService={initialService} theme={theme}/>;
  return <LogsLegacy initialService={initialService} theme={theme}/>;
}
```

Move the existing implementation into `LogsLegacy` unchanged.

- [ ] **Step 2: Implement `LogsStdb`**

```typescript
function LogsStdb({ initialService, theme }: LogsProps) {
  const { isActive, conn } = useSpacetimeDB(); // conn is the SastaspaceConn DbConnection
  const [statusRows] = useTable(tables.container_status);
  const [active, setActive] = useState(initialService ?? 'sastaspace-stdb');
  const [tail, setTail] = useState(200);
  const [filter, setFilter] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [cleared, setCleared] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);

  // Subscribe to log_event filtered by container, manage interest lifecycle
  const [logRows] = useTable(
    tables.log_event.where(r => r.container === active),
  );

  useEffect(() => {
    if (!isActive) return;
    try { reducers.addLogInterest(active); } catch { /* no-op if no owner token */ }
    return () => {
      try { reducers.removeLogInterest(active); } catch { /* same */ }
    };
  }, [active, isActive]);

  const lines: LogLine[] = useMemo(() => {
    return [...logRows]
      .sort((a, b) => Number(a.tsMicros - b.tsMicros))
      .slice(-tail)
      .map(r => {
        const ts = new Date(Number(r.tsMicros / 1000n));
        const hh = ts.getHours().toString().padStart(2, '0');
        const mm = ts.getMinutes().toString().padStart(2, '0');
        const ss = ts.getSeconds().toString().padStart(2, '0');
        const ms = ts.getMilliseconds().toString().padStart(3, '0');
        return { ts: `${hh}:${mm}:${ss}.${ms}`, text: r.text, level: r.level };
      });
  }, [logRows, tail]);

  // ... reuse the existing JSX (sidebar list + toolbar + output) verbatim,
  // with `lines` replaced by the derived value above and `serviceList` derived
  // from statusRows instead of containers.
}
```

Notes:
- The `useTable` `where` filter is client-side; the *subscription query* sent to STDB also needs to be filtered server-side via `subscriptionBuilder().subscribe(["SELECT * FROM log_event WHERE container = '...'"])`. If the SDK's `useTable` doesn't accept SQL filters, fall back to `useEffect(() => conn.subscriptionBuilder().subscribe([...])`. Verify against `packages/stdb-bindings/src/generated/index.ts` what the QueryBuilder exposes.
- `add_log_interest` / `remove_log_interest` are owner-only reducers. When `getOwnerToken()` is absent, skip them (Logs panel still works in read-only mode against whatever the worker is already streaming for *some* owner).
- Reuse `serviceList` from existing legacy code, fed by `statusRows` instead of polled `containers`.

- [ ] **Step 3: Typecheck**

- [ ] **Step 4: Commit**

```bash
git add apps/admin/src/components/panels/Logs.tsx
git commit -m "$(cat <<'EOF'
feat(admin): Logs panel subscribes to log_event + manages log_interest

Phase 2 F3. LogsStdb adds add_log_interest on mount/switch and
remove_log_interest on unmount/switch (owner-only; silently no-ops
without owner token). Renders log_event rows filtered by current
container. Legacy SSE path preserved.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Rewire Dashboard panel (aggregate from STDB tables)

**Files:**
- Modify: `apps/admin/src/components/panels/Dashboard.tsx`

The existing Dashboard already pulls `comment` rows from STDB. Remaining: replace the two `usePoll` calls (`/system`, `/containers`) with `useTable(tables.system_metrics)` + `useTable(tables.container_status)` when `USE_STDB_ADMIN`. Also add a "recent moderation activity" card that reads `tables.moderation_event` ordered by `createdAt desc limit 10`.

- [ ] **Step 1: Split on flag, add new subscriptions**

```typescript
function DashboardInner({ navigate }: { navigate: (path: string) => void }) {
  const { isActive } = useSpacetimeDB();
  const [commentRows] = useTable(tables.comment);
  const [moderationRows] = useTable(tables.moderation_event);

  // Containers + system metrics: STDB or polled per flag
  const [stdbMetrics] = useTable(tables.system_metrics);
  const [stdbContainers] = useTable(tables.container_status);
  const { data: polledContainers } = usePoll<ContainerRow[]>(
    USE_STDB_ADMIN ? '__skip__' : '/containers', 15000,
  );
  const { data: polledSystem } = usePoll<SystemMetrics>(
    USE_STDB_ADMIN ? '__skip__' : '/system', 3000,
  );

  const system = USE_STDB_ADMIN ? adaptMetrics(stdbMetrics[0]) : polledSystem;
  const containers = USE_STDB_ADMIN ? adaptContainers(stdbContainers) : polledContainers;
  // ... rest unchanged
```

`adaptMetrics(row)` and `adaptContainers(rows)` are tiny mappers that produce the existing `SystemMetrics` / `ContainerRow[]` shapes from STDB rows (same shape as in Tasks 3 + 4 — extract to `apps/admin/src/lib/stdb-adapters.ts` if convenient).

`usePoll` should treat `'__skip__'` as a no-op (add a guard in `usePoll.ts`: if path starts with `__skip__`, do nothing). Alternative: drop `usePoll` entirely from Dashboard when the flag is on by conditionally constructing.

- [ ] **Step 2: Add "Recent moderation activity" card**

In the right column of `split-2` (currently the Services preview), add a third row OR replace the Services card with two stacked cards:

```tsx
<div>
  <div className="section__head"><h2 className="section__title">Recent moderation</h2></div>
  <div className="card" style={{ padding: '4px 22px' }}>
    {moderationRows.length === 0 && (
      <div style={{ padding: '20px 0', color: 'var(--color-fg-muted)', fontSize: 13 }}>No verdicts yet.</div>
    )}
    {[...moderationRows]
      .sort((a, b) => {
        const ta = a.createdAt instanceof Date ? a.createdAt.getTime() : Number(a.createdAt);
        const tb = b.createdAt instanceof Date ? b.createdAt.getTime() : Number(b.createdAt);
        return tb - ta;
      })
      .slice(0, 10)
      .map(ev => (
        <div key={String(ev.id)} className="recent-row">
          <Chip status={ev.status as 'approved' | 'flagged' | 'rejected'}/>
          <div className="recent-row__main">
            <div className="recent-row__top">
              <span className="recent-row__author">comment #{String(ev.commentId)}</span>
              <span className="muted">·</span>
              <span className="recent-row__post">{ev.reason}</span>
            </div>
          </div>
          <span className="recent-row__time">
            {relTime(ev.createdAt instanceof Date ? ev.createdAt.toISOString() : new Date(Number(ev.createdAt) / 1000).toISOString())}
          </span>
        </div>
      ))}
  </div>
</div>
```

- [ ] **Step 3: Typecheck**

- [ ] **Step 4: Commit**

```bash
git add apps/admin/src/components/panels/Dashboard.tsx \
        apps/admin/src/hooks/usePoll.ts \
        apps/admin/src/lib/stdb-adapters.ts
git commit -m "$(cat <<'EOF'
feat(admin): Dashboard aggregates from STDB tables + moderation feed

Phase 2 F3. Dashboard reads system_metrics + container_status from STDB
when USE_STDB_ADMIN; adds recent moderation card sourced from
moderation_event (top 10 by created_at desc). Shared stdb-adapters lib
maps row shapes to legacy view types.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: TypeWars panel — verify and tighten

**Files:**
- Modify (only if needed): `apps/admin/src/components/panels/TypeWars.tsx`

The existing TypeWars panel (committed in WIP) ALREADY subscribes to `player`, `region`, `battle_session` via `TypewarsProvider`. This task is mostly verification + adding `global_war` for season context.

- [ ] **Step 1: Subscribe to `global_war` and surface season info**

```typescript
const [warRows] = useTable(tables.global_war);
const war = warRows[0]; // single-row table
```

In the WAR ACTIVE/IDLE banner, show `season {war?.seasonNumber ?? '?'}` and `started {relTime(war?.startedAt)}` if present.

- [ ] **Step 2: Confirm `battle_session` filter**

Existing code does `battleRows.filter(b => b.active)`. Confirm against `packages/typewars-bindings/src/generated/battle_session_table.ts` that the field is named `active`. If it is `isActive` or similar, adjust.

- [ ] **Step 3: Typecheck**

- [ ] **Step 4: Commit (skip if no diff)**

```bash
git add apps/admin/src/components/panels/TypeWars.tsx
git commit -m "$(cat <<'EOF'
feat(admin): TypeWars panel surfaces global_war season info

Phase 2 F3. Adds global_war subscription to show season + uptime in the
WAR ACTIVE banner. Read-only; no writes from admin.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Delete `apps/admin/src/lib/data.ts` mock + update `usePoll.ts`

**Files:**
- Modify: `apps/admin/src/lib/data.ts` — keep types and helpers, delete any remaining mock arrays
- Modify: `apps/admin/src/hooks/usePoll.ts` — keep until Phase 3 cutover, then delete

- [ ] **Step 1: Confirm no mock data remains**

```bash
grep -nE "(COMMENTS|LEGIONS|REGIONS|ACTIVE_BATTLES|MOCK)" apps/admin/src/lib/data.ts
```

The current `data.ts` (per read at plan time) already only contains TYPES + `relTime` + `formatUptime` + `LEGION_COLORS` + `LEGION_NAMES`. No mock arrays. So this step is a confirmation, not a deletion.

- [ ] **Step 2: Move helpers to a clearer file**

Rename `apps/admin/src/lib/data.ts` → `apps/admin/src/lib/types.ts` (since it no longer holds data). Update all imports:

```bash
cd apps/admin && \
  grep -rl "from '@/lib/data'" src | xargs sed -i '' "s|from '@/lib/data'|from '@/lib/types'|g"
git mv src/lib/data.ts src/lib/types.ts
```

Verify with `pnpm typecheck`.

- [ ] **Step 3: Commit**

```bash
git add apps/admin/src/
git commit -m "$(cat <<'EOF'
refactor(admin): rename lib/data.ts to lib/types.ts

Phase 2 F3 cleanup. The file holds only types + helpers now (no mock
data). Renaming for clarity. usePoll.ts kept until Phase 3 cutover
removes the legacy admin-api path.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: E2E spec — admin panels real-time updates

**Files:**
- Create: `tests/e2e/specs/admin-panels.spec.ts`

Coverage matrix: each of the 4 STDB-fed panels (Comments / Server / Services / Logs) gets a "row inserted via spacetime CLI → UI updates within N seconds" test. Both feature-flag paths must pass — when `USE_STDB_ADMIN=false`, the existing `admin.spec.ts` covers the legacy path; when `true`, this new spec covers the STDB path. CI runs both.

- [ ] **Step 1: Author the spec**

```typescript
import { expect, test } from "@playwright/test";
import { signIn } from "../helpers/auth.js";
import { sql, pollUntil } from "../helpers/stdb.js";
import { ADMIN } from "../helpers/urls.js";

const OWNER_EMAIL = process.env.E2E_OWNER_EMAIL ?? "mohitkhare582@gmail.com";
const OWNER_STDB_TOKEN = process.env.E2E_OWNER_STDB_TOKEN ?? "";

test.describe("admin panels — STDB live updates", () => {
  test.skip(!OWNER_STDB_TOKEN, "E2E_OWNER_STDB_TOKEN not set — skipping STDB-mode admin specs");

  test.beforeEach(async ({ page }) => {
    await signIn(page, OWNER_EMAIL);
    // Inject the owner STDB token + flag into localStorage before nav
    await page.addInitScript(({ tok }) => {
      localStorage.setItem("admin_stdb_owner_token", tok as string);
    }, { tok: OWNER_STDB_TOKEN });
    await page.goto(ADMIN);
  });

  test("Comments — pending row appears within 5s; Approve flips status", async ({ page, request }) => {
    const probeBody = `e2e-probe-${Date.now()}-pending`;
    // Insert a comment via SQL as a system identity (test-only path).
    // Adjust this to the actual seeding helper your suite uses; falls back to
    // calling submit_user_comment via STDB REST.
    await sql(request,
      `INSERT INTO comment (id, post_slug, author_name, body, created_at, status, submitter)
       VALUES (0, '2026-04-25-hello', 'e2e', '${probeBody}', now(), 'pending',
               x'1111111111111111111111111111111111111111111111111111111111111111')`);

    await page.click('button[title="Comments"], a:has-text("Comments")');
    await expect(page.locator('text=' + probeBody)).toBeVisible({ timeout: 5_000 });

    await page.locator(`.comment-card:has-text("${probeBody}") button:has-text("Approve")`).click();

    await pollUntil(async () => {
      const rows = await sql(request,
        `SELECT status FROM comment WHERE body = '${probeBody}'`);
      return rows[0]?.[0] === 'approved';
    }, { what: 'comment approved via reducer', timeoutMs: 10_000 });
  });

  test("Server — system_metrics upsert reflects in UI within 5s", async ({ page, request }) => {
    await page.click('a:has-text("Server")');
    // Push a known metric row via the upsert reducer; wait for cpu number to change.
    const targetCpu = 73;
    await sql(request,
      `CALL upsert_system_metrics(${targetCpu}.0, 16, 8.0, 32.0, 25.0, 0, 2048, 100, 500, 20.0, 0, 0, 100, NULL, NULL, NULL, NULL, NULL)`);
    // (exact CALL signature depends on STDB SQL surface; if not supported, drive
    // via spacetime CLI in a child_process or via the node SDK in a script step)
    await expect(page.locator('.card__value', { hasText: `${targetCpu}%` })).toBeVisible({ timeout: 5_000 });
  });

  test("Services — container_status upsert reflects in UI within 5s", async ({ page, request }) => {
    await page.click('a:has-text("Services")');
    const probeName = `e2e-probe-${Date.now()}`;
    await sql(request,
      `CALL upsert_container_status('${probeName}', 'running', 'test:latest', 60, 100, 1024, 0)`);
    await expect(page.locator('.service-card__name', { hasText: /e2e probe/i })).toBeVisible({ timeout: 5_000 });
  });

  test("Logs — log_event row appears in panel within 3s", async ({ page, request }) => {
    await page.click('a:has-text("Logs")');
    // First click a known container so log_interest is registered
    await page.locator('.logs-service-item', { hasText: 'Stdb' }).first().click();
    const probeText = `E2E_PROBE_${Date.now()}`;
    await sql(request,
      `CALL append_log_event('sastaspace-stdb', ${Date.now() * 1000}, 'info', '${probeText}')`);
    await expect(page.locator(`.log-line:has-text("${probeText}")`)).toBeVisible({ timeout: 3_000 });
  });
});
```

(`CALL <reducer>(...)` syntax depends on the STDB version's SQL support for invoking reducers. If unsupported, use the `spacetime call` CLI from `child_process` — see how `tests/e2e/helpers/` already shells out elsewhere. The intent is what matters; the helper is portable.)

- [ ] **Step 2: Add the env var to `tests/e2e/README` (or wherever envs are documented)**

Document `E2E_OWNER_STDB_TOKEN` — the spacetime owner JWT — required to run the STDB-mode admin specs.

- [ ] **Step 3: Run the spec locally**

```bash
NEXT_PUBLIC_USE_STDB_ADMIN=true \
  E2E_OWNER_STDB_TOKEN=$(spacetime login show --token) \
  pnpm --filter e2e test admin-panels
```

Expected: all four tests green.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/specs/admin-panels.spec.ts tests/e2e/README*
git commit -m "$(cat <<'EOF'
test(e2e): admin panels STDB-mode real-time spec

Phase 2 F3. Per panel: insert a row via STDB SQL/CLI, assert UI reflects
within the spec'd budget (3-5s). Comments test also verifies the Approve
button calls set_comment_status_with_reason. Skipped when
E2E_OWNER_STDB_TOKEN is unset so legacy CI keeps passing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: CI matrix — run admin specs against both flag paths

**Files:**
- Modify: `.github/workflows/<existing e2e workflow>.yml` (whichever runs Playwright; check `git ls-files .github/workflows/`)

- [ ] **Step 1: Duplicate the admin job in the matrix**

Add a job dimension `use_stdb_admin: ['true', 'false']`. Pass through to the test runner via `env: NEXT_PUBLIC_USE_STDB_ADMIN: ${{ matrix.use_stdb_admin }}`. The legacy job continues running `tests/e2e/specs/admin.spec.ts`; the STDB job adds `tests/e2e/specs/admin-panels.spec.ts`.

- [ ] **Step 2: Wire `E2E_OWNER_STDB_TOKEN` from CI secrets**

Add it to the workflow `env`:
```yaml
env:
  E2E_OWNER_STDB_TOKEN: ${{ secrets.E2E_OWNER_STDB_TOKEN }}
```

The owner needs to add this secret in the repo settings before the matrix turns green.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/
git commit -m "$(cat <<'EOF'
ci(e2e): matrix admin specs across NEXT_PUBLIC_USE_STDB_ADMIN paths

Phase 2 F3. Both legacy (false) and STDB (true) paths must pass before
Phase 3 cutover flips the default.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Smoke test against the dev compose

- [ ] **Step 1: Boot the stack**

```bash
cd infra && docker compose up -d
# Confirm worker is up and admin-collector is enabled
docker compose logs workers | grep admin-collector
```

If `admin-collector` flag was off in compose, set `WORKER_ADMIN_COLLECTOR_ENABLED=true` for the dev compose only.

- [ ] **Step 2: Run admin frontend in dev with the flag on**

```bash
NEXT_PUBLIC_USE_STDB_ADMIN=true \
NEXT_PUBLIC_STDB_URI=ws://localhost:3100 \
  pnpm --filter @sastaspace/admin dev
```

Visit `http://localhost:3003`. Sign in via Google. Open Settings → paste the local owner token from `spacetime login show --token`. Reload.

- [ ] **Step 3: Walk every panel**

Verify visually:
- Dashboard: pending count + system stats + recent moderation list update live
- Comments: pending rows visible; click Approve on a probe row, status flips
- Server: CPU sparkline updates every ~3s
- Services: container list reflects `docker ps`; stop one container → status changes within 15s
- Logs: select a container → lines stream in
- TypeWars: legions/regions/battles render

- [ ] **Step 4: Note any drift in a follow-up commit**

If reducer signatures or table column casing don't match the binding (e.g. `gpuPct` vs `gpu_pct`), fix and commit; the binding is the source of truth.

---

## Task 12: Update CSP for the admin frontend

**Files:**
- Modify: `infra/admin/security_headers.conf` (if it exists — confirm with `find infra/admin -type f`)

- [ ] **Step 1: Ensure `connect-src` allows the STDB websocket origin**

```
connect-src 'self' wss://stdb.sastaspace.com https://stdb.sastaspace.com https://api.sastaspace.com;
```

(Keep `api.sastaspace.com` until Phase 3 cutover removes it.)

- [ ] **Step 2: Commit**

```bash
git add infra/admin/security_headers.conf
git commit -m "$(cat <<'EOF'
chore(infra): admin CSP allows wss://stdb.sastaspace.com

Phase 2 F3. New direct-STDB connections from admin frontend require
WSS connect-src. api.sastaspace.com remains until Phase 3 cutover.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## F3 acceptance checklist

- [ ] `apps/admin/src/hooks/useStdb.ts` exposes `SastaspaceProvider`, `SastaspaceOwnerProvider`, `TypewarsProvider`, `getOwnerToken`, `setOwnerToken`, `clearOwnerToken`, `USE_STDB_ADMIN`
- [ ] All six panels (Dashboard, Comments, Server, Services, Logs, TypeWars) render correctly with `NEXT_PUBLIC_USE_STDB_ADMIN=true`
- [ ] All six panels still render correctly with `NEXT_PUBLIC_USE_STDB_ADMIN=false` (legacy admin-api path)
- [ ] No remaining mock data arrays in `apps/admin/src/`
- [ ] `apps/admin/src/lib/types.ts` exists; `apps/admin/src/lib/data.ts` no longer exists
- [ ] `pnpm typecheck` clean in `apps/admin/`
- [ ] `pnpm lint` clean in `apps/admin/`
- [ ] `tests/e2e/specs/admin-panels.spec.ts` passes locally with `E2E_OWNER_STDB_TOKEN` set
- [ ] Existing `tests/e2e/specs/admin.spec.ts` still passes (legacy path untouched)
- [ ] CI matrix runs both flag values; both green
- [ ] Owner token settings UI works: paste → save → reload → moderation buttons enabled
- [ ] CSP allows the WSS origin

When all checked: F3 is done. Phase 3 cutover (a separate plan) flips the default `NEXT_PUBLIC_USE_STDB_ADMIN=true` in production, observes for one canary period, then stops the `sastaspace-admin-api` container and deletes `apps/admin/src/hooks/usePoll.ts` + the legacy panel branches.

---

## Self-review

**Spec coverage:** all six panels rewired ✅, mock `data.ts` retired ✅, `useStdb.ts` extended (not duplicated) ✅, owner-JWT-from-localStorage flow ✅, env flag for coexistence ✅, E2E for each panel ✅. ✅

**Coordination:** does not touch F1/F2/F4 surfaces; reducer signatures consumed match what W2/W4 land per the W2 plan and the regenerated bindings inspected at plan-time. ✅

**Placeholder scan:** SDK `withToken` builder method name flagged as version-dependent in Task 1 Step 2; reducer accessor casing flagged in Task 2 Step 2; `CALL <reducer>` SQL syntax flagged as version-dependent in Task 9 Step 1 with CLI fallback. No "TBD" survives — every unknown is bracketed with what to verify and where. ✅

**Type consistency:** STDB row shapes (`row.cpuPct`, `row.memUsedGb`, `row.netTxBytes` as `bigint`) match what the existing `system_metrics_table.ts` exports. `bigint → number` conversions for chart history are explicit. ✅

**Owner-STDB-token UX:** v1 ships with manual paste-from-CLI. Worth flagging to user that this is a one-time setup but a footgun if owner uses multiple devices. A future improvement: derive the token server-side from a Google ID-token exchange, but that re-introduces a service. Out of scope for F3.
