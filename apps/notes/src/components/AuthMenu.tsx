"use client";

import { useEffect, useRef, useState } from "react";
import { clearSession, getSession, requestMagicLink, subscribe, type Session } from "@/lib/auth";
import styles from "./auth.module.css";

type ModalState =
  | { kind: "closed" }
  | { kind: "open" }
  | { kind: "submitting" }
  | { kind: "sent"; email: string }
  | { kind: "error"; message: string };

export function AuthMenu() {
  const [session, setSession] = useState<Session | null>(null);
  const [modal, setModal] = useState<ModalState>({ kind: "closed" });
  const [email, setEmail] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => subscribe((s) => setSession(s)), []);

  // Focus the email input when modal opens
  useEffect(() => {
    if (modal.kind === "open" && inputRef.current) {
      inputRef.current.focus();
    }
  }, [modal.kind]);

  // Close modal on Escape
  useEffect(() => {
    if (modal.kind === "closed") return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setModal({ kind: "closed" });
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [modal.kind]);

  // Other components (e.g. CommentForm) can pop the sign-in modal by
  // dispatching a `sastaspace:open-signin` event — avoids prop-drilling
  // a global opener through unrelated layout components.
  useEffect(() => {
    function open() { setModal({ kind: "open" }); }
    window.addEventListener("sastaspace:open-signin", open);
    return () => window.removeEventListener("sastaspace:open-signin", open);
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = email.trim().toLowerCase();
    if (!value || !value.includes("@")) {
      setModal({ kind: "error", message: "Enter a valid email." });
      return;
    }
    setModal({ kind: "submitting" });
    try {
      // Phase 2 F1: stash the email so /auth/verify can populate Session.email
      // when the magic link comes back. Harmless for the legacy /auth/callback
      // flow (it pulls email from the URL fragment and ignores sessionStorage).
      // If the user opens the link in a different browser, sessionStorage is
      // empty → verify page falls back to a placeholder and the user-table
      // subscription corrects it on next mount.
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem("sastaspace.pendingEmail", value);
      }
      await requestMagicLink(value);
      setModal({ kind: "sent", email: value });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to send.";
      setModal({ kind: "error", message });
    }
  }

  if (session) {
    return (
      <div className={styles.signedIn}>
        <span className={styles.signedInName}>{session.display_name}</span>
        <button className={styles.linkButton} onClick={clearSession} type="button">
          sign out
        </button>
      </div>
    );
  }

  return (
    <>
      <button
        className={styles.linkButton}
        type="button"
        onClick={() => setModal({ kind: "open" })}
      >
        sign in
      </button>
      {modal.kind !== "closed" && (
        <div
          className={styles.backdrop}
          onClick={() => setModal({ kind: "closed" })}
          role="presentation"
        >
          <div
            className={styles.modal}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Sign in"
          >
            {modal.kind === "sent" ? (
              <div className={styles.sent}>
                <div className={styles.eyebrow}>check your inbox</div>
                <p>
                  We sent a sign-in link to <strong>{modal.email}</strong>. Click it to come back
                  signed in. The link is good for 15 minutes.
                </p>
                <button
                  className={styles.linkButton}
                  type="button"
                  onClick={() => setModal({ kind: "closed" })}
                >
                  close
                </button>
              </div>
            ) : (
              <form onSubmit={onSubmit}>
                <div className={styles.eyebrow}>sign in</div>
                <p className={styles.lede}>
                  Enter your email. We send you a one-click link — no password to remember.
                </p>
                <label htmlFor="auth-email" className={styles.label}>
                  email
                </label>
                <input
                  ref={inputRef}
                  id="auth-email"
                  type="email"
                  className={styles.input}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  placeholder="you@example.com"
                  disabled={modal.kind === "submitting"}
                />
                {modal.kind === "error" && (
                  <p className={styles.error}>{modal.message}</p>
                )}
                <div className={styles.actions}>
                  <button
                    type="button"
                    className={styles.linkButton}
                    onClick={() => setModal({ kind: "closed" })}
                  >
                    cancel
                  </button>
                  <button
                    type="submit"
                    className={styles.submit}
                    disabled={modal.kind === "submitting"}
                  >
                    {modal.kind === "submitting" ? "sending…" : "email me a link →"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}

// Re-export getSession for consumers that need to read state without subscribing
export { getSession };
