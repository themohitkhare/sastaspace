'use client';

// Shared SpacetimeDB provider factories for admin panel.
// Reads come from anonymous public-table subscriptions; writes (moderation +
// log_interest) require the owner's STDB JWT pasted into the settings UI.
//
// To keep React contexts simple (one connection per provider) we use a SINGLE
// sastaspace connection per tab, optionally authed with the owner token. When
// no token is present, all reads still work; reducer calls fail server-side.

import { useMemo, useEffect, useState } from 'react';
import { SpacetimeDBProvider } from 'spacetimedb/react';
import { DbConnection as SastaspaceConn } from '@sastaspace/stdb-bindings';
import { DbConnection as TypewarsConn } from '@sastaspace/typewars-bindings';

const STDB_URI = process.env.NEXT_PUBLIC_STDB_URI ?? 'wss://stdb.sastaspace.com';
export const USE_STDB_ADMIN = process.env.NEXT_PUBLIC_USE_STDB_ADMIN === 'true';

const OWNER_TOKEN_KEY = 'admin_stdb_owner_token';

export function getOwnerToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(OWNER_TOKEN_KEY);
}

export function setOwnerToken(t: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(OWNER_TOKEN_KEY, t);
}

export function clearOwnerToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(OWNER_TOKEN_KEY);
}

/**
 * Subscribe to owner-token changes (e.g. saved in another tab or via the
 * settings modal). Returns the current token string or null.
 */
export function useOwnerToken(): string | null {
  const [token, setToken] = useState<string | null>(() => getOwnerToken());
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === OWNER_TOKEN_KEY) setToken(e.newValue);
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
