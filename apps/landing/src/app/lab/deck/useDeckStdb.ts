"use client";

// Phase 2 F4 — STDB connection hook for the /lab/deck page.
//
// The lab page is public — no Google/magic-link sign-in. SpacetimeDB still
// requires an identity to call reducers and to scope subscriptions, so we
// mint one anonymously via the SDK's built-in identity bootstrap and persist
// the JWT in localStorage under TOKEN_KEY. This lets the same browser keep
// the same identity across reloads, so a user who reloads mid-render still
// observes "their" plan_request / generate_job rows.
//
// TODO(Phase 4 modularization): once the legacy HTTP path is removed, this
// hook + deckStdbFlows + Deck.tsx should be split into per-step components.
// Tracked under audit M1.

import { useEffect, useRef, useState } from "react";
import { DbConnection } from "@sastaspace/stdb-bindings";

const STDB_URI =
  process.env.NEXT_PUBLIC_STDB_URI ?? "wss://stdb.sastaspace.com";
const STDB_MODULE =
  process.env.NEXT_PUBLIC_SASTASPACE_MODULE ?? "sastaspace";

const TOKEN_KEY = "sastaspace.deck.anon.v1";

function loadToken(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return window.localStorage.getItem(TOKEN_KEY) ?? undefined;
}

function saveToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export type DeckStdb = {
  conn: DbConnection;
  /** Hex identity of the connected client; stable across reloads in this browser. */
  identityHex: string;
};

/**
 * Connects to the sastaspace module with an anonymous identity, persisted
 * across reloads via `localStorage[TOKEN_KEY]`. Returns null while connecting.
 * Tears down on unmount.
 */
export function useDeckStdb(enabled: boolean): DeckStdb | null {
  const [state, setState] = useState<DeckStdb | null>(null);
  // StrictMode in dev double-invokes effects; guard against double-connect.
  const builtRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    if (builtRef.current) return;
    builtRef.current = true;

    let cancelled = false;
    let conn: DbConnection | null = null;

    const baseBuilder = DbConnection.builder()
      .withUri(STDB_URI)
      .withDatabaseName(STDB_MODULE)
      .onConnect((ctx, identity, token) => {
        if (cancelled) return;
        if (token) saveToken(token);
        // Per the SDK's DbConnectionImpl, the connection itself is the
        // EventContext for the onConnect callback (see node_modules
        // spacetimedb/dist/sdk/db_connection_impl.d.ts).
        const connection = (ctx as unknown as DbConnection) ?? conn;
        if (connection) {
          setState({ conn: connection, identityHex: identity.toHexString() });
        }
      })
      .onConnectError((_ctx, err) => {
        console.warn("[deck] stdb connect error:", err);
      });

    const existing = loadToken();
    const builder = existing ? baseBuilder.withToken(existing) : baseBuilder;
    conn = builder.build();

    return () => {
      cancelled = true;
      try {
        conn?.disconnect();
      } catch {
        /* ignore */
      }
    };
  }, [enabled]);

  return state;
}
