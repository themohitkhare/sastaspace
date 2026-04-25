"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { saveSession } from "@/lib/auth";
import styles from "@/app/notes.module.css";

type State = { kind: "loading" } | { kind: "ok" } | { kind: "error"; message: string };

/**
 * Synchronously parses the URL fragment + saves the session before React
 * even renders. This avoids the React 19 "setState in effect" lint and
 * also tightens the visual flicker — by the time the component paints,
 * we already know whether sign-in succeeded.
 *
 * The redirect-to-/ side effect still runs in useEffect because it needs
 * to fire after mount (window.history etc.).
 */
function processCallback(): State {
  if (typeof window === "undefined") return { kind: "loading" };
  const fragment = window.location.hash.replace(/^#/, "");
  const params = new URLSearchParams(fragment);
  const token = params.get("token");
  const email = params.get("email");
  if (!token || !email) {
    return { kind: "error", message: "Sign-in link is incomplete. Try signing in again." };
  }
  saveSession(token, email);
  return { kind: "ok" };
}

export default function AuthCallbackPage() {
  // useState's lazy initializer runs once at render time (no effect),
  // satisfying the React 19 set-state-in-effect rule. Inline function
  // expression is what the lint wants; processCallback is hoisted.
  const [state] = useState<State>(() => processCallback());

  useEffect(() => {
    if (state.kind !== "ok") return;
    window.history.replaceState({}, "", "/");
    const t = window.setTimeout(() => {
      window.location.replace("/");
    }, 600);
    return () => window.clearTimeout(t);
  }, [state]);

  return (
    <div className={styles.wrap}>
      <main style={{ padding: "96px 0 48px", textAlign: "center" }}>
        {state.kind === "loading" && (
          <p style={{ color: "var(--brand-muted)", fontFamily: "var(--font-mono)", fontSize: 13 }}>
            signing you in…
          </p>
        )}
        {state.kind === "ok" && (
          <>
            <h1 style={{ fontSize: 24, fontWeight: 500, margin: "0 0 8px" }}>You're signed in.</h1>
            <p style={{ color: "var(--brand-muted)", fontSize: 14 }}>Redirecting to notes…</p>
          </>
        )}
        {state.kind === "error" && (
          <>
            <h1 style={{ fontSize: 24, fontWeight: 500, margin: "0 0 8px" }}>Sign-in failed.</h1>
            <p style={{ color: "var(--brand-muted)", fontSize: 14, marginBottom: 16 }}>
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
