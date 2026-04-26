// STDB-native sign-in completion page.
//
// Flow:
//   1. User clicks the magic link in email → /auth/verify?t=<token>
//   2. mintAnonymousIdentity() → fresh JWT for the anon connection
//   3. verifyTokenViaStdb(token) → calls verify_token reducer; the W1 reducer
//      validates the token, marks it used, and (if it's a fresh user) creates
//      a row in `user`. The reducer derives display_name from the email
//      local-part when displayName="" is passed.
//   4. saveFullSession() → writes localStorage; AuthMenu's subscribe fires
//   5. Redirect home.
//
// The email is re-derived from sessionStorage (set by AuthMenu when the user
// hit submit); if missing (different browser), we fall back to a placeholder
// — the canonical source of truth lives in the `user` table and downstream
// reads pick up the corrected display_name on next mount.

"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { saveFullSession } from "@/lib/auth";
import { verifyTokenViaStdb } from "@/lib/stdbAuth";
import styles from "@/app/notes.module.css";

const PENDING_EMAIL_KEY = "sastaspace.pendingEmail";

type State =
  | { kind: "loading" }
  | { kind: "ok" }
  | { kind: "error"; message: string };

function VerifyInner() {
  const params = useSearchParams();
  // Lazy initializer derives the initial state at render time (no effect),
  // satisfying React 19's set-state-in-effect lint for the missing-token
  // branch. The "loading" case immediately kicks off the async verify in
  // useEffect below; setState inside the async closure is allowed because
  // the call is no longer synchronous to the effect body.
  const [state, setState] = useState<State>(() => {
    const token = params.get("t");
    if (!token) {
      return {
        kind: "error",
        message: "Sign-in link is incomplete (no token). Try signing in again.",
      };
    }
    return { kind: "loading" };
  });

  useEffect(() => {
    if (state.kind !== "loading") return;
    const token = params.get("t");
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const { jwt, identity } = await verifyTokenViaStdb(token);
        if (cancelled) return;
        // The reducer derived display_name from the email server-side. We
        // re-derive client-side for the saved Session shape since the reducer
        // call returns void; the canonical value will refresh on next mount
        // via the user-table subscription.
        const pendingEmail =
          typeof window !== "undefined"
            ? window.sessionStorage.getItem(PENDING_EMAIL_KEY) ?? ""
            : "";
        const email = pendingEmail || "user@unknown";
        const display_name = email.split("@")[0] || email;
        saveFullSession({ token: jwt, email, display_name, identity });
        if (typeof window !== "undefined") {
          window.sessionStorage.removeItem(PENDING_EMAIL_KEY);
        }
        setState({ kind: "ok" });
      } catch (err) {
        if (cancelled) return;
        const raw = err instanceof Error ? err.message : "verify failed";
        setState({
          kind: "error",
          message: friendlyError(raw),
        });
      }
    })();
    return () => {
      cancelled = true;
    };
    // We intentionally only re-run when params changes — state.kind is read
    // as a guard but updating state shouldn't re-trigger the verify call.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  useEffect(() => {
    if (state.kind !== "ok") return;
    const t = window.setTimeout(() => {
      window.location.replace("/");
    }, 600);
    return () => window.clearTimeout(t);
  }, [state]);

  return (
    <div className={styles.wrap}>
      <main style={{ padding: "96px 0 48px", textAlign: "center" }}>
        {state.kind === "loading" && (
          <p
            style={{
              color: "var(--brand-muted)",
              fontFamily: "var(--font-mono)",
              fontSize: 13,
            }}
          >
            verifying your sign-in link…
          </p>
        )}
        {state.kind === "ok" && (
          <>
            <h1 style={{ fontSize: 24, fontWeight: 500, margin: "0 0 8px" }}>
              You&apos;re signed in.
            </h1>
            <p style={{ color: "var(--brand-muted)", fontSize: 14 }}>
              Redirecting to notes…
            </p>
          </>
        )}
        {state.kind === "error" && (
          <>
            <h1 style={{ fontSize: 24, fontWeight: 500, margin: "0 0 8px" }}>
              Sign-in failed.
            </h1>
            <p
              style={{
                color: "var(--brand-muted)",
                fontSize: 14,
                marginBottom: 16,
              }}
            >
              {state.message}
            </p>
            <Link href="/" style={{ color: "var(--brand-sasta-text)" }}>
              ← back to notes
            </Link>
          </>
        )}
      </main>
    </div>
  );
}

/**
 * Map known reducer error strings (W1's verify_token returns these literal
 * messages) and other surfaceable failures to user-friendly copy.
 */
function friendlyError(raw: string): string {
  if (/expired/i.test(raw)) {
    return "That sign-in link has expired. Magic links are good for 15 minutes — request a fresh one.";
  }
  if (/already used|already_used/i.test(raw)) {
    return "That link has already been used. Request a fresh sign-in link.";
  }
  if (/unknown token|invalid token/i.test(raw)) {
    return "That sign-in link doesn't look right. Try signing in again.";
  }
  if (/network|fetch|ECONN|disconnected|HTTP \d/i.test(raw)) {
    return "We couldn't reach our servers. Check your connection and try the link again.";
  }
  return "We couldn't verify that link. Try signing in again.";
}

export default function AuthVerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyInner />
    </Suspense>
  );
}
