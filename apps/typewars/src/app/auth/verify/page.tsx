"use client";
/**
 * Phase 2 F2 — STDB-native magic-link verify page for typewars.
 *
 * Flow (when SignInModal routed `callback=https://typewars.sastaspace.com/auth/verify`):
 *   1. Mint a fresh anonymous identity + JWT via POST {STDB_HTTP}/v1/identity.
 *   2. Connect to the **sastaspace** module with that JWT and call
 *      `verify_token(token, displayName)`. This consumes the auth_token and
 *      registers the new identity as a User row (writes the email).
 *   3. If the URL carries `?prev=<hex>` (the guest's pre-sign-in identity),
 *      reconnect to the **typewars** module with the same JWT and call
 *      `claim_progress_self(prevIdentity, email)`. The caller's identity
 *      (= the new authenticated identity) becomes the new owner of the
 *      guest's player rows. Failures here are surfaced as a non-fatal
 *      warning so sign-in still completes.
 *   4. Persist JWT under `typewars:auth_token` and redirect to /.
 *
 * Email derivation: when SignInModal submits, it stashes the email under
 * sessionStorage `typewars:pending_email` (F1 wires this up); until F1 lands
 * the page falls back to subscribing to the User row populated by verify_token
 * and reading the email column.
 */
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Identity } from "spacetimedb";
import { DbConnection as SastaConn } from "@sastaspace/stdb-bindings";
import { DbConnection as TypewarsConn } from "@sastaspace/typewars-bindings";

const TOKEN_KEY = "typewars:auth_token";
const PENDING_EMAIL_KEY = "typewars:pending_email";
const STDB_HTTP =
  process.env.NEXT_PUBLIC_STDB_HTTP ?? "https://stdb.sastaspace.com";
const STDB_WS =
  process.env.NEXT_PUBLIC_STDB_URI ?? "wss://stdb.sastaspace.com";
const SASTA_MODULE =
  process.env.NEXT_PUBLIC_SASTA_MODULE ?? "sastaspace";
const TYPEWARS_MODULE =
  process.env.NEXT_PUBLIC_TYPEWARS_MODULE ?? "typewars";

type Phase =
  | "minting"
  | "verifying"
  | "claiming"
  | "done"
  | "error"
  | "claim-warn";

async function mintIdentity(): Promise<{ identity: string; token: string }> {
  const res = await fetch(`${STDB_HTTP}/v1/identity`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`identity mint failed: HTTP ${res.status}`);
  }
  const json = (await res.json()) as { identity: string; token: string };
  if (!json?.identity || !json?.token) {
    throw new Error("identity response missing identity/token");
  }
  return json;
}

function connectSasta(jwt: string): Promise<SastaConn> {
  return new Promise<SastaConn>((resolve, reject) => {
    const c: SastaConn = SastaConn.builder()
      .withUri(STDB_WS)
      .withDatabaseName(SASTA_MODULE)
      .withToken(jwt)
      .onConnect(() => resolve(c))
      .onConnectError((_ctx, err) => reject(err))
      .build();
  });
}

function connectTypewars(jwt: string): Promise<TypewarsConn> {
  return new Promise<TypewarsConn>((resolve, reject) => {
    const c: TypewarsConn = TypewarsConn.builder()
      .withUri(STDB_WS)
      .withDatabaseName(TYPEWARS_MODULE)
      .withToken(jwt)
      .onConnect(() => resolve(c))
      .onConnectError((_ctx, err) => reject(err))
      .build();
  });
}

/**
 * Subscribe to the User table on the active sastaspace connection and resolve
 * the email when the row keyed on `identityHex` is in the cache. verify_token
 * has already inserted/updated the row server-side, so the row should arrive
 * inside the SubscriptionApplied message in the common case.
 *
 * Resolves to undefined on timeout so callers can decide whether to surface a
 * warning rather than blocking sign-in.
 */
function readEmailFromUserRow(
  conn: SastaConn,
  identityHex: string,
  timeoutMs = 4000,
): Promise<string | undefined> {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (val: string | undefined) => {
      if (settled) return;
      settled = true;
      resolve(val);
    };
    const timer = setTimeout(() => finish(undefined), timeoutMs);
    let target: Identity;
    try {
      target = Identity.fromString(identityHex);
    } catch {
      clearTimeout(timer);
      finish(undefined);
      return;
    }

    const checkCache = (): boolean => {
      // The connection's `db.user` view exposes ReadonlyTableMethods (iter,
      // count). Walk the cache for the row keyed on `target`.
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const userTable = (conn as any).db?.user;
        if (!userTable?.iter) return false;
        for (const row of userTable.iter() as Iterable<{
          identity: Identity;
          email: string;
        }>) {
          if (row.identity.toHexString() === target.toHexString() && row.email) {
            clearTimeout(timer);
            finish(row.email);
            return true;
          }
        }
      } catch {
        /* noop */
      }
      return false;
    };

    try {
      conn
        .subscriptionBuilder()
        .onApplied(() => {
          if (checkCache()) return;
          // Row may arrive on a subsequent insert; hook onInsert too.
          try {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const userTable = (conn as any).db?.user;
            userTable?.onInsert?.(
              (_ctx: unknown, row: { identity: Identity; email: string }) => {
                if (
                  row.identity.toHexString() === target.toHexString() &&
                  row.email
                ) {
                  clearTimeout(timer);
                  finish(row.email);
                }
              },
            );
          } catch {
            /* noop */
          }
        })
        .subscribe(["SELECT * FROM user"]);
    } catch {
      clearTimeout(timer);
      finish(undefined);
    }
  });
}

export default function AuthVerifyPage() {
  return (
    <Suspense
      fallback={
        <div
          className="page"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "100vh",
          }}
        >
          <div style={{ textAlign: "center", maxWidth: 480, padding: 24 }}>
            <p className="ss-eyebrow">~/typewars/auth/verify —</p>
            <p className="ss-body" style={{ marginTop: 8 }}>Loading…</p>
          </div>
        </div>
      }
    >
      <VerifyInner />
    </Suspense>
  );
}

function VerifyInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [phase, setPhase] = useState<Phase>("minting");
  const [message, setMessage] = useState("Minting fresh identity…");
  const [warn, setWarn] = useState<string | null>(null);

  useEffect(() => {
    const token = params?.get("t");
    const app = params?.get("app");
    const prev = params?.get("prev"); // hex without 0x prefix
    if (!token || app !== "typewars") {
      setPhase("error");
      setMessage("Sign-in link is missing required fields.");
      return;
    }

    let cancelled = false;
    let sastaConn: SastaConn | null = null;
    let typewarsConn: TypewarsConn | null = null;

    void (async () => {
      try {
        // 1. Mint fresh identity + JWT.
        setPhase("minting");
        setMessage("Minting fresh identity…");
        const { identity: newIdentityHex, token: jwt } = await mintIdentity();
        if (cancelled) return;

        // 2. Connect to the sastaspace module with the new JWT and call
        //    verify_token. The reducer consumes the auth_token row and
        //    upserts the User row keyed on the caller's identity.
        setPhase("verifying");
        setMessage("Verifying your sign-in link…");
        sastaConn = await connectSasta(jwt);
        await sastaConn.reducers.verifyToken({ token, displayName: "" });
        if (cancelled) return;

        // 3. Email derivation: prefer sessionStorage stash (F1 writes this on
        //    request); fall back to the User row populated by verify_token.
        let email: string | undefined;
        try {
          email = window.sessionStorage.getItem(PENDING_EMAIL_KEY) ?? undefined;
        } catch {
          /* sessionStorage may be blocked */
        }
        if (!email) {
          email = await readEmailFromUserRow(sastaConn, newIdentityHex);
        }

        // 4. claim_progress_self if guest identity present + email known.
        if (prev && prev.length >= 32) {
          if (!email) {
            setWarn(
              "Signed in, but couldn't recover your email to transfer guest stats — leaderboard starts fresh.",
            );
            setPhase("claim-warn");
          } else {
            try {
              setPhase("claiming");
              setMessage("Transferring your guest progress…");
              typewarsConn = await connectTypewars(jwt);
              const prevIdentity = Identity.fromString(prev);
              await typewarsConn.reducers.claimProgressSelf({
                prevIdentity,
                email,
              });
            } catch (e) {
              setWarn(
                "We couldn't transfer your guest stats — you're signed in but the leaderboard starts fresh. " +
                  String(e).slice(0, 200),
              );
              setPhase("claim-warn");
            }
          }
        }

        // 5. Persist JWT under the typewars-specific localStorage key (the
        //    live spacetime connection in apps/typewars/src/lib/spacetime.ts
        //    reads from this same key on next mount).
        try {
          window.localStorage.setItem(TOKEN_KEY, jwt);
        } catch {
          throw new Error("localStorage blocked — sign-in cannot complete");
        }
        try {
          window.sessionStorage.removeItem(PENDING_EMAIL_KEY);
        } catch {
          /* noop */
        }

        if (cancelled) return;
        setPhase((p) => (p === "claim-warn" ? p : "done"));
        setMessage("Signed in. Redirecting…");
        // Brief pause if a warning is showing so the user can read it.
        const delay = warn ? 2500 : 150;
        setTimeout(() => {
          if (!cancelled) router.replace("/");
        }, delay);
      } catch (e) {
        if (cancelled) return;
        setPhase("error");
        setMessage(
          `Sign-in failed: ${e instanceof Error ? e.message : String(e)}`,
        );
      }
    })();

    return () => {
      cancelled = true;
      try { sastaConn?.disconnect(); } catch { /* noop */ }
      try { typewarsConn?.disconnect(); } catch { /* noop */ }
    };
    // The effect intentionally runs once on mount. params/router/warn are
    // captured at that point.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className="page"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
      }}
    >
      <div style={{ textAlign: "center", maxWidth: 480, padding: 24 }}>
        <p className="ss-eyebrow">~/typewars/auth/verify —</p>
        <p className="ss-body" style={{ marginTop: 8 }}>{message}</p>
        {warn && (
          <p
            className="ss-small"
            style={{ marginTop: 12, color: "var(--brand-muted)" }}
          >
            {warn}
          </p>
        )}
        {phase === "error" && (
          <button
            className="enlist-btn"
            onClick={() => router.replace("/")}
            style={{ marginTop: 16 }}
          >
            back to map →
          </button>
        )}
      </div>
    </div>
  );
}
