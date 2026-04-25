"use client";

import { useEffect, useState } from "react";
import { saveSession } from "@/lib/auth";
import styles from "@/app/notes.module.css";

export default function AuthCallbackPage() {
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const fragment = window.location.hash.replace(/^#/, "");
    const params = new URLSearchParams(fragment);
    const token = params.get("token");
    const email = params.get("email");

    if (!token || !email) {
      setState("error");
      setErrorMsg("Sign-in link is incomplete. Try signing in again.");
      return;
    }

    saveSession(token, email);
    setState("ok");
    // Strip the fragment so a refresh doesn't re-process, then bounce home.
    window.history.replaceState({}, "", "/");
    const t = window.setTimeout(() => {
      window.location.replace("/");
    }, 600);
    return () => window.clearTimeout(t);
  }, []);

  return (
    <div className={styles.wrap}>
      <main style={{ padding: "96px 0 48px", textAlign: "center" }}>
        {state === "loading" && (
          <p style={{ color: "var(--brand-muted)", fontFamily: "var(--font-mono)", fontSize: 13 }}>
            signing you in…
          </p>
        )}
        {state === "ok" && (
          <>
            <h1 style={{ fontSize: 24, fontWeight: 500, margin: "0 0 8px" }}>You're signed in.</h1>
            <p style={{ color: "var(--brand-muted)", fontSize: 14 }}>Redirecting to notes…</p>
          </>
        )}
        {state === "error" && (
          <>
            <h1 style={{ fontSize: 24, fontWeight: 500, margin: "0 0 8px" }}>Sign-in failed.</h1>
            <p style={{ color: "var(--brand-muted)", fontSize: 14, marginBottom: 16 }}>
              {errorMsg}
            </p>
            <a href="/" style={{ color: "var(--brand-sasta-text)" }}>
              ← back to notes
            </a>
          </>
        )}
      </main>
    </div>
  );
}
