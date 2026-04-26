'use client';

// Shared SpacetimeDB provider factories for admin panel.
// Reads come from anonymous public-table subscriptions; writes (moderation +
// log_interest) require the owner's STDB JWT pasted into the settings UI.
//
// To keep React contexts simple (one connection per provider) we use a SINGLE
// sastaspace connection per tab, optionally authed with the owner token. When
// no token is present, all reads still work; reducer calls fail server-side.
//
// === STDB TOKEN UX — CURRENT LIMITATION (see apps/admin/AUTH_TODO.md) ===
// The owner must currently paste their STDB JWT into the browser UI manually.
// This is bad UX. The planned fix (Phase 4) is:
//   1. Admin signs in via Google OAuth (already works).
//   2. A Next.js API route on the admin app verifies the Google email matches
//      OWNER_EMAIL (server-only env var) and returns the STDB owner JWT
//      (also held in a server-only env var, never baked into the client bundle).
//   3. The frontend stores it in sessionStorage (per-tab, cleared on close).
// BLOCKER: admin currently uses `output: 'export'` (static site). Adding an
// API route requires switching to a dynamic build target. See AUTH_TODO.md.
//
// SECURITY NOTE (audit D2): token is stored in sessionStorage, NOT
// localStorage. sessionStorage is cleared when the tab closes, reducing XSS
// blast radius — a compromised script can read the token during the session
// but it doesn't persist across sessions or other tabs.

import { useMemo, useEffect, useState } from 'react';
import { SpacetimeDBProvider } from 'spacetimedb/react';
import { DbConnection as SastaspaceConn } from '@sastaspace/stdb-bindings';
import { DbConnection as TypewarsConn } from '@sastaspace/typewars-bindings';

const STDB_URI = process.env.NEXT_PUBLIC_STDB_URI ?? 'wss://stdb.sastaspace.com';
export const USE_STDB_ADMIN = process.env.NEXT_PUBLIC_USE_STDB_ADMIN === 'true';

const OWNER_TOKEN_KEY = 'admin_stdb_owner_token';

export function getOwnerToken(): string | null {
  if (typeof window === 'undefined') return null;
  // Security audit D2: use sessionStorage (per-tab, cleared on close) instead
  // of localStorage (persists across sessions, larger XSS blast radius).
  // Fall back to localStorage to migrate existing tokens saved before this change.
  const session = sessionStorage.getItem(OWNER_TOKEN_KEY);
  if (session) return session;
  const local = localStorage.getItem(OWNER_TOKEN_KEY);
  if (local) {
    // Migrate to sessionStorage and clear from localStorage.
    sessionStorage.setItem(OWNER_TOKEN_KEY, local);
    localStorage.removeItem(OWNER_TOKEN_KEY);
    return local;
  }
  return null;
}

export function setOwnerToken(t: string): void {
  if (typeof window === 'undefined') return;
  // Store in sessionStorage only (see security note above).
  sessionStorage.setItem(OWNER_TOKEN_KEY, t);
  // Ensure it's gone from localStorage if migrating from an older session.
  localStorage.removeItem(OWNER_TOKEN_KEY);
}

export function clearOwnerToken(): void {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(OWNER_TOKEN_KEY);
  localStorage.removeItem(OWNER_TOKEN_KEY);
}

/**
 * Subscribe to owner-token changes (e.g. saved via the settings modal).
 * Returns the current token string or null.
 *
 * NOTE: sessionStorage 'storage' events do NOT fire across tabs (unlike
 * localStorage). Cross-tab token sharing is not supported — each tab must
 * paste its own token. The OwnerTokenSettings modal triggers
 * window.location.reload() after save, which remounts the provider and
 * re-reads the token, so within-tab changes always take effect.
 */
export function useOwnerToken(): string | null {
  const [token, setToken] = useState<string | null>(() => getOwnerToken());
  useEffect(() => {
    // The 'storage' event only fires for localStorage changes from OTHER tabs.
    // For sessionStorage (our storage), we rely on the reload-after-save
    // pattern in OwnerTokenSettings. This listener is kept as a safety net for
    // any callers that might still write to localStorage under the same key.
    const onStorage = (e: StorageEvent) => {
      if (e.key === OWNER_TOKEN_KEY) setToken(getOwnerToken());
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);
  return token;
}

/**
 * Sastaspace SpacetimeDB connection. If an owner token is in localStorage,
 * the connection is authed (so set_comment_status_with_reason etc. succeed).
 * Otherwise the connection is anonymous — read subscriptions still work
 * because all admin-consumed tables are `public`.
 */
export function SastaspaceProvider({ children }: { children: React.ReactNode }) {
  const builder = useMemo(() => {
    const b = SastaspaceConn.builder().withUri(STDB_URI).withDatabaseName('sastaspace');
    const token = getOwnerToken();
    return token ? b.withToken(token) : b;
    // The token is read once at provider mount. The OwnerTokenSettings
    // modal triggers a window.location.reload() after save, which remounts
    // the provider — no need to listen for storage events here.
  }, []);
  return SpacetimeDBProvider({ connectionBuilder: builder, children });
}

export function TypewarsProvider({ children }: { children: React.ReactNode }) {
  const builder = useMemo(
    () => TypewarsConn.builder().withUri(STDB_URI).withDatabaseName('typewars'),
    [],
  );
  return SpacetimeDBProvider({ connectionBuilder: builder, children });
}
